"""Main classification orchestration with metadata analysis and parallel processing."""
import re
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
        Classify multiple tracks with parallel processing and error recovery.
        
        Args:
            tracks: List of track metadata dictionaries
            progress_callback: Optional callback function for progress updates
            track_callback: Optional callback for each track completion (track, category, processed, total)
            
        Returns:
            Dictionary mapping categories to lists of tracks
        """
        categorized = {category: [] for category in Config.CATEGORIES}
        
        # Process tracks in parallel batches
        total = len(tracks)
        processed = 0
        errors = 0
        
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            # Submit tracks in batches
            futures = []
            for i in range(0, len(tracks), Config.BATCH_SIZE):
                batch = tracks[i:i + Config.BATCH_SIZE]
                for track in batch:
                    future = executor.submit(self._classify_single_track_safe, track)
                    futures.append((future, track))
            
            # Collect results as they complete
            for future, track in futures:
                try:
                    category = future.result()
                    categorized[category].append(track)
                except Exception as e:
                    # If classification fails for this track, put in Misc
                    print(f"\n⚠️  Error classifying '{track['name']}': {e}")
                    categorized['Misc'].append(track)
                    category = 'Misc'
                    errors += 1
                
                processed += 1
                
                if progress_callback:
                    progress_callback(processed, total)
                
                if track_callback:
                    track_callback(track, category, processed, total)
        
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
        
        # Check persistent cache
        cached_category = self.cache_manager.get_classification(track_id)
        if cached_category:
            with self.cache_lock:
                self.session_cache[track_id] = cached_category
            return cached_category
        
        # Step 1: Quick metadata checks
        category = self._check_metadata_rules(track)
        if category:
            with self.cache_lock:
                self.session_cache[track_id] = category
            self.cache_manager.save_classification(track_id, category, 1.0)
            return category
        
        # Step 2: Use LLM for classification
        category, confidence = self.llm.classify_song(track)
        
        # Step 3: Check confidence threshold
        if confidence < Config.CONFIDENCE_THRESHOLD:
            category = "Misc"
        
        # Save to both caches (thread-safe)
        with self.cache_lock:
            self.session_cache[track_id] = category
        self.cache_manager.save_classification(track_id, category, confidence)
        
        return category
    
    def _check_metadata_rules(self, track: Dict) -> str:
        """
        Check if track matches any metadata-based rules for quick classification.
        Prioritizes artist-based detection and language detection.
        
        Args:
            track: Track metadata
            
        Returns:
            Category name if matched, None otherwise
        """
        # Rule 1: Check artist knowledge base (HIGHEST PRIORITY)
        artist_category = self._check_artist_knowledge(track)
        if artist_category:
            return artist_category
        
        # Rule 2: Detect language from track name
        lang_category = self._detect_language(track)
        if lang_category:
            return lang_category
        
        # Rule 3: Check for "Oldies" - Hindi songs before 2000 with classic artists
        if self._is_oldies(track):
            return "Oldies"
        
        # Rule 4: Check for instrumental/phonk by genre
        if self._is_instrumental_or_phonk(track):
            return "Phonk/Instrumental"
        
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
            
            # Punjabi artists
            'diljit dosanjh': 'Punjabi',
            'sidhu moose wala': 'Punjabi',
            'karan aujla': 'Punjabi',
            'ap dhillon': 'Punjabi',
            'guru randhawa': 'Punjabi',
            'ammy virk': 'Punjabi',
            'hardy sandhu': 'Punjabi',
            'parmish verma': 'Punjabi',
            'jasmine sandlas': 'Punjabi',
            'jass manak': 'Punjabi',
            'khan bhaini': 'Punjabi',
            'shubh': 'Punjabi',
            
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
    
    def _detect_language_from_text(self, text: str) -> str:
        """
        Detect language from text using character patterns.
        This is a simple heuristic, not foolproof.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language or None
        """
        # Devanagari script (Hindi)
        if re.search(r'[\u0900-\u097F]', text):
            return 'Hindi'
        
        # Gurmukhi script (Punjabi)
        if re.search(r'[\u0A00-\u0A7F]', text):
            return 'Punjabi'
        
        return None

