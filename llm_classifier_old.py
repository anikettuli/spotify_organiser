"""LLM-based song classifier using vLLM with a lightweight fallback.

This module will attempt to use an OpenAI-compatible client (vLLM). If the
dependency is missing or `Config.USE_MOCKS` is enabled, a simple deterministic
rule-based fallback classifier is used instead. The fallback is intentionally
minimal to keep the code small and dependency-free for demos.
"""
import re
import time
from typing import Dict, List, Tuple
from config import Config

_HAS_OPENAI = True
try:
    from openai import OpenAI
except Exception:
    _HAS_OPENAI = False

_HAS_LANGDETECT = True
try:
    from langdetect import detect, LangDetectException
except Exception:
    _HAS_LANGDETECT = False


class LLMClassifier:
    """Classifier that uses vLLM when available, else a rule-based fallback."""

    def __init__(self):
        self.model = Config.VLLM_MODEL
        self.client = None
        if _HAS_OPENAI and not Config.USE_MOCKS:
            try:
                self.client = OpenAI(
                    base_url=Config.VLLM_ENDPOINT,
                    api_key="dummy",
                    timeout=60.0,
                    max_retries=3,
                )
            except Exception:
                self.client = None

    def classify_song(self, track: Dict) -> Tuple[str, float]:
        """Classify a single song and return (category, confidence).

        Uses remote LLM when available; otherwise falls back to a simple
        heuristic that looks at genres, artist names, release year, and title
        keywords.
        """
        # Use real LLM if available
        if self.client:
            prompt = self._build_prompt(track)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a music classification expert."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        max_tokens=100,
                    )
                    response_text = response.choices[0].message.content.strip()
                    return self._parse_response(response_text)
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep((2 ** attempt) * 0.5)
                    else:
                        print(f"Error classifying track {track.get('name')}: {e}")
                        return "Misc", 0.0

        # Fallback rule-based classifier
        return self._fallback_classify(track)

    def _fallback_classify(self, track: Dict) -> Tuple[str, float]:
        """Lightweight deterministic classifier used when LLM is unavailable."""
        name = (track.get('name') or '').lower()
        artists = [a.lower() for a in track.get('artists', [])]
        genres = [g.lower() for g in track.get('genres', [])]
        markets = [m.upper() for m in track.get('markets', [])]

        # Oldies by year or classic artist names
        if track.get('release_date'):
            try:
                year = int(track['release_date'][:4])
                if year < 2000:
                    for a in artists:
                        if any(c in a for c in ['lata', 'rafi', 'kishore', 'asha', 'mukesh', 'talat']):
                            return 'Oldies', 0.95
            except Exception:
                pass

        # Genre-based checks
        for g in genres:
            if 'bollywood' in g or 'hindi' in g:
                return 'Hindi', 0.92
            if 'punjabi' in g:
                return 'Punjabi', 0.92
            if 'phonk' in g or 'instrumental' in g or 'lofi' in g:
                return 'Phonk/Instrumental', 0.9

        # Title/artist heuristics
        if any(ch in name for ch in ['tum hi', 'tere', 'aaja', 'dil', 'pyaar', 'pyar', 'hai']):
            return 'Hindi', 0.85
        if any('singh' in a for a in artists):
            return 'Hindi', 0.8

        # Market hints
        if any(m in markets for m in ['IN', 'PK']):
            return 'Hindi', 0.7

        # Default to English with moderate confidence
        return 'English', 0.6

    def classify_batch(self, tracks: List[Dict]) -> List[Tuple[str, float]]:
        results = []
        for t in tracks:
            results.append(self.classify_song(t))
        return results

    def _detect_language(self, text: str) -> str:
        """Detect language of text using langdetect."""
        if not _HAS_LANGDETECT or not text:
            return "unknown"
        try:
            from langdetect import detect
            lang_code = detect(text)
            # Map language codes to our categories
            lang_map = {
                'hi': 'Hindi',
                'pa': 'Punjabi', 
                'ur': 'Hindi',  # Urdu songs often Hindi/Punjabi
                'en': 'English'
            }
            return lang_map.get(lang_code, lang_code)
        except Exception:
            return "unknown"

    def _build_prompt(self, track: Dict) -> str:
        # Extract year
        year = "Unknown"
        year_int = None
        if track.get('release_date'):
            year = track['release_date'][:4] if len(track['release_date']) >= 4 else track['release_date']
            try:
                year_int = int(year)
            except:
                pass
        
        # Artists (handle collaborations)
        artists_list = track.get('artists', [])
        artists_str = ", ".join(artists_list[:3])  # Limit to first 3 artists
        primary_artist = artists_list[0] if artists_list else "Unknown"
        
        # Genres from Spotify
        genres = track.get('genres', [])
        genres_str = ", ".join(genres[:5]) if genres else "No genre data"
        
        # Title analysis
        title = track.get('name', '')
        title_lower = title.lower()
        
        # Detect patterns in title
        has_hindi_words = any(w in title_lower for w in ['dil', 'pyar', 'pyaar', 'tere', 'mera', 'tera', 'hai', 'tum', 'tu'])
        has_punjabi_words = any(w in title_lower for w in ['jatt', 'patola', 'gabru', 'kudi', 'pind', 'viah', 'gallan'])
        has_instrumental = any(w in title_lower for w in ['instrumental', 'remix', 'beat', 'phonk', 'bgm', 'theme'])
        
        # Build artist intelligence string
        artist_hints = []
        artist_lower = primary_artist.lower()
        
        # Known Punjabi artists
        if any(name in artist_lower for name in ['karan aujla', 'sidhu moose', 'diljit', 'ap dhillon', 'shubh', 'jordan sandhu', 'arjan dhillon', 'gur sidhu', 'cheema']):
            artist_hints.append("⭐ PUNJABI ARTIST")
        
        # Known Hindi/Bollywood artists
        elif any(name in artist_lower for name in ['arijit', 'shreya', 'badshah', 'honey singh', 'yo yo', 'neha kakkar', 'pritam', 'vishal', 'shekhar']):
            artist_hints.append("⭐ HINDI/BOLLYWOOD ARTIST")
        
        # Known English artists
        elif any(name in artist_lower for name in ['travis scott', 'drake', 'weeknd', 'kanye', 'post malone', 'billie', 'lady gaga']):
            artist_hints.append("⭐ ENGLISH ARTIST")
        
        # Classic artists
        elif any(name in artist_lower for name in ['lata', 'rafi', 'kishore', 'asha bhosle', 'mukesh']):
            artist_hints.append("⭐ CLASSIC/OLDIES ARTIST")
        
        artist_intelligence = " ".join(artist_hints) if artist_hints else "Unknown artist style"
        
        # Market analysis
        markets = track.get('markets', [])
        is_south_asian = any(m in markets for m in ['IN', 'PK', 'BD'])
        
        # Build contextual hints
        hints = []
        if has_hindi_words:
            hints.append("📌 Title contains Hindi words")
        if has_punjabi_words:
            hints.append("� Title contains Punjabi words")
        if has_instrumental:
            hints.append("📌 Likely instrumental/remix")
        if year_int and year_int < 2000:
            hints.append("📌 Pre-2000 release")
        if is_south_asian:
            hints.append("📌 South Asian market")
        
        hints_str = "\n".join(hints) if hints else "No strong hints"

        prompt = f"""You are a music expert. Classify this song CONFIDENTLY based on artist identity.

🎵 SONG: "{title}"
👤 PRIMARY ARTIST: {primary_artist}
{artist_intelligence}

📅 Year: {year}
💿 Album: {track.get('album', 'N/A')}
🎸 Genres: {genres_str}

🔍 CONTEXTUAL HINTS:
{hints_str}

🎯 CATEGORIES (choose ONE):
• Punjabi - Punjabi language songs (Karan Aujla, Diljit, AP Dhillon, Sidhu Moose Wala, Shubh style)
• Hindi - Hindi/Bollywood songs (Arijit Singh, Badshah, Yo Yo Honey Singh style)
• English - English language songs (Western pop/hip-hop/rock)
• Phonk/Instrumental - Instrumental, beats, remixes, phonk, no vocals
• Oldies - Pre-2000 classic Hindi/Urdu songs
• Misc - OTHER languages or truly unclear

⚡ DECISION RULES:
1. ARTIST = PRIMARY SIGNAL (if you recognize artist style, use it)
2. If artist unknown, use title words + genre + year
3. Be BOLD - aim for 0.85+ confidence
4. Only use "Misc" if TRULY unclear (rare)

OUTPUT FORMAT (exactly):
Category: [one category]
Confidence: [0.00-1.00]
"""
        return prompt

    def _parse_response(self, response_text: str) -> Tuple[str, float]:
        category = 'Misc'
        confidence = 0.5
        cat_m = re.search(r'Category:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE)
        if cat_m:
            raw = cat_m.group(1).strip().lower()
            # Simple normalization
            if 'old' in raw or 'classic' in raw:
                category = 'Oldies'
            elif 'phonk' in raw or 'instrumental' in raw:
                category = 'Phonk/Instrumental'
            elif 'punjabi' in raw:
                category = 'Punjabi'
            elif 'hindi' in raw:
                category = 'Hindi'
            elif 'english' in raw:
                category = 'English'
            else:
                category = 'Misc'

        conf_m = re.search(r'Confidence:\s*([0-9.]+)', response_text, re.IGNORECASE)
        if conf_m:
            try:
                confidence = float(conf_m.group(1))
                confidence = max(0.0, min(1.0, confidence))
            except Exception:
                confidence = 0.5

        return category, confidence

    def _normalize_category(self, raw_category: str) -> str:
        """Normalize category name to match Config.CATEGORIES (kept for tests)."""
        raw_lower = raw_category.lower().strip()
        category_map = {
            'oldies': 'Oldies',
            'old': 'Oldies',
            'classic': 'Oldies',
            'phonk/instrumental': 'Phonk/Instrumental',
            'phonk': 'Phonk/Instrumental',
            'instrumental': 'Phonk/Instrumental',
            'punjabi': 'Punjabi',
            'hindi': 'Hindi',
            'english': 'English',
            'uncertain': 'Misc',
            'misc': 'Misc',
            'unknown': 'Misc'
        }

        for key, value in category_map.items():
            if key in raw_lower:
                return value

        return 'Misc'

