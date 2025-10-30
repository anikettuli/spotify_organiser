"""Enhanced LLM classifier with comprehensive artist database and year intelligence."""
import re
import time
import os
from typing import Dict, List, Tuple, Optional
from config import Config

_HAS_OPENAI = True
try:
    from openai import OpenAI
except Exception:
    _HAS_OPENAI = False

_HAS_GOOGLE = True
try:
    import google.generativeai as genai
except Exception:
    _HAS_GOOGLE = False


class LLMClassifier:
    """Classifier with enhanced artist intelligence and era detection."""

    def __init__(self):
        self.model = Config.VLLM_MODEL
        self.client = None
        self.gemini_model = None
        self.use_gemini = os.getenv('USE_GEMINI', '0') == '1'
        
        if self.use_gemini and _HAS_GOOGLE and not Config.USE_MOCKS:
            # Use Gemini
            try:
                api_key = os.getenv('GOOGLE_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.gemini_model = genai.GenerativeModel(
                        'gemini-2.5-flash-lite',
                        generation_config={
                            'temperature': 0.1,
                            'response_mime_type': 'application/json',
                        }
                    )
                    print("✅ Using Gemini 2.5 Flash Lite with thinking mode")
            except Exception as e:
                print(f"⚠️  Failed to initialize Gemini: {e}")
                self.gemini_model = None
        elif _HAS_OPENAI and not Config.USE_MOCKS:
            # Use vLLM/OpenAI
            try:
                self.client = OpenAI(
                    base_url=Config.VLLM_ENDPOINT,
                    api_key="dummy",
                    timeout=60.0,
                    max_retries=3,
                )
            except Exception:
                self.client = None

    def classify_batch(self, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Classify multiple songs in one request (batch processing)."""
        if not self.gemini_model or not tracks:
            # Fall back to individual classification
            return [self.classify_song(track) for track in tracks]
        
        # Build batch prompt
        prompt = self._build_batch_prompt(tracks)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.1,
                        'max_output_tokens': 8000,
                    }
                )
                response_text = response.text.strip()
                return self._parse_batch_response(response_text, tracks)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    # Fall back to individual classification
                    return [self._fallback_classify(track) for track in tracks]
        
        return [self._fallback_classify(track) for track in tracks]
    
    def classify_song(self, track: Dict) -> Tuple[str, float]:
        """Classify a single song and return (category, confidence)."""
        prompt = self._build_enhanced_prompt(track)
        
        if self.gemini_model:
            # Use Gemini
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.gemini_model.generate_content(
                        prompt,
                        generation_config={
                            'temperature': 0.1,
                            'max_output_tokens': 100,
                        }
                    )
                    response_text = response.text.strip()
                    return self._parse_response(response_text)
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        return self._fallback_classify(track)
        elif self.client:
            # Use vLLM/OpenAI
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a music expert specializing in South Asian and Western music."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        max_tokens=100,
                    )
                    response_text = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
                    return self._parse_response(response_text)
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep((2 ** attempt) * 0.5)
                    else:
                        print(f"Error classifying track {track.get('name')}: {e}")
                        return "Misc", 0.0
        
        return self._fallback_classify(track)

    def _build_enhanced_prompt(self, track: Dict) -> str:
        """Build prompt with comprehensive artist and year intelligence."""
        
        # Year analysis with era detection
        year = "Unknown"
        year_int = None
        era_signal = ""
        
        if track.get('release_date'):
            year = track['release_date'][:4] if len(track['release_date']) >= 4 else track['release_date']
            try:
                year_int = int(year)
                if year_int < 1990:
                    era_signal = "🕰️ 1980s/Earlier → OLDIES"
                elif year_int < 2000:
                    era_signal = "🕰️ 1990s → LIKELY OLDIES"
                elif year_int < 2010:
                    era_signal = "📻 2000s"
                elif year_int < 2020:
                    era_signal = "📱 2010s"
                else:
                    era_signal = "🆕 2020+"
            except:
                pass
        
        # Artist analysis
        artists_list = track.get('artists', [])
        primary_artist = artists_list[0] if artists_list else "Unknown"
        all_artists = ", ".join(artists_list[:3])
        
        # Get artist category match
        artist_match = self._get_artist_category(primary_artist, all_artists)
        
        # Title analysis with expanded keywords
        title = track.get('name', '')
        title_lower = title.lower()
        
        hindi_words = ['dil', 'pyar', 'tere', 'mera', 'hai', 'tum', 'tu', 'aaja', 'yaar', 'ishq', 'sanam', 'zindagi', 'judaai']
        punjabi_words = ['jatt', 'patola', 'gabru', 'kudi', 'pind', 'viah', 'gallan', 'punjab', 'panga', 'mitran', 'bande', 'yaar']
        instrumental_words = ['instrumental', 'remix', 'beat', 'phonk', 'bgm', 'theme', 'slowed', 'reverb', 'sped up', 'version']
        
        has_hindi = any(w in title_lower for w in hindi_words)
        has_punjabi = any(w in title_lower for w in punjabi_words)
        has_instrumental = any(w in title_lower for w in instrumental_words)
        
        # Build smart hints
        hints = []
        if artist_match:
            hints.append(f"✅ ARTIST: {artist_match} style confirmed")
        if year_int and year_int < 2000:
            hints.append(f"✅ ERA: Pre-2000 ({year}) → OLDIES category")
        if has_hindi:
            found = [w for w in hindi_words if w in title_lower][:3]
            hints.append(f"✅ HINDI words: {found}")
        if has_punjabi:
            found = [w for w in punjabi_words if w in title_lower][:3]
            hints.append(f"✅ PUNJABI words: {found}")
        if has_instrumental:
            hints.append("✅ INSTRUMENTAL markers detected")
        
        hints_text = "\n".join(hints) if hints else "⚠️ No strong signals - analyze carefully"
        
        prompt = f"""Classify this song using ARTIST + YEAR + TITLE keywords.

🎵 "{title}"
👤 {all_artists}
📅 {year} {era_signal}

🔍 SIGNALS DETECTED:
{hints_text}

🎯 CATEGORIES:
• Punjabi - Punjabi songs (Karan Aujla, Diljit, Sidhu Moose Wala, AP Dhillon style)
• Hindi - Hindi/Bollywood (Arijit, Pritam, Badshah, Honey Singh, KR$NA style)
• English - English/Western (Travis Scott, Drake, Weeknd, Radiohead, Arctic Monkeys)
• Phonk/Instrumental - Beats, remixes, instrumentals, no lyrics
• Oldies - Pre-2000 classics (Lata, Rafi, Kishore, old Hindi/Urdu)
• Misc - Other languages or unclear

RULES:
1. Artist match = USE IT (highest priority)
2. Pre-2000 + Hindi/Punjabi = OLDIES
3. Instrumental markers = Phonk/Instrumental
4. Title keywords = Hindi or Punjabi
5. Confidence 0.80+ required

Category: [one]
Confidence: [0.75-1.00]
"""
        return prompt

    def _get_artist_category(self, primary: str, all_artists: str) -> Optional[str]:
        """Check artist against comprehensive database."""
        text = f"{primary} {all_artists}".lower()
        
        # PUNJABI (50+ artists from your data)
        punjabi = ['karan aujla', 'sidhu moose wala', 'diljit dosanjh', 'diljit', 'ap dhillon', 
                   'shubh', 'guru randhawa', 'jordan sandhu', 'arjan dhillon', 'gur sidhu', 
                   'cheema y', 'navaan sandhu', 'chani nattan', 'amrinder gill', 'tegi pannu',
                   'gminxr', 'gurinder gill', 'sukha', 'intense', 'chinna', 'manni sandhu',
                   'gulab sidhu', 'jassa dhillon', 'dilpreet dhillon', 'harkirat sangha',
                   'amrit maan', 'satinder sartaaj', 'harnoor', 'bilal saeed', 'gurdas maan',
                   'jazzy b', 'sharry mann', 'mankirt aulakh', 'hardy sandhu', 'harrdy sandhu',
                   'parmish verma', 'jasmine sandlas', 'jass manak', 'khan bhaini', 'elly mangat',
                   'gurjas sidhu', 'ranjit bawa', 'babbu maan', 'surjit bindrakhia', 'tyson sidhu',
                   'roop bhullar', 'wazir patar', 'ekam sudhar', 'panther', 'bintu pabra']
        
        # HINDI (30+ artists)
        hindi = ['arijit singh', 'arijit', 'shreya ghoshal', 'badshah', 'yo yo honey singh',
                 'honey singh', 'pritam', 'vishal-shekhar', 'vishal dadlani', 'shekhar',
                 'a.r. rahman', 'kr$na', 'divine', 'raftaar', 'neha kakkar', 'sonu nigam',
                 'jubin nautiyal', 'armaan malik', 'ikka', 'king', 'seedhe maut', 'ritviz',
                 'nucleya', 'sunidhi chauhan', 'shaan', 'atif aslam', 'mohit chauhan',
                 'shilpa rao', 'sachin-jigar', 'vishal bhardwaj', 'rahat fateh', 'fotty seven',
                 'bali', 'enzo']
        
        # ENGLISH (40+ artists)
        english = ['travis scott', 'drake', 'the weeknd', 'weeknd', 'kanye west', 'post malone',
                   'billie eilish', 'lady gaga', 'kendrick lamar', 'future', 'don toliver',
                   'tyler the creator', 'lil wayne', 'frank ocean', 'radiohead', 'coldplay',
                   'arctic monkeys', 'nirvana', 'linkin park', 'the strokes', 'tame impala',
                   'metro boomin', '21 savage', 'nle choppa', 'lil tecca', 'g-eazy',
                   'soulja boy', 'bossman dlow', 'yeat', 'lil baby', 'of monsters and men',
                   'beach house', 'glass animals', 'mild high club', 'childish gambino',
                   'rolling stones', 'soundgarden', 'tears for fears']
        
        # OLDIES (15+ classic artists)
        oldies = ['lata mangeshkar', 'lata', 'mohammed rafi', 'rafi', 'kishore kumar', 'kishore',
                  'asha bhosle', 'asha', 'mukesh', 'talat mahmood', 'hemant kumar', 'manna dey',
                  'geeta dutt', 'shamshad begum', 'laxmikant-pyarelal', 'nusrat fateh ali khan',
                  'mehdi hassan']
        
        for a in punjabi:
            if a in text:
                return "Punjabi"
        for a in hindi:
            if a in text:
                return "Hindi"
        for a in english:
            if a in text:
                return "English"
        for a in oldies:
            if a in text:
                return "Oldies"
        
        return None

    def _parse_response(self, response_text: str) -> Tuple[str, float]:
        """Parse LLM response."""
        category = 'Misc'
        confidence = 0.5
        
        cat_m = re.search(r'Category:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE)
        if cat_m:
            raw = cat_m.group(1).strip().lower()
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
            except:
                confidence = 0.5

        return category, confidence

    def _fallback_classify(self, track: Dict) -> Tuple[str, float]:
        """Fallback when LLM unavailable."""
        # Check artist first
        artists = " ".join(track.get('artists', [])).lower()
        category = self._get_artist_category(artists, artists)
        if category:
            return category, 0.90
        
        # Check year
        if track.get('release_date'):
            try:
                year = int(track['release_date'][:4])
                if year < 2000:
                    return 'Oldies', 0.85
            except:
                pass
        
        # Default
        return 'Misc', 0.60

    def _build_batch_prompt(self, tracks: List[Dict]) -> str:
        """Build a batch classification prompt for multiple tracks."""
        prompt = """You are a music expert. Classify these songs into categories: English, Hindi, Punjabi, Phonk/Instrumental, Oldies, or Misc.

Categories:
- English: Western pop/rock/rap/electronic
- Hindi: Bollywood, Indian rap/pop
- Punjabi: Punjabi music (artists like Karan Aujla, Sidhu, AP Dhillon)
- Phonk/Instrumental: Phonk, lo-fi, instrumental, no vocals
- Oldies: Pre-2000 classics (Lata, Rafi, Kishore Kumar)
- Misc: Everything else (Russian, other languages, unclear)

Return JSON array with format: [{"index": 0, "category": "Hindi", "confidence": 0.85}, ...]

Songs:\n"""
        
        for idx, track in enumerate(tracks):
            name = track.get('name', 'Unknown')
            artists = ', '.join(track.get('artists', ['Unknown']))
            album = track.get('album', '')
            year = track.get('release_date', '')[:4] if track.get('release_date') else ''
            
            prompt += f"{idx}. \"{name}\" by {artists}"
            if album:
                prompt += f" (Album: {album})"
            if year:
                prompt += f" [{year}]"
            prompt += "\n"
        
        prompt += "\nThink carefully about language, artist origin, and musical style. Return only the JSON array."
        return prompt
    
    def _parse_batch_response(self, response_text: str, tracks: List[Dict]) -> List[Tuple[str, float]]:
        """Parse batch classification response."""
        import json
        
        # Try to extract JSON from response
        try:
            # Find JSON array in response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group(0))
                
                # Create result list with defaults
                classifications = [('Misc', 0.6) for _ in tracks]
                
                # Fill in classifications from response
                for item in results:
                    idx = item.get('index', -1)
                    if 0 <= idx < len(tracks):
                        category = item.get('category', 'Misc')
                        confidence = float(item.get('confidence', 0.6))
                        classifications[idx] = (category, confidence)
                
                return classifications
        except Exception as e:
            print(f"⚠️  Batch parse error: {e}")
        
        # Fallback: classify individually
        return [self._fallback_classify(track) for track in tracks]
