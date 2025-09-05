#!/usr/bin/env python3
"""
Test script for video file support and metadata extraction.
"""

import tempfile
from pathlib import Path
import subprocess

from src.scanner import (
    HashAlgorithm,
    compute_video_hash,
    get_image_metadata,
    find_duplicates,
    get_file_type,
    compute_video_similarity,
)


def create_test_video(
    filepath: str, duration: int = 3, color: str = "red", resolution: str = "320x240"
):
    """Create a test video using ffmpeg."""
    try:
        # Use ffmpeg to create a test video
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-f",
            "lavfi",  # Use libavfilter input
            "-i",
            f"testsrc2=duration={duration}:size={resolution}:rate=30,format=yuv420p",
            "-f",
            "lavfi",  # Audio input
            "-i",
            f"sine=frequency=1000:duration={duration}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            filepath,
        ]

        # Run ffmpeg quietly
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(
                f"⚠️  Warning: Could not create test video with ffmpeg: {result.stderr}"
            )
            return False

        return True

    except FileNotFoundError:
        print("⚠️  Warning: ffmpeg not found. Skipping video tests.")
        return False
    except Exception as e:
        print(f"⚠️  Warning: Error creating test video: {e}")
        return False


def test_video_metadata():
    """Test video metadata extraction."""
    print("📹 Testing Video Metadata Extraction...")

    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_video_test_"))

    try:
        # Create test videos
        test_videos = []
        video_configs = [
            ("video_hd.mp4", 5, "red", "1280x720"),
            ("video_sd.mp4", 3, "blue", "640x480"),
            ("video_4k.mp4", 2, "green", "3840x2160"),
        ]

        for filename, duration, color, resolution in video_configs:
            video_path = test_dir / filename
            if create_test_video(str(video_path), duration, color, resolution):
                test_videos.append(str(video_path))

        if not test_videos:
            print(
                "  ❌ No test videos could be created. Skipping video metadata tests."
            )
            return

        # Test metadata extraction
        for video_path in test_videos:
            print(f"\\n  📊 Analyzing {Path(video_path).name}:")
            metadata = get_image_metadata(video_path)

            # Display key metadata
            important_keys = [
                "file_type",
                "size",
                "duration",
                "width",
                "height",
                "resolution_category",
                "video_codec",
                "audio_codec",
                "fps",
                "video_bitrate",
                "container_format",
            ]

            for key in important_keys:
                if key in metadata:
                    value = metadata[key]
                    print(f"    {key}: {value}")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(test_dir)


def test_video_hashing():
    """Test video perceptual hashing."""
    print("\\n🎯 Testing Video Perceptual Hashing...")

    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_video_hash_test_"))

    try:
        # Create test videos
        original_video = test_dir / "original.mp4"
        similar_video = test_dir / "similar.mp4"  # Same content, different encoding
        different_video = test_dir / "different.mp4"

        # Create videos with ffmpeg if available
        videos_created = []

        if create_test_video(str(original_video), 3, "red", "640x480"):
            videos_created.append(str(original_video))

        # Create similar video (same visual content, potentially different encoding)
        if create_test_video(str(similar_video), 3, "red", "640x480"):
            videos_created.append(str(similar_video))

        # Create different video
        if create_test_video(str(different_video), 3, "blue", "640x480"):
            videos_created.append(str(different_video))

        if len(videos_created) < 2:
            print("  ❌ Insufficient test videos created. Skipping hash tests.")
            return

        # Test hash computation
        algorithms = [HashAlgorithm.DHASH, HashAlgorithm.PHASH]

        for algorithm in algorithms:
            print(f"\\n  🔍 Testing {algorithm.value} for videos:")

            video_hashes = []
            for video_path in videos_created:
                hash_result = compute_video_hash(video_path, algorithm)
                video_hashes.append(hash_result)

                status = "✅" if not hash_result.error else "❌"
                error_info = (
                    f" (Error: {hash_result.error})" if hash_result.error else ""
                )
                print(
                    f"    {status} {Path(video_path).name}: {hash_result.hash_value[:16]}...{error_info}"
                )

            # Test similarity if we have multiple hashes
            if len(video_hashes) >= 2:
                for i in range(len(video_hashes)):
                    for j in range(i + 1, len(video_hashes)):
                        hash1, hash2 = video_hashes[i], video_hashes[j]

                        if not hash1.error and not hash2.error:
                            similarity = compute_video_similarity(
                                hash1.file_path, hash2.file_path, algorithm
                            )
                            name1 = Path(hash1.file_path).name
                            name2 = Path(hash2.file_path).name
                            print(f"      {name1} vs {name2}: {similarity:.3f}")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(test_dir)


def test_mixed_duplicate_detection():
    """Test duplicate detection with mixed image and video files."""
    print("\\n🔎 Testing Mixed Media Duplicate Detection...")

    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_mixed_test_"))
    files_created = []

    try:
        # Create test images
        from PIL import Image

        # Create test images
        image1 = test_dir / "image1.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(image1)
        files_created.append(str(image1))

        # Create similar image
        image2 = test_dir / "image2.jpg"
        img.save(image2)  # Identical image
        files_created.append(str(image2))

        # Create videos if possible
        video1 = test_dir / "video1.mp4"
        if create_test_video(str(video1), 2, "red", "320x240"):
            files_created.append(str(video1))

            # Create similar video
            video2 = test_dir / "video2.mp4"
            if create_test_video(str(video2), 2, "red", "320x240"):
                files_created.append(str(video2))

        if len(files_created) < 2:
            print("  ❌ Not enough test files created. Skipping mixed detection test.")
            return

        print(f"  📁 Created {len(files_created)} test files")

        # Test duplicate detection with mixed file types
        dupes = find_duplicates(
            dirs=[str(test_dir)],
            types=["jpg", "mp4"],
            exclude_dirs=[],
            similarity_threshold=0.1,
            algorithm=HashAlgorithm.DHASH,
            max_workers=2,
        )

        print(f"  🔍 Found {len(dupes)} duplicate groups:")
        for i, group in enumerate(dupes):
            files = [Path(f).name for f in group]
            file_types = [get_file_type(f).value for f in group]
            print(f"    Group {i + 1}: {files} (types: {file_types})")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(test_dir)


def main():
    """Run video-specific tests."""
    print("🎬 PhotoChomper Video Support Tests")
    print("=" * 40)

    try:
        test_video_metadata()
        test_video_hashing()
        test_mixed_duplicate_detection()

        print("\\n✅ Video tests completed!")

    except Exception as e:
        print(f"\\n❌ Video test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
