#!/usr/bin/env python3
"""
Test script to verify the hanging fix works properly.
"""

import os
import sys
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from report import extract_metadata_with_timeout
    from config import log_action
    print("✓ Successfully imported report functions")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def test_metadata_extraction():
    """Test metadata extraction on actual files."""
    print("=== Testing Metadata Extraction Fix ===")
    
    # Find test files
    test_files = []
    for root, dirs, files in os.walk('/home/jcz/Pictures'):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                test_files.append(os.path.join(root, file))
                if len(test_files) >= 3:  # Test first 3 files
                    break
        if len(test_files) >= 3:
            break
    
    if not test_files:
        print("No test files found")
        return False
    
    print(f"Testing metadata extraction on {len(test_files)} files...")
    
    all_passed = True
    for i, filepath in enumerate(test_files, 1):
        print(f"\nTest {i}/{len(test_files)}: {os.path.basename(filepath)}")
        
        start_time = time.time()
        try:
            metadata = extract_metadata_with_timeout(filepath, timeout_seconds=5)
            elapsed = time.time() - start_time
            
            print(f"  ✓ Completed in {elapsed:.2f}s")
            print(f"  ✓ File: {metadata.get('name', 'Unknown')}")
            print(f"  ✓ Size: {metadata.get('size', 0)} bytes")
            print(f"  ✓ Type: {metadata.get('file_type', 'Unknown')}")
            
            # Check that we got basic metadata
            if not metadata.get('name') or not metadata.get('path'):
                print(f"  ✗ Missing basic metadata")
                all_passed = False
            else:
                print(f"  ✓ Metadata extraction successful")
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ✗ Failed after {elapsed:.2f}s: {e}")
            all_passed = False
        
        # Check for hanging (should complete quickly)
        if elapsed > 3.0:
            print(f"  ⚠ Took longer than expected: {elapsed:.2f}s")
    
    return all_passed

def main():
    print("PhotoChomper Hanging Fix Test")
    print("=" * 40)
    
    success = test_metadata_extraction()
    
    print("\n" + "=" * 40)
    if success:
        print("✓ All tests PASSED - Hanging fix is working!")
        print("✓ Report generation should now complete without hanging")
    else:
        print("✗ Some tests FAILED - Fix may need adjustment")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)