"""Spotify API client for authentication and data fetching.

This module provides a lightweight mock fallback so the app can run without
the `spotipy` package or real Spotify credentials when `Config.USE_MOCKS` is
enabled. The real code path is unchanged when Spotipy is installed and
mocking is disabled.
"""
from typing import List, Dict, Optional
import time
from config import Config

_HAS_SPOTIPY = True
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    _HAS_SPOTIPY = False


class SpotifyClient:
    """Wrapper for Spotify API operations."""
    
    def __init__(self):
        """Initialize Spotify client with OAuth2."""
        self.sp = None
        # If spotipy is available and mocks are not requested, authenticate.
        if _HAS_SPOTIPY and not Config.USE_MOCKS:
            self._authenticate()
        else:
            # Keep self.sp as None to indicate mock mode
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
        except Exception as e:
            print(f"⚠️  Spotify authentication failed: {e}")
            print("   Falling back to mock mode for development")
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
        Handles pagination automatically. Fetches artist genres efficiently in one pass.
        
        Returns:
            List of track objects with metadata
        """
        # Real API path
        if self.sp:
            tracks = []
            offset = 0
            limit = 50

            # First pass: fetch all tracks
            print("📥 Fetching tracks...")
            while True:
                results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
                if not results['items']:
                    break

                for item in results['items']:
                    track = item['track']
                    track_info = self._extract_track_info(track)
                    tracks.append(track_info)

                offset += limit

                # Break if we've fetched all tracks
                if len(results['items']) < limit:
                    break

            # Second pass: collect all unique artist IDs (automatically deduplicates)
            print(f"🎤 Found {len(tracks)} tracks, collecting unique artists...")
            
            # Check if we should fetch artist genres
            if not Config.FETCH_ARTIST_GENRES:
                print("⏭️  Skipping artist genre fetching (disabled in config)")
                print("   Classification will rely on artist names and language detection")
                for track in tracks:
                    track['genres'] = []
                return tracks
            
            all_artist_ids = set()  # Set automatically handles duplicates
            total_artist_references = 0
            for track in tracks:
                total_artist_references += len(track['artist_ids'])
                all_artist_ids.update(track['artist_ids'])
            
            unique_artist_ids = list(all_artist_ids)
            duplicates_avoided = total_artist_references - len(unique_artist_ids)
            print(f"🎵 {len(unique_artist_ids)} unique artists (avoided {duplicates_avoided} duplicate API calls)")
            print(f"   Fetching genre data in batches of 50 (with 2s delays to avoid rate limits)...")
            
            # Third pass: fetch all artist genres in batches of 50
            import time
            artist_genres_map = {}
            for i in range(0, len(unique_artist_ids), 50):
                batch = unique_artist_ids[i:i+50]
                try:
                    artists_info = self.sp.artists(batch)
                    for artist in artists_info.get('artists', []):
                        if artist and artist.get('id'):
                            artist_genres_map[artist['id']] = {
                                'genres': artist.get('genres', []),
                                'popularity': artist.get('popularity', 0)
                            }
                    print(f"   ✓ Processed {min(i+50, len(unique_artist_ids))}/{len(unique_artist_ids)} artists")
                    
                    # Add delay to avoid rate limits (Spotify is VERY strict)
                    # Wait 2 seconds between batches to stay well under limits
                    if i + 50 < len(unique_artist_ids):  # Don't sleep after last batch
                        time.sleep(2.0)
                        
                except Exception as e:
                    print(f"   ⚠ Error fetching artists {i}-{i+50}: {e}")
                    # On rate limit, wait longer
                    if "429" in str(e) or "rate" in str(e).lower():
                        print(f"   ⏸️  Rate limited, waiting 30 seconds...")
                        time.sleep(30)
                    pass

            # Fourth pass: enrich tracks with artist genres (mapping cached artist data)
            print(f"✨ Mapping artist genres back to {len(tracks)} tracks...")
            tracks_enriched = 0
            total_genres_added = 0
            
            for track in tracks:
                genres = []
                # Look up each artist ID in the cached map (already fetched once)
                for artist_id in track['artist_ids']:
                    if artist_id in artist_genres_map:
                        artist_genres = artist_genres_map[artist_id]['genres']
                        genres.extend(artist_genres)
                
                # Store unique genres for this track
                track['genres'] = list(set(genres))
                if track['genres']:
                    tracks_enriched += 1
                    total_genres_added += len(track['genres'])
            
            print(f"   ✓ {tracks_enriched}/{len(tracks)} tracks now have genre data ({total_genres_added} total genre tags)")
            if len(artist_genres_map) < len(unique_artist_ids):
                missing = len(unique_artist_ids) - len(artist_genres_map)
                print(f"   ⚠️  {missing} artists had no genre data available from Spotify")

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

