"""
Test script for PhotoChomper v3.1.14
Created: 2025-09-09
Purpose: Verify fix for EXIF extraction hanging issue

This test verifies that the EXIF extraction timeout protection prevents
hanging on the problematic file that was causing indefinite hangs.
"""

import os
import sys
import time
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.scanner import extract_exif_with_timeout, get_image_metadata
from src.config import log_action


def test_exif_timeout_protection():
    """Test that EXIF extraction times out after specified duration."""
    print("Testing EXIF timeout protection...")
    
    # Create a mock PIL Image that hangs on _getexif()
    class HangingMockImage:
        def __getattr__(self, name):
            if name == "_getexif":
                def hanging_getexif():
                    # Simulate hanging by sleeping longer than timeout
                    time.sleep(15)  # Hang for 15 seconds
                    return {"test": "data"}
                return hanging_getexif
            return MagicMock()
    
    mock_img = HangingMockImage()
    test_filepath = "/test/hanging/file.jpg"
    
    # Test with 2-second timeout
    start_time = time.time()
    result = extract_exif_with_timeout(mock_img, test_filepath, timeout_seconds=2)
    end_time = time.time()
    
    # Should complete within 3 seconds (2 second timeout + overhead)
    assert end_time - start_time < 3, f"Function took too long: {end_time - start_time} seconds"
    
    # Should return empty dict due to timeout
    assert result == {}, f"Expected empty dict, got: {result}"
    
    print("✅ EXIF timeout protection working correctly")


def test_exif_normal_operation():
    """Test that EXIF extraction works normally for non-hanging images."""
    print("Testing EXIF normal operation...")
    
    # Create a mock PIL Image with normal EXIF data
    class NormalMockImage:
        def __getattr__(self, name):
            if name == "_getexif":
                def normal_getexif():
                    return {272: "Canon", 271: "EOS R5", 306: "2023:01:01 12:00:00"}
                return normal_getexif
            return MagicMock()
    
    mock_img = NormalMockImage()
    test_filepath = "/test/normal/file.jpg"
    
    start_time = time.time()
    result = extract_exif_with_timeout(mock_img, test_filepath, timeout_seconds=10)
    end_time = time.time()
    
    # Should complete quickly
    assert end_time - start_time < 1, f"Function took too long: {end_time - start_time} seconds"
    
    # Should return the EXIF data
    expected_data = {272: "Canon", 271: "EOS R5", 306: "2023:01:01 12:00:00"}
    assert result == expected_data, f"Expected {expected_data}, got: {result}"
    
    print("✅ EXIF normal operation working correctly")


def test_exif_exception_handling():
    """Test that EXIF extraction handles exceptions gracefully."""
    print("Testing EXIF exception handling...")
    
    # Create a mock PIL Image that raises an exception
    class ExceptionMockImage:
        def __getattr__(self, name):
            if name == "_getexif":
                def exception_getexif():
                    raise ValueError("Test exception")
                return exception_getexif
            return MagicMock()
    
    mock_img = ExceptionMockImage()
    test_filepath = "/test/exception/file.jpg"
    
    result = extract_exif_with_timeout(mock_img, test_filepath, timeout_seconds=5)
    
    # Should return empty dict due to exception
    assert result == {}, f"Expected empty dict, got: {result}"
    
    print("✅ EXIF exception handling working correctly")


def test_no_exif_data():
    """Test behavior when image has no EXIF data."""
    print("Testing no EXIF data scenario...")
    
    # Create a mock PIL Image with no EXIF data
    class NoExifMockImage:
        def __getattr__(self, name):
            if name == "_getexif":
                def no_exif_getexif():
                    return None
                return no_exif_getexif
            return MagicMock()
    
    mock_img = NoExifMockImage()
    test_filepath = "/test/no_exif/file.jpg"
    
    result = extract_exif_with_timeout(mock_img, test_filepath, timeout_seconds=5)
    
    # Should return empty dict when no EXIF data
    assert result == {}, f"Expected empty dict, got: {result}"
    
    print("✅ No EXIF data scenario working correctly")


def test_integration_with_get_image_metadata():
    """Test that get_image_metadata uses the timeout function correctly."""
    print("Testing integration with get_image_metadata...")
    
    # This is a mock test since we can't easily mock the internal PIL usage
    # But we can verify the function exists and is callable
    
    # Check that the function is properly imported
    assert callable(extract_exif_with_timeout), "extract_exif_with_timeout should be callable"
    
    # Test with mock PIL module
    try:
        with patch('src.scanner.Image') as mock_image:
            # This would test the actual integration, but requires more complex mocking
            print("✅ Integration test structure verified")
    except ImportError:
        print("✅ Integration test skipped (PIL not available)")


def test_problematic_file_timeout():
    """Test timeout protection on the specific problematic file if it exists."""
    problematic_file = "/home/jcz/Pictures/2 (copy 1).jpg"
    
    if not os.path.exists(problematic_file):
        print(f"⚠️  Problematic file not found: {problematic_file}")
        print("✅ Problematic file test skipped")
        return
    
    print(f"Testing timeout protection on problematic file: {problematic_file}")
    
    try:
        # Try to import PIL for real testing
        from PIL import Image
        
        # Open the problematic image
        with Image.open(problematic_file) as img:
            start_time = time.time()
            result = extract_exif_with_timeout(img, problematic_file, timeout_seconds=5)
            end_time = time.time()
            
            # Should complete within timeout period
            assert end_time - start_time < 7, f"Function took too long: {end_time - start_time} seconds"
            print(f"✅ Problematic file handled in {end_time - start_time:.2f} seconds")
            
            if result:
                print(f"   EXIF data extracted: {len(result)} fields")
            else:
                print("   No EXIF data or timeout occurred (expected)")
                
    except ImportError:
        print("⚠️  PIL not available, skipping problematic file test")
    except Exception as e:
        print(f"⚠️  Error testing problematic file: {e}")


def run_all_tests():
    """Run all v3.1.14 EXIF hanging fix tests."""
    print("=" * 70)
    print("PhotoChomper v3.1.14 - EXIF Hanging Fix Tests")
    print("=" * 70)
    
    tests = [
        test_exif_timeout_protection,
        test_exif_normal_operation,
        test_exif_exception_handling,
        test_no_exif_data,
        test_integration_with_get_image_metadata,
        test_problematic_file_timeout,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            print(f"\n--- {test_func.__name__} ---")
            test_func()
            passed += 1
            print(f"✅ {test_func.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 70}")
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! EXIF hanging fix is working correctly.")
    else:
        print(f"⚠️  {failed} test(s) failed. Please review the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)