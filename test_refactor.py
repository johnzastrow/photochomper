#!/usr/bin/env python3
"""
Simple test for the refactored report generation.
"""
import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_basic_import():
    """Test that we can import the refactored module."""
    try:
        from src.report import export_report, safe_get_metadata, process_single_group
        print("✓ Successfully imported refactored report module")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_safe_metadata_fallback():
    """Test that safe_get_metadata handles missing files gracefully."""
    try:
        from src.report import safe_get_metadata
        
        # Test with non-existent file
        result = safe_get_metadata("/non/existent/file.jpg")
        
        if isinstance(result, dict) and "name" in result:
            print("✓ safe_get_metadata returns fallback metadata for missing files")
            return True
        else:
            print("✗ safe_get_metadata did not return expected fallback")
            return False
    except Exception as e:
        print(f"✗ safe_get_metadata test failed: {e}")
        return False

def test_basic_structure():
    """Test basic structure of refactored functions."""
    try:
        from src.report import export_report
        
        # Create test data
        test_dupes = [
            ["/test1.jpg", "/test2.jpg"],  # One group
        ]
        
        temp_dir = tempfile.mkdtemp()
        output_prefix = os.path.join(temp_dir, "test_report")
        
        # This should run without crashing (even if metadata fails)
        export_report(
            dupes=test_dupes,
            formats=["csv"],
            out_prefix=output_prefix
        )
        
        print("✓ export_report completed without crashing")
        return True
        
    except Exception as e:
        print(f"✗ Basic structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Refactored Report Generation (v3.2.0)")
    print("=" * 50)
    
    tests = [
        test_basic_import,
        test_safe_metadata_fallback, 
        test_basic_structure,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        print(f"\nRunning {test_func.__name__}...")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Refactor appears to be working.")
    else:
        print("❌ Some tests failed. Check the output above.")
        
    print("=" * 50)