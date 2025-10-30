"""Spotify API client for authentication and data fetching.

This module provides a lightweight mock fallback so the app can run without
the `spotipy` package or real Spotify credentials when `Config.USE_MOCKS` is
enabled. The real code path is unchanged when Spotipy is installed and
mocking is disabled.
"""
from typing import List, Dict, Optional
from config import Config

_HAS_SPOTIPY = True
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except Exception:
    _HAS_SPOTIPY = False


class SpotifyClient:
    """Wrapper for Spotify API operations."""
    
    def __init__(self):
        """Initialize Spotify client with OAuth2."""
        self.sp = None
        print(f"🔍 Debug: _HAS_SPOTIPY={_HAS_SPOTIPY}, USE_MOCKS={Config.USE_MOCKS}")
        # If spotipy is available and mocks are not requested, authenticate.
        if _HAS_SPOTIPY and not Config.USE_MOCKS:
            print("🔐 Attempting Spotify authentication...")
            self._authenticate()
        else:
            # Keep self.sp as None to indicate mock mode
            print(f"⚠️  Using mock mode (_HAS_SPOTIPY={_HAS_SPOTIPY}, USE_MOCKS={Config.USE_MOCKS})")
            self.sp = None
    
    def _authenticate(self):
        """Authenticate with Spotify using OAuth2."""
        try:
            auth_manager = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope="user-library-read playlist-read-private playlist-modify-public playlist-modify-private",
                cache_path=Config.TOKEN_CACHE_PATH,
                open_browser=True  # Open browser for OAuth flow
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            # Test the connection by getting current user
            _ = self.sp.current_user()
            print(f"✅ Successfully authenticated with Spotify!")
        except Exception as e:
            print(f"⚠️  Spotify authentication failed: {e}")
            print(f"   Falling back to mock mode for development")
            self.sp = None
    
    def get_current_user(self) -> Dict:
        """Get current user's profile."""
        if self.sp:
            return self.sp.current_user()

        # Mock user for offline/demo mode
        return {'id': 'mock_user', 'display_name': 'Mock User'}
    
    def get_liked_songs(self) -> List[Dict]:
        """
        Fetch all liked songs from user's library.
        Handles pagination automatically.
        
        Returns:
            List of track objects with metadata
        """
        # Real API path
        if self.sp:
            tracks = []
            offset = 0
            limit = 50

            while True:
                results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
                if not results['items']:
                    break

                for item in results['items']:
                    track = item['track']
                    tracks.append(self._extract_track_info(track))

                offset += limit

                # Break if we've fetched all tracks
                if len(results['items']) < limit:
                    break

            return tracks

        # Mock/demo path: return a few synthetic tracks
        return [
            {
                'id': 'mock1',
                'name': 'Demo Song One',
                'artists': ['Demo Artist'],
                'artist_ids': [],
                'album': 'Demo Album',
                'release_date': '2021-01-01',
                'genres': ['pop'],
                'markets': ['US'],
                'uri': 'spotify:track:mock1'
            },
            {
                'id': 'mock2',
                'name': 'Tum Hi Ho',
                'artists': ['Arijit Singh'],
                'artist_ids': [],
                'album': 'Aashiqui 2',
                'release_date': '2013-04-08',
                'genres': ['bollywood'],
                'markets': ['IN'],
                'uri': 'spotify:track:mock2'
            }
        ]
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """
        Fetch all tracks from a specific playlist.
        Handles pagination automatically.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of track objects with metadata
        """
        if self.sp:
            tracks = []
            offset = 0
            limit = 100

            while True:
                results = self.sp.playlist_tracks(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    fields='items(track(id,name,artists,album,external_ids)),next'
                )

                if not results['items']:
                    break

                for item in results['items']:
                    if item['track']:  # Sometimes tracks can be None
                        tracks.append(self._extract_track_info(item['track']))

                offset += limit

                # Break if we've fetched all tracks
                if not results.get('next'):
                    break

            return tracks

        # Mock path for playlists
        return [
            {
                'id': 'mock_pl_1',
                'name': 'Demo Playlist Song',
                'artists': ['Demo Artist'],
                'artist_ids': [],
                'album': 'Demo Album',
                'release_date': '2019-06-01',
                'genres': ['lofi'],
                'markets': ['US'],
                'uri': 'spotify:track:mock_pl_1'
            }
        ]
    
    def _extract_track_info(self, track: Dict) -> Dict:
        """
        Extract relevant information from a track object.
        
        Args:
            track: Spotify track object
            
        Returns:
            Dictionary with track metadata
        """
        # If this was a full Spotify track object, extract properly
        try:
            artist_ids = [artist['id'] for artist in track.get('artists', []) if artist.get('id')]
            # Note: Not fetching artist genres to avoid rate limits - LLM will classify instead
            
            return {
                'id': track.get('id'),
                'name': track.get('name'),
                'artists': [a.get('name') if isinstance(a, dict) else a for a in track.get('artists', [])],
                'artist_ids': artist_ids,
                'album': track.get('album', {}).get('name', '') if isinstance(track.get('album'), dict) else track.get('album', ''),
                'release_date': track.get('release_date', '') or track.get('album', {}).get('release_date', ''),
                'genres': [],  # Empty - LLM will classify based on track/artist name instead
                'markets': track.get('markets', []) or track.get('album', {}).get('available_markets', []),
                'uri': track.get('uri')
            }
        except Exception:
            # Fallback minimal shape
            return {
                'id': track.get('id'),
                'name': track.get('name', 'Unknown'),
                'artists': track.get('artists', []),
                'artist_ids': [],
                'album': track.get('album', ''),
                'release_date': track.get('release_date', ''),
                'genres': track.get('genres', []),
                'markets': track.get('markets', []),
                'uri': track.get('uri', '')
            }
    
    def create_playlist(self, name: str, description: str = "", public: bool = True) -> str:
        """
        Create a new playlist.
        
        Args:
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public
            
        Returns:
            Playlist ID
        """
        if self.sp:
            user_id = self.get_current_user()['id']
            playlist = self.sp.user_playlist_create(
                user_id,
                name,
                public=public,
                description=description
            )
            return playlist['id']

        # Mock path
        return f"mock_playlist_{name}"
    
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]):
        """
        Add tracks to a playlist in batches.
        Spotify allows max 100 tracks per request.
        
        Args:
            playlist_id: Target playlist ID
            track_uris: List of track URIs to add
        """
        if self.sp:
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                self.sp.playlist_add_items(playlist_id, batch)
            return

        # Mock: no-op (but print for visibility)
        print(f"[MOCK] Adding {len(track_uris)} tracks to playlist {playlist_id}")
    
    def get_playlist_name(self, playlist_id: str) -> str:
        """Get the name of a playlist."""
        if self.sp:
            playlist = self.sp.playlist(playlist_id, fields='name')
            return playlist['name']

        return 'Mock Playlist'

