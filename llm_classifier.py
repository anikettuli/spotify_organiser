"""Gemini-based music classifier with 14-category genre and mood classification."""
import re
import time
import json
import asyncio
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from config import Config

try:
    import google.generativeai as genai
    _HAS_GOOGLE = True
except ImportError:
    _HAS_GOOGLE = False


class LLMClassifier:
    """Music classifier using Gemini 2.0 Flash with comprehensive genre and mood detection."""

    def __init__(self):
        """Initialize Gemini API."""
        self.gemini_model = None
        
        if _HAS_GOOGLE and not Config.USE_MOCKS:
            try:
                if Config.GOOGLE_API_KEY:
                    genai.configure(api_key=Config.GOOGLE_API_KEY)
                    self.gemini_model = genai.GenerativeModel(
                        Config.GEMINI_MODEL,
                        generation_config={
                            'temperature': 0.1,
                            'response_mime_type': 'application/json',
                        }
                    )
                    print(f"✅ Using {Config.GEMINI_MODEL} for classification")
            except Exception as e:
                print(f"⚠️  Failed to initialize Gemini: {e}")
                self.gemini_model = None

    def classify_tracks(self, tracks: List[Dict], track_callback=None) -> Dict[str, List[Dict]]:
        """
        Classify a list of tracks and organize them by category.
        
        Args:
            tracks: List of track dictionaries
            track_callback: Optional callback function(track, category, processed_count, total_count)
            
        Returns:
            Dictionary mapping categories to lists of tracks
        """
        categorized_tracks = {}
        total_tracks = len(tracks)
        
        # Process in batches using the existing batch mechanism
        # We process all at once using classify_batch which handles its own chunking
        print(f"🚀 Starting classification for {total_tracks} tracks...")
        
        results = self.classify_batch(tracks)
        
        for i, (category, confidence) in enumerate(results):
            track = tracks[i]
            
            # Store confidence in track for reference
            track['classification_confidence'] = confidence
            track['classification_category'] = category
            
            # Add to categorized dictionary
            if category not in categorized_tracks:
                categorized_tracks[category] = []
            categorized_tracks[category].append(track)
            
            # Handle low confidence
            if confidence < Config.CONFIDENCE_THRESHOLD:
                track['_low_confidence_guess'] = category
                # We still keep it in the category, but main.py might filter it or warn
                # Alternatively, move to 'Misc' if very low?
                # For now, we respect the classifier's choice but mark it.
            
            # Invoke callback
            if track_callback:
                track_callback(track, category, i + 1, total_tracks)
                
        return categorized_tracks

    def classify_batch(self, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Classify multiple songs with 8 parallel API calls."""
        if not self.gemini_model or not tracks:
            return [self._fallback_classify(track) for track in tracks]
        
        try:
            # Split tracks into 8 chunks for parallel processing
            chunk_size = (len(tracks) + 7) // 8  # Ceiling division by 8
            chunks = [tracks[i:i + chunk_size] for i in range(0, len(tracks), chunk_size)]
            
            # Process chunks in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(self._classify_batch_internal, chunk) for chunk in chunks]
                results_chunks = [future.result() for future in futures]
            
            # Flatten results
            results = []
            for chunk_results in results_chunks:
                results.extend(chunk_results)
            
            return results
        except Exception as e:
            print(f"\n⚠️  Parallel classification failed: {e}")
            return [self._fallback_classify(track) for track in tracks]
    
    def _classify_batch_internal(self, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Internal batch classification with retry logic."""
        prompt = self._build_batch_prompt(tracks)
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.1,
                        'max_output_tokens': 15000,
                    },
                    safety_settings={
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                    }
                )
                
                # Safely get response text
                if hasattr(response, 'text') and response.text:
                    response_text = response.text.strip()
                    return self._parse_batch_response(response_text, tracks)
                elif hasattr(response, 'candidates') and response.candidates:
                    # Try to extract from candidates
                    candidate = response.candidates[0]
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        response_text = candidate.content.parts[0].text.strip()
                        return self._parse_batch_response(response_text, tracks)
                
                raise Exception("No valid response text found")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    raise e
        
        raise Exception("Max retries exceeded")
    
    def _build_batch_prompt(self, tracks: List[Dict]) -> str:
        """Build comprehensive prompt for batch classification."""
        songs_text = []
        for i, track in enumerate(tracks):
            title = track.get('name', 'Unknown')
            artists_raw = track.get('artists', [])
            # Handle both list of strings and list of dicts
            if artists_raw and isinstance(artists_raw[0], dict):
                artists = ', '.join([a.get('name', '') for a in artists_raw])
            else:
                artists = ', '.join(artists_raw) if isinstance(artists_raw, list) else str(artists_raw)
            album = track.get('album', 'Unknown')
            year = str(track.get('year', 'Unknown'))
            
            songs_text.append(f"{i}. \"{title}\" by {artists} (Album: {album}) [{year}]")
        
        return f"""You are an expert music classifier. Analyze each song carefully and classify into ONE category.

**14 CATEGORIES:**

**LANGUAGE-BASED (Check artist/title first):**
1. "Punjabi - Hype/Fun" - Punjabi language songs. Artists: Sidhu Moose Wala, Karan Aujla, AP Dhillon, Shubh, Diljit Dosanjh, Ammy Virk, Jassa Dhillon, Arjan Dhillon, Navaan Sandhu, Tegi Pannu, Khan Bhaini, Sultaan.

2. "Hindi - Party/Dance" - High-energy Hindi club/party tracks. Artists: Badshah, Yo Yo Honey Singh, Divine, KR$NA, Raftaar, Seedhe Maut. Songs like "Chammak Challo", "Kajra Re", "Hookah Bar".

3. "Hindi - Bollywood/Melodic" - Hindi film songs, indie, romantic ballads. Artists: Arijit Singh, Pritam, A.R. Rahman, Mohit Chauhan, Atif Aslam, Vishal-Shekhar, Shankar-Ehsaan-Loy, Salim-Sulaiman, Amit Trivedi.

4. "English - Pop" - English pop/dance/EDM. Artists: The Weeknd (most songs), Dua Lipa, Lady Gaga, Harry Styles, Taylor Swift, Ariana Grande, Post Malone, Doja Cat, Calvin Harris, David Guetta.

5. "English - Hip-Hop" - English rap/trap (moderate energy). Artists: Drake, Eminem, Kanye West, Travis Scott, J. Cole, Future, 21 Savage, Kendrick Lamar, Jack Harlow, Lil Baby, Don Toliver.

6. "English - R&B" - Smooth R&B/soul. Artists: The Weeknd (R&B tracks), Frank Ocean, SZA, ZAYN, Khalid, 6LACK, Brent Faiyaz, Beyoncé (slow tracks).

7. "English - Rock/Alt" - Rock/alternative/indie. Artists: Arctic Monkeys, Linkin Park, Imagine Dragons, Coldplay, Nirvana, Foo Fighters, The Neighbourhood, Radiohead, Green Day.

8. "Oldies" - ONLY Hindi classics pre-1990s. Artists: Kishore Kumar, Lata Mangeshkar, Mohammed Rafi, Mukesh, Nusrat Fateh Ali Khan. NO English oldies.

9. "World" - Songs in OTHER languages (French, Spanish, Russian, Arabic, Turkish, K-pop, etc.). Artists: Indila, MORGENSHTERN, Bad Bunny, BLACKPINK.

**MOOD OVERRIDES (Check vibe/energy):**
10. "Sad/Emotional" - Sad/breakup songs ANY language. Keywords: heartbreak, lonely, tears, lost love, emotional. Artists: Harnoor, Billie Eilish, XXXTENTACION, Juice WRLD, sad Arijit Singh tracks.

11. "Gym - Phonk" - Dark aggressive phonk ONLY. Artists: Kordhell, DVRST, KSLV Noh, Dxrk ダーク, MoonDeity, ONIMXRU. Keywords: "phonk", "drift", aggressive cowbell.

12. "Gym - Hype" - Aggressive workout English rap/trap. Artists: NLE Choppa, Pop Smoke, CJ, NEFFEX, Lil Pump. Must have aggressive energy.

13. "Chill/Lofi" - Lofi/ambient/study beats. Keywords: "lofi", "chill", "ambient", "slowed + reverb" (soft). Artists: Lofi Fruits Music, instrumental chill tracks.

14. "Soundtracks" - Epic movie/game scores ONLY. Artists: Hans Zimmer, Ludwig Göransson, Michael Giacchino, Anirudh Ravichander (BGM), Ravi Basrur.

**CLASSIFICATION PRIORITY:**
1. Check if SAD → "Sad/Emotional" (override language)
2. Check if PHONK/GYM → "Gym - Phonk" or "Gym - Hype"
3. Check LANGUAGE → Punjabi/Hindi/English categories
4. Check if CHILL/LOFI → "Chill/Lofi"
5. Check if SOUNDTRACK → "Soundtracks"
6. Default foreign language → "World"

**CRITICAL RULES:**
- Artist name = PRIMARY indicator (Karan Aujla = always Punjabi, Badshah = Hindi Party)
- "World" is ONLY for non-English/Hindi/Punjabi languages
- Sad songs override language categories
- English songs before 2000 still go to English-Pop/Rock (NOT Oldies)
- Soundtracks are ONLY epic/orchestral (NOT chill instrumentals)

**Songs to classify:**
{chr(10).join(songs_text)}

**Instructions:**
1. Analyze artist origin, language, genre, mood, and energy level
2. Prioritize mood categories (Sad, Gym, Chill, Soundtracks) if applicable
3. Return JSON array: [{{"index": 0, "category": "Punjabi - Hype/Fun", "confidence": 0.95}}, ...]
4. Be decisive - use high confidence (0.85-0.95) for clear classifications
5. Think carefully about cross-cultural collabs and mood overrides

Return ONLY the JSON array, no other text."""

    def _parse_batch_response(self, response_text: str, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Parse Gemini JSON response into list of (category, confidence) tuples."""
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                results_json = json.loads(json_match.group(0))
                
                # Map results back to track order
                results = [('World', 0.5)] * len(tracks)  # Default fallback
                for item in results_json:
                    idx = item.get('index', -1)
                    category = item.get('category', 'World')
                    confidence = float(item.get('confidence', 0.7))
                    
                    if 0 <= idx < len(tracks) and category in Config.CATEGORIES:
                        results[idx] = (category, confidence)
                
                return results
        except Exception as e:
            print(f"\n⚠️  JSON parse error: {e}")
        
        # Fallback to basic classification
        return [self._fallback_classify(track) for track in tracks]
    
    def _fallback_classify(self, track: Dict) -> Tuple[str, float]:
        """Simple fallback classification when Gemini fails."""
        title = track.get('name', '').lower()
        artists_raw = track.get('artists', [])
        # Handle both list of strings and list of dicts
        if artists_raw and isinstance(artists_raw[0], dict):
            artists = ', '.join([a.get('name', '') for a in artists_raw]).lower()
        else:
            artists = ', '.join(artists_raw).lower() if isinstance(artists_raw, list) else str(artists_raw).lower()
        
        # Check for known Punjabi artists
        punjabi_artists = [
            'sidhu moose wala', 'karan aujla', 'ap dhillon', 'shubh', 'diljit dosanjh',
            'ammy virk', 'jassa dhillon', 'tegi pannu', 'khan bhaini', 'arjan dhillon',
            'prem dhillon', 'jordan sandhu', 'harnoor', 'navaan sandhu'
        ]
        if any(artist in artists for artist in punjabi_artists):
            # Check if sad
            if any(word in title for word in ['sad', 'dil', 'yaad', 'pyar', 'miss']):
                return ('Sad/Emotional', 0.75)
            return ('Punjabi - Hype/Fun', 0.75)
        
        # Check for Hindi artists
        hindi_artists = [
            'badshah', 'honey singh', 'divine', 'kr$na', 'arijit singh',
            'pritam', 'a.r. rahman', 'atif aslam'
        ]
        if any(artist in artists for artist in hindi_artists):
            if any(word in title for word in ['sad', 'dil', 'tu', 'hai']):
                return ('Sad/Emotional', 0.75)
            if 'badshah' in artists or 'honey singh' in artists:
                return ('Hindi - Party/Dance', 0.75)
            return ('Hindi - Bollywood/Melodic', 0.75)
        
        # Check for English artists/genres
        english_pop = ['weeknd', 'dua lipa', 'harry styles', 'taylor swift']
        english_hiphop = ['eminem', 'drake', 'travis scott', 'future', 'kanye']
        english_rock = ['arctic monkeys', 'linkin park', 'queen', 'nirvana']
        
        if any(artist in artists for artist in english_pop):
            return ('English - Pop', 0.75)
        if any(artist in artists for artist in english_hiphop):
            return ('English - Hip-Hop', 0.75)
        if any(artist in artists for artist in english_rock):
            return ('English - Rock/Alt', 0.75)
        
        # Check for phonk/gym keywords
        if any(word in title for word in ['phonk', 'drift', 'slowed', 'cowbell']):
            return ('Gym - Phonk', 0.70)
        
        # Check for lofi/chill
        if any(word in title for word in ['lofi', 'chill', 'ambient', 'study']):
            return ('Chill/Lofi', 0.70)
        
        # Check for soundtracks
        soundtrack_artists = ['hans zimmer', 'ludwig göransson', 'john williams']
        if any(artist in artists for artist in soundtrack_artists):
            return ('Soundtracks', 0.75)
        
        # Default to World
        return ('World', 0.50)
    
    def classify_song(self, track: Dict) -> Tuple[str, float]:
        """Classify a single song (not recommended - use classify_batch instead)."""
        return self._fallback_classify(track)
