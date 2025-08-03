#!/usr/bin/env python3
"""
Test script for the enhanced perceptual hashing functionality.
"""

import os
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np

from src.scanner import (
    HashAlgorithm, compute_perceptual_hash, calculate_hash_similarity,
    find_duplicates, get_file_type, FileType
)
from src.config import log_action

def create_test_images():
    """Create test images for duplicate detection testing."""
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_test_"))
    
    # Create a base image
    base_img = Image.new('RGB', (100, 100), color='red')
    base_path = test_dir / "original.jpg"
    base_img.save(base_path)
    
    # Create a slightly modified version (should be detected as similar)
    similar_img = base_img.copy()
    # Add a small modification
    pixels = similar_img.load()
    for i in range(5):
        for j in range(5):
            pixels[i, j] = (255, 255, 255)  # White corner
    similar_path = test_dir / "similar.jpg"  
    similar_img.save(similar_path)
    
    # Create an exact copy (should be detected as identical)
    exact_path = test_dir / "exact_copy.jpg"
    base_img.save(exact_path)
    
    # Create a completely different image
    different_img = Image.new('RGB', (100, 100), color='blue')
    different_path = test_dir / "different.jpg"
    different_img.save(different_path)
    
    return test_dir, [str(base_path), str(similar_path), str(exact_path), str(different_path)]

def test_perceptual_hashing():
    """Test perceptual hashing algorithms."""
    print("🧪 Testing Perceptual Hashing System...")
    
    test_dir, test_files = create_test_images()
    
    try:
        # Test different hash algorithms
        algorithms = [HashAlgorithm.DHASH, HashAlgorithm.PHASH, HashAlgorithm.AHASH]
        
        for algorithm in algorithms:
            print(f"\n📊 Testing {algorithm.value} algorithm:")
            
            # Compute hashes for all test images
            hashes = []
            for filepath in test_files:
                result = compute_perceptual_hash(filepath, algorithm)
                hashes.append(result)
                print(f"  {Path(filepath).name}: {result.hash_value[:16]}... (error: {result.error})")
            
            # Test similarity calculations
            print("  Similarity matrix:")
            for i, hash1 in enumerate(hashes):
                for j, hash2 in enumerate(hashes):
                    if i <= j:
                        continue
                    similarity = calculate_hash_similarity(hash1.hash_value, hash2.hash_value, algorithm)
                    file1_name = Path(hash1.file_path).name
                    file2_name = Path(hash2.file_path).name
                    print(f"    {file1_name} vs {file2_name}: {similarity:.3f}")
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)

def test_file_type_detection():
    """Test file type detection."""
    print("\n🔍 Testing File Type Detection...")
    
    test_cases = [
        ("photo.jpg", FileType.IMAGE),
        ("video.mp4", FileType.VIDEO),
        ("document.pdf", FileType.UNKNOWN),
        ("image.png", FileType.IMAGE),
        ("movie.avi", FileType.VIDEO),
        ("raw.cr2", FileType.IMAGE),
        ("modern.heic", FileType.IMAGE),
        ("clip.mov", FileType.VIDEO),
    ]
    
    for filename, expected in test_cases:
        detected = get_file_type(filename)
        status = "✅" if detected == expected else "❌"
        print(f"  {status} {filename}: {detected.value} (expected: {expected.value})")

def test_duplicate_detection():
    """Test the enhanced find_duplicates function."""
    print("\n🔎 Testing Duplicate Detection...")
    
    test_dir, test_files = create_test_images()
    
    try:
        # Test with different algorithms and thresholds
        test_configs = [
            (HashAlgorithm.SHA256, 0.0, "Exact matching"),
            (HashAlgorithm.DHASH, 0.1, "Similar matching (strict)"),
            (HashAlgorithm.DHASH, 0.3, "Similar matching (loose)"),
        ]
        
        for algorithm, threshold, description in test_configs:
            print(f"\n  {description} ({algorithm.value}, threshold={threshold}):")
            
            dupes = find_duplicates(
                dirs=[str(test_dir)],
                types=["jpg"],
                exclude_dirs=[],
                similarity_threshold=threshold,
                algorithm=algorithm,
                max_workers=2
            )
            
            print(f"    Found {len(dupes)} duplicate groups")
            for i, group in enumerate(dupes):
                files = [Path(f).name for f in group]
                print(f"      Group {i+1}: {files}")
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)

def main():
    """Run all tests."""
    print("🚀 PhotoChomper Enhanced Functionality Tests")
    print("=" * 50)
    
    try:
        test_file_type_detection()
        test_perceptual_hashing()
        test_duplicate_detection()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()