"""Configuration management for Spotify LLM Organizer."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # Spotify credentials
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')
    
    # Gemini API configuration
    # Using Gemini 3 Pro Preview
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3-pro-preview')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    
    # Batch processing (100 songs per Gemini request)
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
    
    # Classification settings
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.8'))
    FETCH_ARTIST_GENRES = os.getenv('FETCH_ARTIST_GENRES', '1').lower() in ('1', 'true', 'yes')
    
    # Cache file for token
    TOKEN_CACHE_PATH = '.spotify_token_cache'
    
    # Categories (14 total - language/genre primary + mood/vibe secondary)
    CATEGORIES = [
        # Language & Core Genre (9 categories)
        'Punjabi - Hype/Fun',
        'Hindi - Party/Dance',
        'Hindi - Bollywood/Melodic',
        'English - Pop',
        'English - Hip-Hop',
        'English - R&B',
        'English - Rock/Alt',
        'Oldies',
        'World',
        # Mood & Vibe (5 categories)
        'Sad/Emotional',
        'Gym - Phonk',
        'Gym - Hype',
        'Chill/Lofi',
        'Soundtracks'
    ]

    # When enabled the app will use local mocks/fallbacks so the app can run
    # without real Spotify/OpenAI dependencies. Useful for development/demo.
    USE_MOCKS = os.getenv('USE_MOCKS', '0').lower() in ('1', 'true', 'yes')

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        # Allow running in mock mode without real Spotify credentials
        if cls.USE_MOCKS:
            return True

        if not cls.SPOTIFY_CLIENT_ID:
            raise ValueError("SPOTIFY_CLIENT_ID not set in .env file")
        if not cls.SPOTIFY_CLIENT_SECRET:
            raise ValueError("SPOTIFY_CLIENT_SECRET not set in .env file")
        return True

