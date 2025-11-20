"""Rule-based classifier to reduce LLM dependency and improve accuracy."""
from typing import Dict, List, Optional, Tuple


class RuleClassifier:
    """Deterministic rule-based classifier for obvious cases."""
    
    # Comprehensive artist databases (expandable over time)
    PUNJABI_ARTISTS = {
        'sidhu moose wala', 'karan aujla', 'ap dhillon', 'shubh', 'diljit dosanjh',
        'ammy virk', 'jassa dhillon', 'tegi pannu', 'khan bhaini', 'arjan dhillon',
        'prem dhillon', 'jordan sandhu', 'harnoor', 'navaan sandhu', 'sultaan',
        'gurinder gill', 'amrit maan', 'dilpreet dhillon', 'gur sidhu', 'r nait',
        'mankirt aulakh', 'garry sandhu', 'jaz dhami', 'surjit bhullar', 'tarsem jassar',
        'babbu maan', 'sharry mann', 'prabh gill', 'ninja', 'sippy gill',
        'varinder brar', 'ranjit bawa', 'gippy grewal', 'jazzy b', 'bohemia'
    }
    
    HINDI_PARTY_ARTISTS = {
        'badshah', 'yo yo honey singh', 'divine', 'kr$na', 'raftaar', 'seedhe maut',
        'emiway bantai', 'ikka', 'guru randhawa', 'neha kakkar', 'tony kakkar',
        'meet bros', 'tanishk bagchi', 'sukhe', 'hardy sandhu'
    }
    
    HINDI_MELODIC_ARTISTS = {
        'arijit singh', 'pritam', 'a.r. rahman', 'mohit chauhan', 'atif aslam',
        'vishal-shekhar', 'shankar-ehsaan-loy', 'salim-sulaiman', 'amit trivedi',
        'armaan malik', 'shreya ghoshal', 'sonu nigam', 'jubin nautiyal', 'darshan raval',
        'lata mangeshkar', 'kishore kumar', 'mohammed rafi', 'asha bhosle', 'mukesh',
        'kumar sanu', 'udit narayan', 'alka yagnik', 'shaan', 'sunidhi chauhan'
    }
    
    ENGLISH_POP_ARTISTS = {
        'the weeknd', 'dua lipa', 'lady gaga', 'harry styles', 'taylor swift',
        'ariana grande', 'post malone', 'doja cat', 'calvin harris', 'david guetta',
        'ed sheeran', 'bruno mars', 'rihanna', 'beyoncé', 'billie eilish',
        'selena gomez', 'shawn mendes', 'olivia rodrigo', 'charlie puth', 'maroon 5',
        'justin bieber', 'miley cyrus', 'katy perry', 'sia'
    }
    
    ENGLISH_HIPHOP_ARTISTS = {
        'drake', 'eminem', 'kanye west', 'travis scott', 'j. cole', 'future',
        '21 savage', 'kendrick lamar', 'jack harlow', 'lil baby', 'don toliver',
        'lil uzi vert', 'playboi carti', 'a$ap rocky', 'tyler, the creator',
        'juice wrld', 'xxxtentacion', 'lil wayne', 'nicki minaj', 'cardi b',
        'migos', 'offset', 'quavo', '50 cent', 'snoop dogg', 'dr. dre',
        'pop smoke', 'roddy ricch', 'dababy', 'nle choppa', 'lil durk'
    }
    
    ENGLISH_RNB_ARTISTS = {
        'frank ocean', 'sza', 'zayn', 'khalid', '6lack', 'brent faiyaz',
        'jhené aiko', 'miguel', 'h.e.r.', 'daniel caesar', 'partynextdoor',
        'bryson tiller', 'kehlani', 'summer walker', 'alicia keys', 'usher',
        'chris brown', 'trey songz', 'ne-yo'
    }
    
    ENGLISH_ROCK_ARTISTS = {
        'arctic monkeys', 'linkin park', 'imagine dragons', 'coldplay', 'nirvana',
        'foo fighters', 'the neighbourhood', 'radiohead', 'green day', 'queen',
        'led zeppelin', 'pink floyd', 'the beatles', 'red hot chili peppers',
        'muse', 'system of a down', 'metallica', 'ac/dc', 'the strokes',
        'tame impala', 'cage the elephant', 'twenty one pilots'
    }
    
    PHONK_ARTISTS = {
        'kordhell', 'dvrst', 'kslv noh', 'dxrk ダーク', 'moondeity', 'onimxru',
        'pharmacist', 'sxmpra', 'soverset', 'twisted', 'kaito shoma', 'hensonn'
    }
    
    GYM_HYPE_ARTISTS = {
        'nle choppa', 'pop smoke', 'cj', 'neffex', 'lil pump', 'ski mask the slump god',
        'denzel curry', 'smokepurpp', 'zillakami', 'city morgue', 'scarlxrd'
    }
    
    LOFI_ARTISTS = {
        'lofi fruits music', 'chillhop music', 'chill select', 'dreamy',
        'allem iversom', 'kupla', 'nymano', 'sleepy fish', 'møøse', 'idealism'
    }
    
    SOUNDTRACK_ARTISTS = {
        'hans zimmer', 'ludwig göransson', 'john williams', 'michael giacchino',
        'anirudh ravichander', 'ravi basrur', 'a.r. rahman', 'background score',
        'trent reznor', 'atticus ross', 'thomas newman', 'howard shore'
    }
    
    OLDIES_ARTISTS = {
        'kishore kumar', 'lata mangeshkar', 'mohammed rafi', 'mukesh',
        'asha bhosle', 'manna dey', 'talat mahmood', 'geeta dutt',
        'hemant kumar', 'rafi', 'nusrat fateh ali khan'
    }
    
    # Language detection patterns
    PUNJABI_PATTERNS = [
        'da', 'di', 'ch', 'jatt', 'pind', 'yaari', 'gaddi', 'dhol',
        'teri', 'mera', 'tere', 'meri', 'veera', 'dil', 'pyaar'
    ]
    
    HINDI_PATTERNS = [
        'hai', 'hain', 'mujhe', 'tujhe', 'mere', 'tere', 'pyaar', 'dil',
        'tera', 'mera', 'ke', 'ki', 'ho', 'tum', 'main', 'tu'
    ]
    
    # Mood/vibe keywords
    SAD_KEYWORDS = [
        'sad', 'heartbreak', 'broken', 'miss', 'alone', 'lonely', 'tears',
        'pain', 'hurt', 'lost', 'empty', 'cry', 'goodbye', 'memories',
        'dil tutda', 'yaad', 'bewafa', 'judai', 'alvida'
    ]
    
    PHONK_KEYWORDS = [
        'phonk', 'drift', 'cowbell', 'aggressive', 'slowed', 'bass boosted',
        'brazilian phonk', 'sigma', 'gigachad'
    ]
    
    GYM_KEYWORDS = [
        'workout', 'gym', 'hype', 'beast mode', 'aggressive', 'hard',
        'rage', 'energy', 'pump', 'training'
    ]
    
    CHILL_KEYWORDS = [
        'lofi', 'chill', 'ambient', 'relax', 'study', 'sleep', 'calm',
        'peaceful', 'meditation', 'soft', 'piano', 'instrumental'
    ]
    
    SOUNDTRACK_KEYWORDS = [
        'theme', 'score', 'ost', 'bgm', 'soundtrack', 'interstellar',
        'inception', 'epic', 'orchestral', 'cinematic', 'main title'
    ]

    def __init__(self):
        """Initialize rule-based classifier."""
        pass
    
    def classify(self, track: Dict) -> Optional[Tuple[str, float]]:
        """
        Attempt deterministic classification based on rules.
        
        Returns:
            (category, confidence) tuple if confident classification, None otherwise
        """
        # Extract track metadata
        title = track.get('name', '').lower()
        artists_raw = track.get('artists', [])
        
        # Handle both list of strings and list of dicts
        if artists_raw and isinstance(artists_raw[0], dict):
            artists = ', '.join([a.get('name', '') for a in artists_raw]).lower()
        else:
            artists = ', '.join(artists_raw).lower() if isinstance(artists_raw, list) else str(artists_raw).lower()
        
        genres = [g.lower() for g in track.get('genres', [])]
        year = track.get('release_date', '')[:4] if track.get('release_date') else ''
        
        # Priority 1: Check mood/vibe overrides (highest priority)
        mood_result = self._check_mood_categories(title, artists, genres)
        if mood_result:
            return mood_result
        
        # Priority 2: Check artist-based classification (very reliable)
        artist_result = self._check_artist_categories(artists, title)
        if artist_result:
            return artist_result
        
        # Priority 3: Check genre-based classification
        genre_result = self._check_genre_categories(genres, title, artists)
        if genre_result:
            return genre_result
        
        # Priority 4: Check language patterns in title
        language_result = self._check_language_patterns(title, artists)
        if language_result:
            return language_result
        
        # Priority 5: Check for oldies (pre-1990)
        if year and year.isdigit() and int(year) < 1990:
            if any(artist in artists for artist in self.OLDIES_ARTISTS):
                return ('Oldies', 0.90)
        
        # No confident rule-based classification
        return None
    
    def _check_mood_categories(self, title: str, artists: str, genres: List[str]) -> Optional[Tuple[str, float]]:
        """Check mood/vibe categories (highest priority)."""
        # Phonk detection
        if any(kw in title for kw in self.PHONK_KEYWORDS) or \
           any(artist in artists for artist in self.PHONK_ARTISTS) or \
           'phonk' in ' '.join(genres):
            return ('Gym - Phonk', 0.95)
        
        # Gym hype detection
        if any(artist in artists for artist in self.GYM_HYPE_ARTISTS) or \
           any(kw in title for kw in self.GYM_KEYWORDS):
            return ('Gym - Hype', 0.90)
        
        # Lofi/Chill detection
        if any(kw in title for kw in self.CHILL_KEYWORDS) or \
           any(artist in artists for artist in self.LOFI_ARTISTS) or \
           'lofi' in ' '.join(genres) or 'chillhop' in ' '.join(genres):
            return ('Chill/Lofi', 0.95)
        
        # Soundtrack detection
        if any(kw in title for kw in self.SOUNDTRACK_KEYWORDS) or \
           any(artist in artists for artist in self.SOUNDTRACK_ARTISTS):
            return ('Soundtracks', 0.90)
        
        # Sad/Emotional detection
        sad_score = sum(1 for kw in self.SAD_KEYWORDS if kw in title)
        if sad_score >= 2:  # At least 2 sad keywords
            return ('Sad/Emotional', 0.85)
        
        return None
    
    def _check_artist_categories(self, artists: str, title: str) -> Optional[Tuple[str, float]]:
        """Check artist-based categories (very reliable)."""
        # Punjabi artists
        for artist in self.PUNJABI_ARTISTS:
            if artist in artists:
                # Check if it's a sad Punjabi song
                if any(kw in title for kw in self.SAD_KEYWORDS[:7]):  # Only English sad keywords
                    return ('Sad/Emotional', 0.90)
                return ('Punjabi - Hype/Fun', 0.95)
        
        # Hindi Party artists
        for artist in self.HINDI_PARTY_ARTISTS:
            if artist in artists:
                return ('Hindi - Party/Dance', 0.95)
        
        # Hindi Melodic artists
        for artist in self.HINDI_MELODIC_ARTISTS:
            if artist in artists:
                # Check for sad Hindi songs
                if any(kw in title for kw in ['sad', 'dil', 'yaad', 'bewafa', 'judai']):
                    return ('Sad/Emotional', 0.90)
                return ('Hindi - Bollywood/Melodic', 0.95)
        
        # English Pop artists
        for artist in self.ENGLISH_POP_ARTISTS:
            if artist in artists:
                # The Weeknd special case (often R&B)
                if 'weeknd' in artists and any(kw in title for kw in ['feel', 'love', 'heart', 'hurt']):
                    return ('English - R&B', 0.85)
                return ('English - Pop', 0.95)
        
        # English Hip-Hop artists
        for artist in self.ENGLISH_HIPHOP_ARTISTS:
            if artist in artists:
                return ('English - Hip-Hop', 0.95)
        
        # English R&B artists
        for artist in self.ENGLISH_RNB_ARTISTS:
            if artist in artists:
                return ('English - R&B', 0.95)
        
        # English Rock artists
        for artist in self.ENGLISH_ROCK_ARTISTS:
            if artist in artists:
                return ('English - Rock/Alt', 0.95)
        
        return None
    
    def _check_genre_categories(self, genres: List[str], title: str, artists: str) -> Optional[Tuple[str, float]]:
        """Check Spotify genre tags for classification."""
        if not genres:
            return None
        
        genres_str = ' '.join(genres)
        
        # Punjabi genres
        if any(g in genres_str for g in ['punjabi', 'bhangra', 'desi']):
            return ('Punjabi - Hype/Fun', 0.85)
        
        # Hindi/Bollywood genres
        if any(g in genres_str for g in ['bollywood', 'filmi', 'indian', 'hindi']):
            if any(g in genres_str for g in ['dance', 'party', 'edm']):
                return ('Hindi - Party/Dance', 0.85)
            return ('Hindi - Bollywood/Melodic', 0.85)
        
        # Phonk genre
        if 'phonk' in genres_str:
            return ('Gym - Phonk', 0.95)
        
        # Hip-Hop genres
        if any(g in genres_str for g in ['hip hop', 'rap', 'trap', 'drill']):
            if any(g in genres_str for g in ['aggressive', 'hard', 'memphis']):
                return ('Gym - Hype', 0.85)
            return ('English - Hip-Hop', 0.85)
        
        # Pop genres
        if any(g in genres_str for g in ['pop', 'dance pop', 'electropop', 'indie pop']):
            return ('English - Pop', 0.80)
        
        # R&B genres
        if any(g in genres_str for g in ['r&b', 'rnb', 'soul', 'neo soul']):
            return ('English - R&B', 0.85)
        
        # Rock genres
        if any(g in genres_str for g in ['rock', 'alternative', 'indie rock', 'metal', 'punk']):
            return ('English - Rock/Alt', 0.85)
        
        # Lofi genres
        if any(g in genres_str for g in ['lofi', 'chillhop', 'ambient', 'chillout']):
            return ('Chill/Lofi', 0.90)
        
        # Classical/Soundtrack
        if any(g in genres_str for g in ['soundtrack', 'score', 'orchestral', 'cinematic']):
            return ('Soundtracks', 0.85)
        
        # K-pop, French, Spanish, etc.
        if any(g in genres_str for g in ['k-pop', 'french', 'spanish', 'latin', 'afrobeat', 'reggaeton', 'arabic', 'turkish']):
            return ('World', 0.85)
        
        return None
    
    def _check_language_patterns(self, title: str, artists: str) -> Optional[Tuple[str, float]]:
        """Check language patterns in title for classification."""
        # Punjabi language patterns
        punjabi_score = sum(1 for pattern in self.PUNJABI_PATTERNS if pattern in title)
        if punjabi_score >= 2:
            return ('Punjabi - Hype/Fun', 0.75)
        
        # Hindi language patterns
        hindi_score = sum(1 for pattern in self.HINDI_PATTERNS if pattern in title)
        if hindi_score >= 2:
            return ('Hindi - Bollywood/Melodic', 0.75)
        
        return None
    
    def get_confidence_boost(self, track: Dict, llm_category: str, llm_confidence: float) -> Tuple[str, float]:
        """
        Boost LLM confidence if rules agree with classification.
        
        Args:
            track: Track metadata
            llm_category: Category from LLM
            llm_confidence: Confidence from LLM
        
        Returns:
            (potentially adjusted category, potentially boosted confidence)
        """
        rule_result = self.classify(track)
        
        if rule_result:
            rule_category, rule_confidence = rule_result
            
            # If rules and LLM agree, use higher confidence
            if rule_category == llm_category:
                return (llm_category, max(llm_confidence, rule_confidence))
            
            # If rules are very confident, override LLM
            if rule_confidence >= 0.90 and llm_confidence < 0.80:
                return rule_result
        
        # Return LLM classification unchanged
        return (llm_category, llm_confidence)
