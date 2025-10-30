"""Test cache manager functionality."""
import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import CacheManager


def test_cache_manager():
    """Test CacheManager basic operations."""
    print("🧪 Testing CacheManager...")
    
    # Create temporary cache directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize cache manager
        cache = CacheManager(cache_dir=temp_dir)
        print("✅ Cache manager initialized")
        
        # Test track metadata caching
        test_track = {
            'id': 'test123',
            'name': 'Test Song',
            'artists': ['Test Artist'],
            'album': 'Test Album',
            'release_date': '2020-01-01',
            'genres': ['pop'],
            'markets': ['US', 'IN'],
            'uri': 'spotify:track:test123'
        }
        
        cache.save_track_metadata('test123', test_track)
        retrieved = cache.get_track_metadata('test123')
        assert retrieved is not None, "Track not found in cache"
        assert retrieved['name'] == 'Test Song', "Track name mismatch"
        print("✅ Track metadata caching works")
        
        # Test classification caching
        cache.save_classification('test123', 'English', 0.95)
        category = cache.get_classification('test123')
        assert category == 'English', f"Expected 'English', got '{category}'"
        print("✅ Classification caching works")
        
        # Test batch operations
        tracks = [
            {**test_track, 'id': f'test{i}', 'name': f'Song {i}'} 
            for i in range(10)
        ]
        cache.save_tracks_batch(tracks)
        print("✅ Batch track saving works")
        
        # Test fetch session
        cache.save_fetch_session('liked', 'user123', [t['id'] for t in tracks])
        session = cache.get_fetch_session('liked', 'user123')
        assert session is not None, "Session not found"
        assert session['track_count'] == 10, "Track count mismatch"
        print("✅ Fetch session tracking works")
        
        # Test unclassified tracks
        all_ids = [f'test{i}' for i in range(15)]
        cache.save_classification('test5', 'Hindi', 0.90)
        cache.save_classification('test10', 'Punjabi', 0.85)
        
        unclassified = cache.get_unclassified_tracks(all_ids)
        assert 'test5' not in unclassified, "test5 should be classified"
        assert 'test14' in unclassified, "test14 should be unclassified"
        print(f"✅ Unclassified detection works ({len(unclassified)} unclassified)")
        
        # Test cache stats
        stats = cache.get_cache_stats()
        print(f"✅ Cache stats: {stats}")
        
        print("\n✅ All cache tests passed!")
        return True
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"🗑️  Cleaned up temp directory: {temp_dir}")


if __name__ == '__main__':
    try:
        test_cache_manager()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

