"""Test LLM classifier with mock responses (no actual vLLM needed)."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from llm_classifier import LLMClassifier
except ImportError as e:
    print(f"⚠️  Skipping LLM tests - missing dependencies: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(0)


def test_prompt_building():
    """Test that prompts are built correctly."""
    print("🧪 Testing LLM Prompt Building...")
    
    classifier = LLMClassifier()
    
    test_track = {
        'id': 'test1',
        'name': 'Tum Hi Ho',
        'artists': ['Arijit Singh'],
        'album': 'Aashiqui 2',
        'release_date': '2013-04-08',
        'genres': ['bollywood', 'romantic'],
        'markets': ['IN', 'US', 'GB'],
        'uri': 'spotify:track:test1'
    }
    
    prompt = classifier._build_prompt(test_track)
    
    # Check that all important fields are in prompt
    assert 'Tum Hi Ho' in prompt, "Track name missing from prompt"
    assert 'Arijit Singh' in prompt, "Artist missing from prompt"
    assert 'Aashiqui 2' in prompt, "Album missing from prompt"
    assert '2013' in prompt, "Year missing from prompt"
    assert 'bollywood' in prompt or 'romantic' in prompt, "Genres missing from prompt"
    
    print("✅ Prompt contains all required fields")
    print(f"\nSample prompt (first 300 chars):\n{prompt[:300]}...\n")
    
    print("✅ Prompt building tests passed!\n")


def test_response_parsing():
    """Test response parsing logic."""
    print("🧪 Testing LLM Response Parsing...")
    
    classifier = LLMClassifier()
    
    test_responses = [
        {
            'response': 'Category: Hindi\nConfidence: 0.95\nReasoning: Bollywood song',
            'expected_category': 'Hindi',
            'expected_confidence': 0.95
        },
        {
            'response': 'Category: English\nConfidence: 0.88\nReasoning: Pop song',
            'expected_category': 'English',
            'expected_confidence': 0.88
        },
        {
            'response': 'Category: Phonk/Instrumental\nConfidence: 0.92',
            'expected_category': 'Phonk/Instrumental',
            'expected_confidence': 0.92
        },
        {
            'response': 'Category: Oldies\nConfidence: 0.98\nReasoning: Classic Lata',
            'expected_category': 'Oldies',
            'expected_confidence': 0.98
        },
        {
            'response': 'Category: Uncertain\nConfidence: 0.45\nReasoning: Cannot determine',
            'expected_category': 'Misc',
            'expected_confidence': 0.45
        }
    ]
    
    for i, test in enumerate(test_responses):
        category, confidence = classifier._parse_response(test['response'])
        assert category == test['expected_category'], \
            f"Test {i+1}: Expected category '{test['expected_category']}', got '{category}'"
        assert abs(confidence - test['expected_confidence']) < 0.01, \
            f"Test {i+1}: Expected confidence {test['expected_confidence']}, got {confidence}"
        print(f"✅ Test {i+1}: Correctly parsed '{test['expected_category']}' with confidence {confidence}")
    
    print("\n✅ Response parsing tests passed!\n")


def test_category_normalization():
    """Test category name normalization."""
    print("🧪 Testing Category Normalization...")
    
    classifier = LLMClassifier()
    
    test_cases = [
        ('english', 'English'),
        ('HINDI', 'Hindi'),
        ('punjabi music', 'Punjabi'),
        ('Phonk', 'Phonk/Instrumental'),
        ('instrumental', 'Phonk/Instrumental'),
        ('Oldies (Hindi classics)', 'Oldies'),
        ('Classic', 'Oldies'),
        ('Uncertain', 'Misc'),
        ('Unknown', 'Misc'),
        ('something weird', 'Misc'),
    ]
    
    for raw, expected in test_cases:
        result = classifier._normalize_category(raw)
        assert result == expected, f"Expected '{expected}' for '{raw}', got '{result}'"
        print(f"✅ '{raw}' → '{result}'")
    
    print("\n✅ Category normalization tests passed!\n")


if __name__ == '__main__':
    try:
        test_prompt_building()
        test_response_parsing()
        test_category_normalization()
        print("✅ All LLM classifier tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

