"""Playlist creation and management."""
from typing import Dict, List
from datetime import datetime
from spotify_client import SpotifyClient
from config import Config


class PlaylistManager:
    """Manages playlist creation and track addition."""
    
    def __init__(self, spotify_client: SpotifyClient):
        """
        Initialize playlist manager.
        
        Args:
            spotify_client: Authenticated Spotify client
        """
        self.spotify = spotify_client
    
    def create_categorized_playlists(
        self,
        categorized_tracks: Dict[str, List[Dict]],
        source_name: str = "Liked Songs",
        dry_run: bool = False
    ) -> Dict[str, str]:
        """
        Create playlists for each category and add tracks.
        Overwrites any existing playlists with the same name.
        
        Args:
            categorized_tracks: Dict mapping categories to track lists
            source_name: Name of source (for playlist description)
            dry_run: If True, don't actually create playlists
            
        Returns:
            Dict mapping category names to playlist IDs
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        playlist_ids = {}
        
        for category, tracks in categorized_tracks.items():
            if not tracks:
                print(f"⏭️  Skipping {category} - no tracks")
                continue
            
            # New naming format: autosorted-english, autosorted-oldies, etc.
            category_slug = category.lower().replace("/", "-").replace(" ", "-")
            playlist_name = f"autosorted-{category_slug}"
            description = f"Auto-sorted {category} tracks from {source_name} on {timestamp}"
            
            if dry_run:
                print(f"📋 [DRY RUN] Would create playlist '{playlist_name}' with {len(tracks)} tracks")
                playlist_ids[category] = f"dry_run_{category}"
            else:
                try:
                    # In mock mode, sp is None
                    if not self.spotify.sp:
                        return None

                    # Check for and delete existing playlist with same name
                    existing_id = self._find_playlist_by_name(playlist_name)
                    if existing_id:
                        print(f"🗑️  Deleting existing playlist '{playlist_name}'")
                        self.spotify.sp.current_user_unfollow_playlist(existing_id)
                    
                    # Create new playlist
                    playlist_id = self.spotify.create_playlist(
                        name=playlist_name,
                        description=description,
                        public=False  # Keep private by default
                    )
                    
                    # Add tracks
                    track_uris = [track['uri'] for track in tracks]
                    self.spotify.add_tracks_to_playlist(playlist_id, track_uris)
                    
                    playlist_ids[category] = playlist_id
                    print(f"✅ Created '{playlist_name}' with {len(tracks)} tracks")
                    
                except Exception as e:
                    print(f"❌ Error creating playlist for {category}: {e}")
        
        return playlist_ids
    
    def _find_playlist_by_name(self, playlist_name: str) -> str:
        """
        Find a playlist by exact name match.
        
        Args:
            playlist_name: Name of playlist to find
            
        Returns:
            Playlist ID if found, None otherwise
        """
        if not self.spotify.sp:
            return None
        try:
            # Get current user's playlists
            offset = 0
            limit = 50
            
            while True:
                results = self.spotify.sp.current_user_playlists(limit=limit, offset=offset)
                
                for playlist in results['items']:
                    if playlist['name'] == playlist_name:
                        return playlist['id']
                
                if not results.get('next'):
                    break
                    
                offset += limit
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error searching for playlist: {e}")
            return None
    
    def update_existing_playlist(
        self,
        playlist_id: str,
        tracks: List[Dict],
        append: bool = True
    ):
        """
        Update an existing playlist with tracks.
        
        Args:
            playlist_id: Target playlist ID
            tracks: List of tracks to add
            append: If True, append to existing tracks; if False, replace
        """
        track_uris = [track['uri'] for track in tracks]
        
        if not append:
            # Clear existing tracks first
            # Note: spotipy doesn't have a direct clear method,
            # we'd need to fetch and remove all tracks
            pass
        
        self.spotify.add_tracks_to_playlist(playlist_id, track_uris)

