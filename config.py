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
    
    # LLM configuration (vLLM - gemma-3-1b-it for maximum speed)
    VLLM_ENDPOINT = os.getenv('VLLM_ENDPOINT', 'http://localhost:8000/v1')
    VLLM_MODEL = os.getenv('VLLM_MODEL', 'unsloth/gemma-3-1b-it')  # 1B for fastest inference
    
    # Parallel processing (optimized for 1B model - maximum parallelization)
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))  # Large batches with 1B model
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '15'))  # Maximum parallel workers
    
    # Classification settings
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.8'))
    
    # Cache file for token
    TOKEN_CACHE_PATH = '.spotify_token_cache'
    
    # Categories
    CATEGORIES = [
        'English',
        'Hindi',
        'Punjabi',
        'Phonk/Instrumental',
        'Oldies',
        'Misc'
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

