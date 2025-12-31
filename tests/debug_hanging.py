#!/usr/bin/env python3
"""
Debug script to identify which files are causing PhotoChomper to hang during metadata extraction.
This script tests metadata extraction on individual files to isolate the problematic one.
"""

import os
import sys
import time
import signal
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def timeout_handler(signum, frame):
    raise TimeoutError("File processing timed out")

def test_file_access(filepath):
    """Test basic file operations that could hang."""
    print(f"Testing file access: {filepath}")
    
    try:
        # Test basic file stats
        print(f"  - File exists: {os.path.exists(filepath)}")
        print(f"  - File size: {os.path.getsize(filepath)} bytes")
        print(f"  - File type: {Path(filepath).suffix}")
        
        # Test file opening
        print("  - Opening file for reading...")
        with open(filepath, 'rb') as f:
            # Read first 1024 bytes
            data = f.read(1024)
            print(f"  - Successfully read {len(data)} bytes")
        
        return True
        
    except Exception as e:
        print(f"  - ERROR: {e}")
        return False

def test_basic_metadata(filepath):
    """Test basic os metadata that's used in get_image_metadata."""
    print(f"Testing basic metadata: {filepath}")
    
    try:
        # Test the basic operations from get_image_metadata
        created = os.path.getctime(filepath)
        modified = os.path.getmtime(filepath)
        size = os.path.getsize(filepath)
        name = os.path.basename(filepath)
        
        print(f"  - Created: {time.ctime(created)}")
        print(f"  - Modified: {time.ctime(modified)}")
        print(f"  - Size: {size} bytes")
        print(f"  - Name: {name}")
        
        return True
        
    except Exception as e:
        print(f"  - ERROR in basic metadata: {e}")
        return False

def find_duplicate_files():
    """Find the files that were being processed when hanging occurred."""
    print("Looking for image files in /home/jcz/Pictures...")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
    files = []
    
    try:
        for root, dirs, filenames in os.walk('/home/jcz/Pictures'):
            for filename in filenames:
                if Path(filename).suffix.lower() in image_extensions:
                    filepath = os.path.join(root, filename)
                    files.append(filepath)
                    if len(files) >= 10:  # Limit to first 10 files for testing
                        break
            if len(files) >= 10:
                break
                
    except Exception as e:
        print(f"Error walking directory: {e}")
    
    return files

def main():
    print("=== PhotoChomper Hanging Debug Script ===")
    print("This script will test file access and metadata extraction to identify problematic files.")
    print()
    
    # Find some test files
    test_files = find_duplicate_files()
    
    if not test_files:
        print("No test files found in /home/jcz/Pictures")
        return
    
    print(f"Found {len(test_files)} test files to analyze")
    print()
    
    for i, filepath in enumerate(test_files, 1):
        print(f"=== Test File {i}/{len(test_files)} ===")
        print(f"File: {filepath}")
        
        # Set up timeout handler
        signal.signal(signal.SIGALRM, timeout_handler)
        
        try:
            # Test with 5 second timeout
            signal.alarm(5)
            
            # Test basic file access
            if not test_file_access(filepath):
                print(f"  PROBLEM: Basic file access failed for {filepath}")
                continue
            
            # Test basic metadata
            if not test_basic_metadata(filepath):
                print(f"  PROBLEM: Basic metadata extraction failed for {filepath}")
                continue
                
            print(f"  SUCCESS: File {filepath} processed without hanging")
            
        except TimeoutError:
            print(f"  HANGING FILE FOUND: {filepath}")
            print("  This file causes a timeout and is likely the source of the hanging issue!")
            return filepath
            
        except Exception as e:
            print(f"  ERROR: {e}")
            
        finally:
            signal.alarm(0)  # Cancel alarm
        
        print()
    
    print("All test files processed successfully. The hanging issue may be:")
    print("1. Related to specific EXIF/metadata extraction libraries")
    print("2. Caused by a file not in this sample")
    print("3. Related to threading or concurrent processing")

if __name__ == "__main__":
    main()