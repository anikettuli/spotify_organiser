"""Persistent cache manager for track metadata and classifications."""
import json
import os
import tempfile
import shutil
from typing import Dict, List, Optional
from datetime import datetime


class CacheManager:
    """Manages persistent cache for track data and classifications."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.tracks_cache_file = os.path.join(cache_dir, "tracks_metadata.json")
        self.classifications_cache_file = os.path.join(cache_dir, "classifications.json")
        self.fetch_sessions_file = os.path.join(cache_dir, "fetch_sessions.json")
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing caches
        self.tracks_cache = self._load_cache(self.tracks_cache_file)
        self.classifications_cache = self._load_cache(self.classifications_cache_file)
        self.fetch_sessions = self._load_cache(self.fetch_sessions_file)
    
    def _load_cache(self, filepath: str) -> Dict:
        """Load cache from file."""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_cache(self, filepath: str, data: Dict):
        """Save cache to file atomically to prevent corruption."""
        try:
            # Write to temporary file first
            temp_fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix='.tmp')
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic move to actual file
            shutil.move(temp_path, filepath)
        except IOError as e:
            print(f"Warning: Could not save cache to {filepath}: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
    
    def get_track_metadata(self, track_id: str) -> Optional[Dict]:
        """
        Get cached track metadata.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Track metadata dict or None if not cached
        """
        return self.tracks_cache.get(track_id)
    
    def save_track_metadata(self, track_id: str, metadata: Dict):
        """
        Save track metadata to cache.
        
        Args:
            track_id: Spotify track ID
            metadata: Track metadata dictionary
        """
        self.tracks_cache[track_id] = {
            **metadata,
            'cached_at': datetime.now().isoformat()
        }
        self._save_cache(self.tracks_cache_file, self.tracks_cache)
    
    def save_tracks_batch(self, tracks: List[Dict]):
        """
        Save multiple tracks to cache in batch.
        
        Args:
            tracks: List of track metadata dictionaries
        """
        for track in tracks:
            track_id = track.get('id')
            if track_id:
                self.tracks_cache[track_id] = {
                    **track,
                    'cached_at': datetime.now().isoformat()
                }
        self._save_cache(self.tracks_cache_file, self.tracks_cache)
    
    def get_classification(self, track_id: str) -> Optional[str]:
        """
        Get cached classification for a track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Category name or None if not cached
        """
        entry = self.classifications_cache.get(track_id)
        if entry:
            return entry.get('category')
        return None
    
    def save_classification(self, track_id: str, category: str, confidence: float = 1.0):
        """
        Save track classification to cache.
        
        Args:
            track_id: Spotify track ID
            category: Assigned category
            confidence: Classification confidence score
        """
        self.classifications_cache[track_id] = {
            'category': category,
            'confidence': confidence,
            'classified_at': datetime.now().isoformat()
        }
        self._save_cache(self.classifications_cache_file, self.classifications_cache)
    
    def save_classifications_batch(self, classifications: Dict[str, tuple]):
        """
        Save multiple classifications in batch.
        
        Args:
            classifications: Dict mapping track_id to (category, confidence) tuples
        """
        for track_id, (category, confidence) in classifications.items():
            self.classifications_cache[track_id] = {
                'category': category,
                'confidence': confidence,
                'classified_at': datetime.now().isoformat()
            }
        self._save_cache(self.classifications_cache_file, self.classifications_cache)
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about cached data."""
        return {
            'tracks_cached': len(self.tracks_cache),
            'classifications_cached': len(self.classifications_cache)
        }
    
    def save_fetch_session(self, source: str, source_id: str, track_ids: List[str]):
        """
        Save a fetch session (tracks retrieved from Spotify).
        
        Args:
            source: 'liked' or 'playlist'
            source_id: User ID or playlist ID
            track_ids: List of track IDs fetched
        """
        session_key = f"{source}_{source_id}"
        self.fetch_sessions[session_key] = {
            'source': source,
            'source_id': source_id,
            'track_ids': track_ids,
            'fetched_at': datetime.now().isoformat(),
            'track_count': len(track_ids)
        }
        self._save_cache(self.fetch_sessions_file, self.fetch_sessions)
    
    def get_fetch_session(self, source: str, source_id: str) -> Optional[Dict]:
        """Get a saved fetch session."""
        session_key = f"{source}_{source_id}"
        return self.fetch_sessions.get(session_key)
    
    def get_unclassified_tracks(self, track_ids: List[str]) -> List[str]:
        """
        Get list of track IDs that haven't been classified yet.
        
        Args:
            track_ids: List of all track IDs to check
            
        Returns:
            List of unclassified track IDs
        """
        return [tid for tid in track_ids if tid not in self.classifications_cache]
    
    def get_cached_tracks_by_ids(self, track_ids: List[str]) -> List[Dict]:
        """
        Retrieve full track metadata for given IDs from cache.
        
        Args:
            track_ids: List of track IDs
            
        Returns:
            List of track metadata dicts
        """
        tracks = []
        for track_id in track_ids:
            track = self.tracks_cache.get(track_id)
            if track:
                tracks.append(track)
        return tracks
    
    def clear_cache(self):
        """Clear all cached data."""
        self.tracks_cache = {}
        self.classifications_cache = {}
        self.fetch_sessions = {}
        self._save_cache(self.tracks_cache_file, self.tracks_cache)
        self._save_cache(self.classifications_cache_file, self.classifications_cache)
        self._save_cache(self.fetch_sessions_file, self.fetch_sessions)

