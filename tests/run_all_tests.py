#!/usr/bin/env python3
"""Run all tests sequentially."""
import os
import sys
import subprocess

# Test files in order
TESTS = [
    'test_cache.py',
    'test_llm_mock.py',
    'test_classifier_rules.py',
]

def run_test(test_file):
    """Run a single test file."""
    test_path = os.path.join(os.path.dirname(__file__), test_file)
    
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)
    
    result = subprocess.run([sys.executable, test_path], capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {test_file} FAILED")
        return False
    
    print(f"\n✅ {test_file} PASSED")
    return True


def main():
    """Run all tests."""
    print("🧪 Running Spotify LLM Organizer Test Suite")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_file in TESTS:
        if run_test(test_file):
            passed += 1
        else:
            failed += 1
            # Stop on first failure
            break
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print('='*60)
    
    if failed > 0:
        print("\n❌ Some tests failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()

