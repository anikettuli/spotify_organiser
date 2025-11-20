"""Gemini-based music classifier with 14-category genre and mood classification."""
import re
import time
import json
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from config import Config
from rule_classifier import RuleClassifier

genai: Any

try:
    import google.generativeai as genai
    _HAS_GOOGLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    _HAS_GOOGLE = False


class LLMClassifier:
    """Music classifier using Gemini 2.0 Flash with comprehensive genre and mood detection."""

    def __init__(self):
        """Initialize Gemini API and rule-based classifier."""
        self.gemini_model: Optional[Any] = None
        self.rule_classifier = RuleClassifier()
        
        if _HAS_GOOGLE and not Config.USE_MOCKS:
            try:
                if Config.GOOGLE_API_KEY:
                    genai.configure(api_key=Config.GOOGLE_API_KEY)
                    # Configure tools for grounding if available
                    try:
                        # Try enabling Google Search using protos to avoid ambiguity
                        # We use the nested class genai.protos.Tool.GoogleSearch
                        tool = genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())
                        
                        self.gemini_model = genai.GenerativeModel(
                            Config.GEMINI_MODEL,
                            tools=[tool],
                            generation_config={
                                'temperature': 0.1,
                                'response_mime_type': 'application/json',
                            }
                        )
                        print(f"✅ Using {Config.GEMINI_MODEL} for classification (with Grounding enabled)")
                    except Exception as e:
                        print(f"⚠️  Failed to initialize Gemini with Grounding: {e}")
                        print("   Falling back to standard classification without grounding.")
                        self.gemini_model = genai.GenerativeModel(
                            Config.GEMINI_MODEL,
                            generation_config={
                                'temperature': 0.1,
                                'response_mime_type': 'application/json',
                            }
                        )
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
        """
        Classify multiple songs using hybrid approach:
        1. Try rule-based classification first (fast, deterministic)
        2. Use LLM for ambiguous cases only
        """
        if not tracks:
            return []
        
        # Phase 1: Rule-based pre-classification
        print(f"🎯 Running rule-based pre-classification on {len(tracks)} tracks...")
        rule_classified = []
        llm_needed = []
        llm_needed_indices = []
        
        for i, track in enumerate(tracks):
            rule_result = self.rule_classifier.classify(track)
            if rule_result:
                rule_classified.append((i, rule_result))
            else:
                llm_needed.append(track)
                llm_needed_indices.append(i)
        
        print(f"   ✅ {len(rule_classified)} tracks classified by rules ({len(rule_classified)/len(tracks)*100:.1f}%)")
        print(f"   🤖 {len(llm_needed)} tracks need LLM classification ({len(llm_needed)/len(tracks)*100:.1f}%)")
        
        # Initialize results array
        results: List[Tuple[str, float]] = [('World', 0.5)] * len(tracks)
        
        # Fill in rule-based results
        for idx, result in rule_classified:
            results[idx] = result
        
        # Phase 2: LLM classification for remaining tracks
        if not llm_needed or not self.gemini_model:
            # Use fallback for LLM-needed tracks if no model
            if llm_needed and not self.gemini_model:
                for idx in llm_needed_indices:
                    results[idx] = self._fallback_classify(tracks[idx])
            return results
        
        try:
            # Process only LLM-needed tracks
            batch_size = Config.BATCH_SIZE
            chunks = [llm_needed[i:i + batch_size] for i in range(0, len(llm_needed), batch_size)]
            
            llm_results: List[Optional[List[Tuple[str, float]]]] = [None] * len(chunks)

            # Number of parallel Gemini requests (configurable via Config.PARALLEL_WORKERS)
            parallel_workers = Config.PARALLEL_WORKERS
            print(f"🔄 Processing {len(llm_needed)} LLM-needed tracks in {len(chunks)} batches ({parallel_workers} parallel calls)...")
            
            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                for i in range(0, len(chunks), parallel_workers):
                    group_end = min(i + parallel_workers, len(chunks))
                    group_indices = range(i, group_end)
                    group_chunks = [chunks[j] for j in group_indices]
                    
                    print(f"   🚀 Launching batches {i+1}-{group_end}...")
                    
                    # Submit group
                    futures = {executor.submit(self._classify_batch_internal, chunk): idx for idx, chunk in zip(group_indices, group_chunks)}
                    
                    # Collect results for this group
                    for future in futures:
                        idx = futures[future]
                        try:
                            llm_results[idx] = future.result()
                        except Exception as e:
                            print(f"   ⚠️ Batch {idx+1} failed: {e}")
                            llm_results[idx] = [self._fallback_classify(t) for t in chunks[idx]]
                    
                    # Minimal wait (1s) just to be polite, even with high limits
                    if group_end < len(chunks):
                        time.sleep(1)
            
            # Merge LLM results back into main results array
            llm_flat_results = []
            for r in llm_results:
                if r:
                    llm_flat_results.extend(r)
            
            # Apply confidence boosting (rules + LLM agreement)
            for i, llm_result in enumerate(llm_flat_results):
                original_idx = llm_needed_indices[i]
                track = llm_needed[i]
                category, confidence = llm_result
                
                # Boost confidence if rules agree
                boosted_category, boosted_confidence = self.rule_classifier.get_confidence_boost(
                    track, category, confidence
                )
                results[original_idx] = (boosted_category, boosted_confidence)
                    
            return results
        except Exception as e:
            print(f"\n⚠️  LLM Classification failed: {e}")
            # Fill remaining LLM-needed indices with fallback
            for idx in llm_needed_indices:
                if results[idx] == ('World', 0.5):  # Not yet classified
                    results[idx] = self._fallback_classify(tracks[idx])
            return results
    
    def _classify_batch_internal(self, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Internal batch classification with retry logic."""
        if not self.gemini_model:
            raise RuntimeError("Gemini model not initialized")

        prompt = self._build_batch_prompt(tracks)
        
        max_retries = 3
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
                if hasattr(response, 'text'):
                    try:
                        response_text = response.text.strip()
                        return self._parse_batch_response(response_text, tracks)
                    except Exception:
                        # If response.text fails, check candidates directly
                        pass
                
                if hasattr(response, 'candidates') and response.candidates:
                    # Try to extract from candidates
                    candidate = response.candidates[0]
                    # Check finish reason
                    if candidate.finish_reason == 2: # MAX_TOKENS
                        print("   ⚠️  Batch hit token limit (Finish Reason: MAX_TOKENS). Reducing batch size recommended.")
                    
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        response_text = candidate.content.parts[0].text.strip()
                        return self._parse_batch_response(response_text, tracks)
                
                raise Exception(f"No valid response text found. Finish Reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    # Exponential backoff with a higher base for 3 Pro
                    wait_time = 45 * (attempt + 1)
                    print(f"   ⚠️  Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                elif attempt < max_retries - 1:
                    time.sleep(2.0 * (attempt + 1))
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
            release_date = track.get('release_date', '')
            year = release_date[:4] if release_date else 'Unknown'
            
            # New metadata
            genres = ', '.join(track.get('genres', []))
            
            # Track details
            popularity = track.get('popularity', 0)
            explicit = "Explicit" if track.get('explicit') else "Clean"
            duration_ms = track.get('duration_ms', 0)
            duration_min = f"{duration_ms / 60000:.1f}m"
            
            songs_text.append(f"{i}. \"{title}\" by {artists} (Album: {album}) [{year}]\n   "
                              f"Info: {popularity}% pop, {explicit}, {duration_min}\n   "
                              f"Genres: {genres}")
        
        return f"""You are an expert music classifier analyzing songs that couldn't be confidently classified by rule-based systems. These are AMBIGUOUS cases requiring your expertise.

**YOUR TASK:** Classify each song into ONE of 14 categories based on language, genre, artist, and mood.

**METADATA GUIDE:**
- **Genres**: Spotify artist genres (most reliable signal - USE THIS FIRST)
- **Artist Name**: Strong indicator of language/region (e.g., non-English names often indicate regional music)
- **Popularity**: >80 = Mainstream, <30 = Niche/Underground
- **Explicit**: Often indicates Hip-Hop/Rap
- **Title Keywords**: Look for language-specific words or mood indicators

**14 CATEGORIES WITH EXAMPLES:**

**LANGUAGE-BASED CATEGORIES (Primary):**
1. **"Punjabi - Hype/Fun"** - Punjabi language, upbeat/party vibe
   - Genres: punjabi, bhangra, desi hip hop
   - Example: "295" by Sidhu Moose Wala, "Excuses" by AP Dhillon

2. **"Hindi - Party/Dance"** - Hindi club bangers, high energy
   - Genres: bollywood + (dance/edm/hip hop)
   - Example: "Kala Chashma", "Nashe Si Chadh Gayi"

3. **"Hindi - Bollywood/Melodic"** - Hindi romantic/melodic songs
   - Genres: filmi, bollywood, indian indie
   - Example: "Tum Hi Ho" by Arijit Singh, "Agar Tum Saath Ho"

4. **"English - Pop"** - English mainstream pop/dance
   - Genres: pop, dance pop, electropop, edm
   - Example: "Blinding Lights", "Levitating", "Anti-Hero"

5. **"English - Hip-Hop"** - English rap/trap (not aggressive gym music)
   - Genres: hip hop, trap, rap
   - Example: "God's Plan", "SICKO MODE", "The Box"

6. **"English - R&B"** - Smooth R&B/soul, slower tempo
   - Genres: r&b, soul, neo soul
   - Example: "Earned It", "Location", "Best Part"

7. **"English - Rock/Alt"** - Rock/alternative/indie rock
   - Genres: rock, alternative, indie, metal
   - Example: "Do I Wanna Know?", "In the End", "Radioactive"

8. **"Oldies"** - Hindi/Urdu classics ONLY from pre-1990
   - Must be from golden era (Kishore Kumar, Lata, Rafi)
   - Example: "Mere Sapno Ki Rani", "Kabhi Kabhie"

9. **"World"** - Non-English/Hindi/Punjabi languages
   - Genres: french pop, k-pop, latin, reggaeton, afrobeat, arabic, turkish
   - Example: "Dernière Danse" (French), "Dynamite" (K-pop), "Despacito" (Spanish)

**MOOD OVERRIDES (Higher Priority):**
10. **"Sad/Emotional"** - Heartbreak songs ANY language, melancholic mood
    - Keywords: sad, heartbreak, miss, lonely, tears, pain
    - Example: "Someone You Loved", "Chal Tere Ishq Mein", "Lucid Dreams"

11. **"Gym - Phonk"** - Dark phonk with cowbell/drift vibes
    - Genres: phonk, brazilian phonk
    - Example: "Murder in My Mind", "DVRST - Close Eyes"

12. **"Gym - Hype"** - Aggressive workout rap (NOT regular hip-hop)
    - Must have intense energy for workouts
    - Example: "Walk Em Down", "Godzilla", "NEFFEX"

13. **"Chill/Lofi"** - Calm instrumental/lofi/study music
    - Genres: lofi, chillhop, ambient
    - Example: "3 A.M. Study Session", instrumental chill beats

14. **"Soundtracks"** - Epic cinematic/orchestral scores
    - Genres: soundtrack, score, orchestral
    - Example: "Time" (Hans Zimmer), "No Time for Caution"

**CLASSIFICATION DECISION TREE:**
1. **Check GENRES first** (most reliable): If genre contains "punjabi/bhangra" → Punjabi. "bollywood/filmi" → Hindi. "k-pop/french/latin" → World. "phonk" → Gym-Phonk. "lofi" → Chill/Lofi.
2. **Check MOOD keywords** in title: "sad/heartbreak/lonely/tears" → Sad/Emotional (overrides language).
3. **Check ARTIST NAME** for language clues: Indian/South Asian names usually → Hindi/Punjabi. Korean names → World (K-pop).
4. **Check TITLE LANGUAGE**: If Punjabi words (da, di, jatt, yaari) → Punjabi. Hindi words (hai, mera, tera, dil) → Hindi.
5. **Default to genre-based**: Hip-hop/rap → English Hip-Hop. Pop → English Pop. Rock → English Rock/Alt.

**CRITICAL RULES:**
✅ **"World"** is ONLY for non-English/non-Hindi/non-Punjabi languages (French, Spanish, Korean, Arabic, etc.)
✅ **Sad mood OVERRIDES language** (sad Punjabi song → Sad/Emotional, NOT Punjabi)
✅ **"Gym - Hype"** needs AGGRESSIVE energy (NOT regular hip-hop)
✅ **"Oldies"** is ONLY Hindi pre-1990 (NO English oldies)
✅ **Use genres as primary signal** when available

**Songs to classify:**
{chr(10).join(songs_text)}

**OUTPUT FORMAT:**
Return ONLY a JSON array with this exact structure:
[{{"index": 0, "category": "Punjabi - Hype/Fun", "confidence": 0.90}}, {{"index": 1, "category": "English - Pop", "confidence": 0.85}}, ...]

**Confidence guidelines:**
- 0.95: Genre tag perfectly matches category
- 0.90: Artist is well-known for this category
- 0.85: Multiple signals point to same category
- 0.75: Reasonable inference from available data
- 0.65: Uncertain, best guess

Be decisive. Avoid "World" unless the song is clearly in a non-English/Hindi/Punjabi language."""

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
