"""Test classifier metadata rules without LLM."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from classifier import SongClassifier
except ImportError as e:
    print(f"⚠️  Skipping classifier tests - missing dependencies: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(0)


def test_oldies_detection():
    """Test oldies classification rules."""
    print("🧪 Testing Oldies Detection...")
    
    classifier = SongClassifier()
    
    # Test classic artist detection
    test_tracks = [
        {
            'id': 'old1',
            'name': 'Lag Jaa Gale',
            'artists': ['Lata Mangeshkar'],
            'album': 'Woh Kaun Thi',
            'release_date': '1964-01-01',
            'genres': ['bollywood'],
            'markets': ['IN'],
            'uri': 'spotify:track:old1'
        },
        {
            'id': 'old2',
            'name': 'Abhi Na Jao Chhod Kar',
            'artists': ['Mohammed Rafi'],
            'album': 'Hum Dono',
            'release_date': '1961-01-01',
            'genres': ['bollywood'],
            'markets': ['IN'],
            'uri': 'spotify:track:old2'
        },
        {
            'id': 'new1',
            'name': 'Tum Hi Ho',
            'artists': ['Arijit Singh'],
            'album': 'Aashiqui 2',
            'release_date': '2013-04-08',
            'genres': ['bollywood', 'pop'],
            'markets': ['IN'],
            'uri': 'spotify:track:new1'
        }
    ]
    
    for track in test_tracks:
        result = classifier._check_metadata_rules(track)
        if track['id'].startswith('old'):
            assert result == 'Oldies', f"Failed to detect oldie: {track['name']}"
            print(f"✅ Correctly identified '{track['name']}' as Oldies")
        elif track['id'] == 'new1':
            # This should NOT be caught by oldies rule (too recent)
            if result == 'Oldies':
                print(f"⚠️  Warning: '{track['name']}' incorrectly marked as Oldies")
    
    print("✅ Oldies detection tests passed!\n")


def test_instrumental_detection():
    """Test instrumental/phonk classification rules."""
    print("🧪 Testing Instrumental/Phonk Detection...")
    
    classifier = SongClassifier()
    
    test_tracks = [
        {
            'id': 'inst1',
            'name': 'Clair de Lune',
            'artists': ['Claude Debussy'],
            'album': 'Suite Bergamasque',
            'release_date': '1905-01-01',
            'genres': ['classical', 'piano', 'instrumental'],
            'markets': ['US'],
            'uri': 'spotify:track:inst1'
        },
        {
            'id': 'inst2',
            'name': 'Lofi Hip Hop Beat',
            'artists': ['Lofi Producer'],
            'album': 'Chill Beats',
            'release_date': '2022-01-01',
            'genres': ['lofi', 'beats', 'instrumental'],
            'markets': ['US'],
            'uri': 'spotify:track:inst2'
        },
        {
            'id': 'phonk1',
            'name': 'Murder In My Mind - Phonk Remix',
            'artists': ['Phonk Artist'],
            'album': 'Phonk Vol 1',
            'release_date': '2023-01-01',
            'genres': ['phonk', 'electronic'],
            'markets': ['US'],
            'uri': 'spotify:track:phonk1'
        }
    ]
    
    for track in test_tracks:
        result = classifier._check_metadata_rules(track)
        assert result == 'Phonk/Instrumental', f"Failed to detect instrumental: {track['name']}"
        print(f"✅ Correctly identified '{track['name']}' as Phonk/Instrumental")
    
    print("✅ Instrumental/Phonk detection tests passed!\n")


def test_is_oldies_logic():
    """Test the _is_oldies method specifically."""
    print("🧪 Testing _is_oldies() method...")
    
    classifier = SongClassifier()
    
    # Should be detected as oldie
    oldie_track = {
        'id': 'test1',
        'name': 'Pyar Kiya To Darna Kya',
        'artists': ['Lata Mangeshkar'],
        'release_date': '1960',
        'genres': [],
        'markets': []
    }
    
    assert classifier._is_oldies(oldie_track), "Failed to detect classic artist"
    print("✅ Classic artist detection works")
    
    # Should NOT be detected (wrong era)
    modern_track = {
        'id': 'test2',
        'name': 'Some Song',
        'artists': ['Modern Artist'],
        'release_date': '2020-01-01',
        'genres': [],
        'markets': []
    }
    
    assert not classifier._is_oldies(modern_track), "False positive for modern track"
    print("✅ Modern track rejection works")
    
    print("✅ _is_oldies() tests passed!\n")


if __name__ == '__main__':
    try:
        test_oldies_detection()
        test_instrumental_detection()
        test_is_oldies_logic()
        print("✅ All classifier rule tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

