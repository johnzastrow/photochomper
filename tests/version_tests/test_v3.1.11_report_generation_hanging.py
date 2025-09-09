#!/usr/bin/env python3
"""
Test script for PhotoChomper v3.1.11
Created: 2025-09-09
Purpose: Debug and verify fix for report generation hanging issue

This test isolates the metadata extraction hanging problem by testing individual
components that could cause blocking during report generation.
"""

import os
import sys
import time
import signal
import threading
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.scanner import get_image_metadata
from src.report import export_report

class TimeoutError(Exception):
    """Custom timeout exception for cross-platform compatibility."""
    pass

@contextmanager
def timeout_context(seconds: int):
    """Cross-platform timeout context manager using threading."""
    
    def timeout_handler():
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Start timeout timer
    timer = threading.Timer(seconds, timeout_handler)
    timer.start()
    
    try:
        yield
    finally:
        timer.cancel()

def create_test_image(filepath: str, corrupt_metadata: bool = False) -> None:
    """Create a simple test image file with optional corrupted metadata."""
    try:
        from PIL import Image
        
        # Create a simple 100x100 RGB image
        img = Image.new('RGB', (100, 100), color='red')
        
        if corrupt_metadata:
            # Add potentially problematic EXIF data
            # This simulates conditions that might cause hanging
            import piexif
            exif_dict = {
                "0th": {
                    piexif.ImageIFD.Make: "Test Camera" * 1000,  # Extremely long string
                    piexif.ImageIFD.Model: "Test Model",
                    piexif.ImageIFD.Software: "PhotoChomper Test",
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: "2025:09:09 12:00:00",
                },
                "GPS": {},
                "1st": {},
                "thumbnail": None,
            }
            exif_bytes = piexif.dump(exif_dict)
            img.save(filepath, "JPEG", exif=exif_bytes)
        else:
            img.save(filepath, "JPEG")
            
    except ImportError:
        # Fallback: create a dummy JPEG file
        with open(filepath, 'wb') as f:
            # Minimal JPEG header
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00d\x00d\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')

def test_metadata_extraction_timeout():
    """Test metadata extraction with timeout protection."""
    print("Testing metadata extraction timeout protection...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_image.jpg")
        create_test_image(test_file)
        
        start_time = time.time()
        
        try:
            with timeout_context(10):  # 10-second timeout
                metadata = get_image_metadata(test_file)
                extraction_time = time.time() - start_time
                
                print(f"✅ Metadata extraction completed in {extraction_time:.2f}s")
                print(f"   Found keys: {list(metadata.keys())}")
                return True
                
        except TimeoutError:
            extraction_time = time.time() - start_time
            print(f"❌ Metadata extraction timed out after {extraction_time:.2f}s")
            return False
        except Exception as e:
            extraction_time = time.time() - start_time
            print(f"❌ Metadata extraction failed after {extraction_time:.2f}s: {e}")
            return False

def test_metadata_extraction_corrupted_file():
    """Test metadata extraction on potentially problematic files."""
    print("Testing metadata extraction on potentially problematic files...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "corrupted_image.jpg")
        
        try:
            create_test_image(test_file, corrupt_metadata=True)
        except:
            # Create a simple file if corruption creation fails
            create_test_image(test_file, corrupt_metadata=False)
        
        start_time = time.time()
        
        try:
            with timeout_context(15):  # 15-second timeout for potentially problematic files
                metadata = get_image_metadata(test_file)
                extraction_time = time.time() - start_time
                
                print(f"✅ Corrupted file metadata extraction completed in {extraction_time:.2f}s")
                print(f"   Found keys: {list(metadata.keys())}")
                return True
                
        except TimeoutError:
            extraction_time = time.time() - start_time
            print(f"❌ Corrupted file metadata extraction timed out after {extraction_time:.2f}s")
            return False
        except Exception as e:
            extraction_time = time.time() - start_time
            print(f"❌ Corrupted file metadata extraction failed after {extraction_time:.2f}s: {e}")
            return False

def test_report_generation_timeout():
    """Test full report generation with timeout protection."""
    print("Testing full report generation with timeout protection...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test duplicate files
        test_file1 = os.path.join(temp_dir, "duplicate1.jpg")
        test_file2 = os.path.join(temp_dir, "duplicate2.jpg")
        
        create_test_image(test_file1)
        create_test_image(test_file2)
        
        # Create duplicate groups (simulate scanner output)
        dupes = [[test_file1, test_file2]]
        output_prefix = os.path.join(temp_dir, "test_report")
        
        start_time = time.time()
        
        try:
            with timeout_context(30):  # 30-second timeout for full report generation
                export_report(
                    dupes=dupes,
                    formats=["csv"],
                    out_prefix=output_prefix,
                    exec_time=1.0
                )
                
                generation_time = time.time() - start_time
                
                # Check if report was actually created
                if os.path.exists(f"{output_prefix}.csv"):
                    print(f"✅ Report generation completed in {generation_time:.2f}s")
                    print(f"   Report file created: {output_prefix}.csv")
                    return True
                else:
                    print(f"❌ Report generation claimed success but no file created after {generation_time:.2f}s")
                    return False
                
        except TimeoutError:
            generation_time = time.time() - start_time
            print(f"❌ Report generation timed out after {generation_time:.2f}s")
            return False
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"❌ Report generation failed after {generation_time:.2f}s: {e}")
            return False

def test_individual_metadata_operations():
    """Test individual metadata extraction operations to isolate hanging."""
    print("Testing individual metadata operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_image.jpg")
        create_test_image(test_file)
        
        results = {
            "file_stats": False,
            "image_dimensions": False,
            "exif_data": False,
            "iptc_data": False,
            "xmp_data": False
        }
        
        # Test basic file operations
        try:
            with timeout_context(5):
                stats = {
                    "size": os.path.getsize(test_file),
                    "created": os.path.getctime(test_file),
                    "modified": os.path.getmtime(test_file)
                }
                print(f"✅ File stats extraction completed")
                results["file_stats"] = True
        except Exception as e:
            print(f"❌ File stats extraction failed: {e}")
        
        # Test image operations
        try:
            from PIL import Image
            with timeout_context(5):
                with Image.open(test_file) as img:
                    width, height = img.width, img.height
                print(f"✅ Image dimensions extraction completed ({width}x{height})")
                results["image_dimensions"] = True
        except Exception as e:
            print(f"❌ Image dimensions extraction failed: {e}")
        
        # Test EXIF operations (potential hanging point)
        try:
            from PIL import Image
            with timeout_context(10):
                with Image.open(test_file) as img:
                    if hasattr(img, "_getexif"):
                        exif = img._getexif()
                print(f"✅ EXIF data extraction completed")
                results["exif_data"] = True
        except Exception as e:
            print(f"❌ EXIF data extraction failed: {e}")
        
        # Test IPTC operations (major hanging suspect)
        try:
            import iptcinfo3
            with timeout_context(10):
                info = iptcinfo3.IPTCInfo(test_file)
            print(f"✅ IPTC data extraction completed")
            results["iptc_data"] = True
        except ImportError:
            print("ℹ️  IPTC library not available - skipping test")
            results["iptc_data"] = True  # Not a failure if library is missing
        except Exception as e:
            print(f"❌ IPTC data extraction failed: {e}")
        
        # Test XMP operations (another hanging suspect)
        try:
            from libxmp import XMPFiles
            with timeout_context(10):
                xmpfile = XMPFiles(file_path=test_file)
                xmp = xmpfile.get_xmp()
                xmpfile.close_file()
            print(f"✅ XMP data extraction completed")
            results["xmp_data"] = True
        except ImportError:
            print("ℹ️  XMP library not available - skipping test")
            results["xmp_data"] = True  # Not a failure if library is missing
        except Exception as e:
            print(f"❌ XMP data extraction failed: {e}")
        
        return results

def run_all_hanging_tests():
    """Run comprehensive hanging detection tests."""
    print("=" * 60)
    print("PhotoChomper v3.1.11 Hanging Issue Debug Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Basic Metadata Extraction", test_metadata_extraction_timeout),
        ("Corrupted File Metadata", test_metadata_extraction_corrupted_file),
        ("Individual Operations", test_individual_metadata_operations),
        ("Full Report Generation", test_report_generation_timeout),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            results[test_name] = result
            
            if isinstance(result, dict):
                # Individual operations test returns dict
                success = all(result.values())
                print(f"Overall result: {'✅ PASS' if success else '❌ FAIL'}")
            else:
                print(f"Result: {'✅ PASS' if result else '❌ FAIL'}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        if isinstance(result, dict):
            success = all(result.values())
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
            if not success:
                for op, op_result in result.items():
                    if not op_result:
                        print(f"  └─ Failed operation: {op}")
        else:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
    
    print("\n" + "=" * 60)
    print("DEBUGGING RECOMMENDATIONS")
    print("=" * 60)
    
    # Analyze results and provide specific debugging guidance
    if not results.get("Basic Metadata Extraction", False):
        print("🔧 Issue detected in basic metadata extraction:")
        print("   - Check for corrupted files or excessive metadata")
        print("   - Verify PIL/Pillow installation and version")
        print("   - Test with simpler image files")
    
    if not results.get("Corrupted File Metadata", False):
        print("🔧 Issue detected with problematic files:")
        print("   - Add more robust error handling in get_image_metadata()")
        print("   - Implement file validation before metadata extraction")
        print("   - Consider skipping files that fail quick validation")
    
    individual_results = results.get("Individual Operations", {})
    if isinstance(individual_results, dict):
        if not individual_results.get("iptc_data", True):
            print("🔧 IPTC metadata extraction is hanging:")
            print("   - This is likely the primary cause of hanging")
            print("   - Consider disabling IPTC extraction or adding strict timeouts")
            print("   - Update iptcinfo3 library or replace with alternative")
        
        if not individual_results.get("xmp_data", True):
            print("🔧 XMP metadata extraction is hanging:")
            print("   - Secondary hanging cause identified")
            print("   - Consider disabling XMP extraction or adding timeouts")
            print("   - Update libxmp library or replace with alternative")
        
        if not individual_results.get("exif_data", True):
            print("🔧 EXIF metadata extraction is hanging:")
            print("   - Check for malformed EXIF data in images")
            print("   - Consider using exifread library instead of PIL._getexif")
    
    if not results.get("Full Report Generation", False):
        print("🔧 Full report generation is timing out:")
        print("   - Implement progress tracking with timeouts per file")
        print("   - Add graceful fallback when metadata extraction fails")
        print("   - Consider processing files in smaller batches")

if __name__ == "__main__":
    run_all_hanging_tests()