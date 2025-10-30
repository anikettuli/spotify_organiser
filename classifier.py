"""Main classification orchestration with metadata analysis and parallel processing."""
import re
import os
import threading
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from llm_classifier import LLMClassifier
from cache_manager import CacheManager
from config import Config

try:
    from langdetect import detect, LangDetectException
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False


class SongClassifier:
    """Orchestrates song classification with metadata analysis and LLM."""
    
    def __init__(self):
        """Initialize classifier."""
        self.llm = LLMClassifier()
        self.cache_manager = CacheManager()
        self.session_cache = {}  # In-memory cache for current session
        self.cache_lock = threading.Lock()  # Thread-safe access to session cache
    
    def classify_tracks(self, tracks: List[Dict], progress_callback=None, track_callback=None) -> Dict[str, List[Dict]]:
        """
        Classify multiple tracks with parallel processing using queue-based approach.
        
        Args:
            tracks: List of track metadata dictionaries
            progress_callback: Optional callback function for progress updates
            track_callback: Optional callback for each track completion (track, category, processed, total)
            
        Returns:
            Dictionary mapping categories to lists of tracks
        """
        categorized = {category: [] for category in Config.CATEGORIES}
        
        # Process tracks in batches if using Gemini, otherwise parallel individual
        total = len(tracks)
        processed = 0
        errors = 0
        
        use_gemini = os.getenv('USE_GEMINI', '0') == '1'
        batch_size = 100 if use_gemini else 1
        
        # Use a lock for all shared data structures
        results_lock = threading.Lock()
        
        if use_gemini and batch_size > 1:
            # Batch processing for Gemini
            for i in range(0, len(tracks), batch_size):
                batch = tracks[i:i+batch_size]
                try:
                    # Classify entire batch at once
                    results = self.llm.classify_batch(batch)
                    
                    for track, (category, confidence) in zip(batch, results):
                        # Save to cache
                        self.cache_manager.save_classification(track['id'], category, confidence)
                        with results_lock:
                            categorized[category].append(track)
                            processed += 1
                        
                        if progress_callback:
                            progress_callback(processed, total)
                        if track_callback:
                            track_callback(track, category, processed, total)
                            
                except Exception as e:
                    print(f"\n⚠️  Batch classification error: {e}")
                    # Fall back to individual classification for this batch
                    for track in batch:
                        try:
                            category = self._classify_single_track(track)
                            with results_lock:
                                categorized[category].append(track)
                        except:
                            with results_lock:
                                categorized['Misc'].append(track)
                            category = 'Misc'
                            errors += 1
                        
                        with results_lock:
                            processed += 1
                        if progress_callback:
                            progress_callback(processed, total)
                        if track_callback:
                            track_callback(track, category, processed, total)
        else:
            # Original parallel processing
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                # Submit all tracks to queue
                futures = []
                for track in tracks:
                    future = executor.submit(self._classify_single_track_safe, track)
                    futures.append((future, track))
                
                # Collect results as they complete (no timeout - let it finish)
                for future, track in futures:
                    try:
                        category = future.result()  # Block until done, no timeout
                        with results_lock:
                            categorized[category].append(track)
                    except Exception as e:
                        # If classification fails for this track, put in Misc
                        print(f"\n⚠️  Error classifying '{track['name']}': {e}")
                        with results_lock:
                            categorized['Misc'].append(track)
                        category = 'Misc'
                        errors += 1
                    
                    with results_lock:
                        processed += 1
                        current_processed = processed
                    
                    if progress_callback:
                        progress_callback(current_processed, total)
                    
                    if track_callback:
                        track_callback(track, category, current_processed, total)
        
        if errors > 0:
            print(f"\n⚠️  {errors} tracks failed classification and were moved to Misc")
        
        return categorized
    
    def _classify_single_track_safe(self, track: Dict) -> str:
        """
        Wrapper for _classify_single_track with error handling.
        
        Args:
            track: Track metadata dictionary
            
        Returns:
            Category name
        """
        try:
            return self._classify_single_track(track)
        except Exception as e:
            # Log error and return Misc as fallback
            print(f"\n⚠️  Classification failed for '{track.get('name', 'Unknown')}': {e}")
            # Still save to cache as Misc so we don't retry repeatedly
            track_id = track.get('id')
            if track_id:
                self.cache_manager.save_classification(track_id, 'Misc', 0.0)
            return 'Misc'
    
    def _classify_single_track(self, track: Dict) -> str:
        """
        Classify a single track using metadata rules and LLM.
        
        Args:
            track: Track metadata dictionary
            
        Returns:
            Category name
        """
        track_id = track['id']
        
        # Check session cache first (thread-safe)
        with self.cache_lock:
            if track_id in self.session_cache:
                return self.session_cache[track_id]
            
            # Also check if another thread is working on this track
            # by seeing if it's in persistent cache (just fetched)
            cached_category = self.cache_manager.get_classification(track_id)
            if cached_category:
                self.session_cache[track_id] = cached_category
                return cached_category
        
        # Step 1: Quick metadata checks (no shared state modification)
        category = self._check_metadata_rules(track)
        if category:
            # Save immediately to prevent duplicate work
            with self.cache_lock:
                self.session_cache[track_id] = category
            self.cache_manager.save_classification(track_id, category, 1.0)
            return category
        
        # Step 2: Use LLM for classification (no shared state modification)
        category, confidence = self.llm.classify_song(track)
        original_category = category
        
        # Step 3: Check confidence threshold
        if confidence < Config.CONFIDENCE_THRESHOLD:
            # Low confidence - move to Misc
            # DO NOT modify track dict (shared across threads!)
            category = "Misc"
        
        # Save to both caches (thread-safe, atomic operation)
        with self.cache_lock:
            self.session_cache[track_id] = category
        self.cache_manager.save_classification(track_id, category, confidence)
        
        return category
    
    def _check_metadata_rules(self, track: Dict) -> str:
        """
        Check if track matches any metadata-based rules for quick classification.
        Uses multi-source intelligence: artist + album + title + year.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if matched, None otherwise
        """
        # Rule 1: Check artist knowledge base (HIGHEST PRIORITY)
        artist_category = self._check_artist_knowledge(track)
        if artist_category:
            return artist_category
        
        # Rule 2: Check album patterns (NEW - STRONG SIGNAL)
        album_category = self._check_album_patterns(track)
        if album_category:
            return album_category
        
        # Rule 3: Enhanced language detection from title + album
        lang_category = self._detect_language_enhanced(track)
        if lang_category:
            return lang_category
        
        # Rule 4: Check for "Oldies" - pre-2000 with patterns
        if self._is_oldies(track):
            return "Oldies"
        
        # Rule 5: Check for instrumental/phonk
        if self._is_instrumental_or_phonk(track):
            return "Phonk/Instrumental"
        
        # Rule 6: Title keyword analysis (expanded)
        keyword_category = self._check_title_keywords(track)
        if keyword_category:
            return keyword_category
        
        # No quick rules matched, need LLM
        return None
    
    def _check_artist_knowledge(self, track: Dict) -> str:
        """
        Check if any artist matches our knowledge base of known artists.
        This is the HIGHEST priority check.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if artist is known, None otherwise
        """
        # Artist knowledge base - maps artist names to categories
        artist_db = {
            # Hindi artists
            'arijit singh': 'Hindi',
            'shreya ghoshal': 'Hindi',
            'neha kakkar': 'Hindi',
            'sonu nigam': 'Hindi',
            'alka yagnik': 'Hindi',
            'kumar sanu': 'Hindi',
            'udit narayan': 'Hindi',
            'vishal-shekhar': 'Hindi',
            'a.r. rahman': 'Hindi',
            'pritam': 'Hindi',
            'badshah': 'Hindi',
            'yo yo honey singh': 'Hindi',
            'raftaar': 'Hindi',
            'jubin nautiyal': 'Hindi',
            'armaan malik': 'Hindi',
            'kr$na': 'Hindi',
            'divine': 'Hindi',
            'ikka': 'Hindi',
            'king': 'Hindi',
            'seedhe maut': 'Hindi',
            'ritviz': 'Hindi',
            
            # Punjabi artists (EXPANDED - from your sample data)
            'diljit dosanjh': 'Punjabi',
            'sidhu moose wala': 'Punjabi',
            'karan aujla': 'Punjabi',
            'ap dhillon': 'Punjabi',
            'guru randhawa': 'Punjabi',
            'ammy virk': 'Punjabi',
            'hardy sandhu': 'Punjabi',
            'harrdy sandhu': 'Punjabi',
            'parmish verma': 'Punjabi',
            'jasmine sandlas': 'Punjabi',
            'jass manak': 'Punjabi',
            'khan bhaini': 'Punjabi',
            'shubh': 'Punjabi',
            'arjan dhillon': 'Punjabi',
            'jordan sandhu': 'Punjabi',
            'gur sidhu': 'Punjabi',
            'cheema y': 'Punjabi',
            'chani nattan': 'Punjabi',
            'navaan sandhu': 'Punjabi',
            'amrinder gill': 'Punjabi',
            'tegi pannu': 'Punjabi',
            'gminxr': 'Punjabi',
            'gurinder gill': 'Punjabi',
            'sukha': 'Punjabi',
            'intense': 'Punjabi',
            'dhanda nyoliwala': 'Punjabi',
            'chinna': 'Punjabi',
            'manni sandhu': 'Punjabi',
            'gulab sidhu': 'Punjabi',
            'jassa dhillon': 'Punjabi',
            'dilpreet dhillon': 'Punjabi',
            'harkirat sangha': 'Punjabi',
            'fotty seven': 'Hindi',  # Indian hip-hop
            'bali': 'Hindi',  # Indian hip-hop
            'elly mangat': 'Punjabi',
            'mankirt aulakh': 'Punjabi',
            'amrit maan': 'Punjabi',
            'satinder sartaaj': 'Punjabi',
            'harnoor': 'Punjabi',
            'bilal saeed': 'Punjabi',
            'gurdas maan': 'Punjabi',
            'jazzy b': 'Punjabi',
            'sharry mann': 'Punjabi',
            
            # Oldies (classic artists)
            'lata mangeshkar': 'Oldies',
            'mohammed rafi': 'Oldies',
            'kishore kumar': 'Oldies',
            'asha bhosle': 'Oldies',
            'mukesh': 'Oldies',
            'talat mahmood': 'Oldies',
            'hemant kumar': 'Oldies',
            'manna dey': 'Oldies',
            'geeta dutt': 'Oldies',
            'shamshad begum': 'Oldies',
            'laxmikant-pyarelal': 'Oldies',
            'nusrat fateh ali khan': 'Oldies',
            
            # English artists (common ones)
            'travis scott': 'English',
            'drake': 'English',
            'the weeknd': 'English',
            'kanye west': 'English',
            'post malone': 'English',
            'billie eilish': 'English',
            'lady gaga': 'English',
            'kendrick lamar': 'English',
            'future': 'English',
            'don toliver': 'English',
            'tyler the creator': 'English',
            'lil wayne': 'English',
            'nle choppa': 'English',
            'bossman dlow': 'English',
            'lil tecca': 'English',
            'soulja boy': 'English',
            'g-eazy': 'English',
            'radiohead': 'English',
            'coldplay': 'English',
            'nirvana': 'English',
            'linkin park': 'English',
        }
        
        # Check each artist in the track
        for artist in track['artists']:
            artist_lower = artist.lower().strip()
            
            # Direct match
            if artist_lower in artist_db:
                return artist_db[artist_lower]
            
            # Partial match (for artist names with variations)
            for known_artist, category in artist_db.items():
                if known_artist in artist_lower or artist_lower in known_artist:
                    return category
        
        return None
    
    def _detect_language(self, track: Dict) -> str:
        """
        Detect language from track name using langdetect library.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if language detected with confidence, None otherwise
        """
        if not _HAS_LANGDETECT:
            return None
        
        try:
            # Combine track name and artist for better detection
            text = f"{track['name']} {' '.join(track['artists'][:2])}"
            
            # Detect language
            lang = detect(text)
            
            # Map language codes to categories
            lang_map = {
                'en': 'English',
                'hi': 'Hindi',
                'pa': 'Punjabi',  # Punjabi
                'ur': 'Hindi',    # Urdu (close to Hindi)
            }
            
            if lang in lang_map:
                return lang_map[lang]
                
        except (LangDetectException, Exception):
            pass
        
        return None
    
    def _is_oldies(self, track: Dict) -> bool:
        """
        Check if track is a classic Hindi song (pre-2000).
        
        Args:
            track: Track metadata
            
        Returns:
            True if track is likely an oldie
        """
        # Check release year
        if track['release_date']:
            try:
                year_str = track['release_date'][:4]
                year = int(year_str)
                if year >= 2000:
                    return False  # Not old enough
            except (ValueError, IndexError):
                pass
        
        # Check for classic artists
        classic_artists = [
            'lata mangeshkar', 'lata', 'mohammed rafi', 'rafi',
            'kishore kumar', 'kishore', 'asha bhosle', 'asha',
            'mukesh', 'talat mahmood', 'hemant kumar',
            'manna dey', 'geeta dutt', 'shamshad begum',
            'suraiya', 'noor jehan', 'k. l. saigal'
        ]
        
        for artist in track['artists']:
            artist_lower = artist.lower()
            for classic in classic_artists:
                if classic in artist_lower:
                    return True
        
        return False
    
    def _is_instrumental_or_phonk(self, track: Dict) -> bool:
        """
        Check if track is instrumental or phonk music.
        
        Args:
            track: Track metadata
            
        Returns:
            True if track is likely instrumental/phonk
        """
        # Check genres
        instrumental_genres = [
            'instrumental', 'phonk', 'ambient', 'classical',
            'soundtrack', 'score', 'jazz instrumental', 'lo-fi',
            'lofi', 'beat', 'beats', 'piano'
        ]
        
        track_name_lower = track['name'].lower()
        
        # Check for instrumental keywords in title
        instrumental_keywords = [
            'instrumental', 'karaoke', 'background music',
            'bgm', '(no vocals)', 'phonk', 'lofi', 'lo-fi'
        ]
        
        for keyword in instrumental_keywords:
            if keyword in track_name_lower:
                return True
        
        # Check genres
        for genre in track['genres']:
            genre_lower = genre.lower()
            for inst_genre in instrumental_genres:
                if inst_genre in genre_lower:
                    return True
        
        return False
    
    def _check_album_patterns(self, track: Dict) -> Optional[str]:
        """
        Check album name for strong category signals.
        Albums often have clearer indicators than track names.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if matched, None otherwise
        """
        album = track.get('album', '').lower()
        if not album:
            return None
        
        # Punjabi album patterns
        punjabi_patterns = ['punjabi', 'pind', 'jatt', 'coke studio bharat', 
                           'punjab', 'desi', 'gabru']
        for pattern in punjabi_patterns:
            if pattern in album:
                return 'Punjabi'
        
        # Hindi/Bollywood patterns
        hindi_patterns = ['bollywood', 'soundtrack', 'original motion picture',
                         'yrf music', 'tseries', 'dharma', 'zee music',
                         'hindi', 'desi kalakaar']
        for pattern in hindi_patterns:
            if pattern in album:
                return 'Hindi'
        
        # Oldies patterns
        oldies_patterns = ['golden', 'evergreen', 'classic', 'retro',
                          'best of', 'greatest hits']
        for pattern in oldies_patterns:
            if pattern in album:
                # Only if old enough
                if track.get('release_date'):
                    try:
                        year = int(track['release_date'][:4])
                        if year < 2005:
                            return 'Oldies'
                    except:
                        pass
        
        return None
    
    def _detect_language_enhanced(self, track: Dict) -> Optional[str]:
        """
        Enhanced language detection using title + album + artist combined.
        More text = better accuracy.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if language detected with confidence, None otherwise
        """
        if not _HAS_LANGDETECT:
            return None
        
        try:
            # Combine multiple text sources for better detection
            title = track.get('name', '')
            album = track.get('album', '')
            artists = ' '.join(track.get('artists', [])[:2])
            
            # Combined text (more context = better detection)
            text = f"{title} {album} {artists}"
            
            if len(text.strip()) < 10:  # Too short
                return None
            
            # Detect language (detect is imported at top)
            lang = detect(text)
            
            # Map language codes to categories
            lang_map = {
                'en': 'English',
                'hi': 'Hindi',
                'pa': 'Punjabi',
                'ur': 'Hindi',  # Urdu close to Hindi
                'mr': 'Hindi',  # Marathi
                'ta': 'Hindi',  # Tamil (Indian)
                'te': 'Hindi',  # Telugu (Indian)
            }
            
            if lang in lang_map:
                return lang_map[lang]
            return None
                
        except (LangDetectException, Exception):
            return None
    
    def _check_title_keywords(self, track: Dict) -> Optional[str]:
        """
        Expanded keyword analysis for title.
        More comprehensive than before.
        
        Args:
            track: Track metadata
            
        Returns:
            Category if strong keyword match, None otherwise
        """
        title = track.get('name', '').lower()
        
        # Expanded Hindi keywords (30+)
        hindi_keywords = [
            'dil', 'pyar', 'pyaar', 'tere', 'mera', 'tera', 'hai', 'tum', 'tu',
            'aaja', 'yaar', 'sanam', 'ishq', 'judaai', 'bewafa', 'deewana',
            'sapna', 'raaton', 'mohabbat', 'zindagi', 'khuda', 'rab', 'meri',
            'teri', 'humara', 'tumhara', 'main', 'kaise', 'kyun', 'kahan'
        ]
        
        # Expanded Punjabi keywords (30+)
        punjabi_keywords = [
            'jatt', 'patola', 'gabru', 'kudi', 'pind', 'viah', 'gallan',
            'sardar', 'punjab', 'panga', 'shera', 'bande', 'mitran',
            'taur', 'nachdi', 'gedi', 'fauji', 'jattan', 'pendu', 'yaari',
            'daru', 'sharab', 'feem', 'akh', 'gabroo', 'pta', 'kro', 'vi',
            'nu', 'da'
        ]
        
        # Count keyword matches
        hindi_count = sum(1 for w in hindi_keywords if w in title)
        punjabi_count = sum(1 for w in punjabi_keywords if w in title)
        
        # Need at least 2 keywords for confidence
        if hindi_count >= 2:
            return 'Hindi'
        if punjabi_count >= 2:
            return 'Punjabi'
        
        # Single strong keyword (for short titles)
        if hindi_count == 1 and len(title.split()) <= 5:
            return 'Hindi'
        if punjabi_count == 1 and len(title.split()) <= 5:
            return 'Punjabi'
        
        return None
    
    def _detect_language_from_text(self, text: str) -> Optional[str]:
        """
        Detect language from text using character patterns.
        This is a simple heuristic, not foolproof.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language or None
        """
        # Cyrillic script (Russian/Ukrainian) - should be Misc
        if re.search(r'[\u0400-\u04FF]', text):
            return 'Misc'
        
        # Devanagari script (Hindi)
        if re.search(r'[\u0900-\u097F]', text):
            return 'Hindi'
        
        # Gurmukhi script (Punjabi)
        if re.search(r'[\u0A00-\u0A7F]', text):
            return 'Punjabi'
        
        return None

