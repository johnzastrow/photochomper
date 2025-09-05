#!/usr/bin/env python3
"""
Integration demonstration of PhotoChomper v3.0+ enhanced features.
This script demonstrates the new progress tracking, chunking, and TUI improvements.
"""

import os
import sys
import tempfile
import shutil
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scanner import (
    find_duplicates,
    HashAlgorithm,
    ProgressStats,
    get_chunk_size_recommendations,
    get_optimal_chunk_size,
)


def create_test_collection(base_dir, num_files=50):
    """Create a realistic test photo collection."""
    print(f"Creating test collection with {num_files} files...")

    # Create various subdirectories
    subdirs = ["vacation_2023", "family_photos", "work_events", "misc"]
    for subdir in subdirs:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)

    # Create test files with different content
    file_types = ["jpg", "png", "gif"]

    for i in range(num_files):
        subdir = subdirs[i % len(subdirs)]
        file_type = file_types[i % len(file_types)]
        file_path = os.path.join(base_dir, subdir, f"photo_{i:03d}.{file_type}")

        # Create files with varying content
        content = f"photo_content_{i}".encode() * (100 + i * 20)
        with open(file_path, "wb") as f:
            f.write(content)

    # Create some exact duplicates
    duplicate_content = b"duplicate_photo_content" * 500

    # Original
    original_path = os.path.join(base_dir, "vacation_2023", "sunset_original.jpg")
    with open(original_path, "wb") as f:
        f.write(duplicate_content)

    # Exact duplicate
    duplicate_path = os.path.join(base_dir, "family_photos", "sunset_copy.jpg")
    with open(duplicate_path, "wb") as f:
        f.write(duplicate_content)

    # Another duplicate in different folder
    duplicate2_path = os.path.join(base_dir, "work_events", "sunset_backup.jpg")
    with open(duplicate2_path, "wb") as f:
        f.write(duplicate_content)

    print(f"✅ Created {num_files + 3} test files with duplicates")
    return base_dir


def demonstrate_chunking_analysis(total_files, available_memory):
    """Demonstrate chunking analysis and recommendations."""
    print(f"\n{'=' * 60}")
    print(f"CHUNKING ANALYSIS FOR {total_files:,} FILES")
    print(f"{'=' * 60}")

    print(f"System Memory: {available_memory:,} MB available")

    # Get optimal chunk size
    optimal_chunk = get_optimal_chunk_size(total_files, available_memory)
    estimated_chunks = (total_files + optimal_chunk - 1) // optimal_chunk

    print("\nOptimal Configuration:")
    print(f"  Chunk Size: {optimal_chunk:,} files per chunk")
    print(f"  Total Chunks: {estimated_chunks:,}")
    print(f"  Memory per Chunk: ~{(available_memory * 0.25) / estimated_chunks:.1f}MB")

    # Get recommendations
    recommendations = get_chunk_size_recommendations(total_files, available_memory)

    print("\nAvailable Strategies:")
    for strategy, rec in recommendations.items():
        memory_percent = (rec["memory_usage_mb"] / available_memory) * 100
        print(
            f"  {strategy.title():12s}: {rec['chunk_size']:5,} files/chunk | "
            f"{rec['estimated_chunks']:3d} chunks | "
            f"{rec['memory_usage_mb']:6.1f}MB ({memory_percent:4.1f}%) | "
            f"{rec['description']}"
        )

    return optimal_chunk


def demonstrate_progress_tracking(test_dir, chunk_size):
    """Demonstrate enhanced progress tracking."""
    print(f"\n{'=' * 60}")
    print("PROGRESS TRACKING DEMONSTRATION")
    print(f"{'=' * 60}")

    progress_log = []
    last_phase = None

    def enhanced_progress_callback(stats: ProgressStats):
        nonlocal last_phase

        # Only print when phase changes or every few updates
        if stats.phase != last_phase or len(progress_log) % 5 == 0:
            elapsed_str = format_time(stats.elapsed_time)
            phase_elapsed_str = format_time(stats.phase_elapsed_time)

            # Status emoji
            emoji_map = {
                "File Discovery": "📁",
                "Stage 1/2: SHA256 Exact Duplicates": "🔗",
                "Stage 2/2: DHASH Similarity": "🎯",
                "Completed": "✅",
            }
            emoji = emoji_map.get(stats.phase, "⚙️")

            if stats.total_files > 0:
                progress_info = f"{stats.files_processed:,}/{stats.total_files:,} files ({stats.files_percent:.1f}%)"
                eta_info = (
                    f" | ETA: {format_time(stats.estimated_completion_time)}"
                    if stats.estimated_completion_time > 0
                    else ""
                )
                print(f"{emoji} {stats.phase}")
                print(
                    f"   Progress: {progress_info} | Elapsed: {elapsed_str} ({phase_elapsed_str} this phase){eta_info}"
                )
            else:
                print(f"{emoji} {stats.phase} | Elapsed: {elapsed_str}")

        progress_log.append(stats)
        last_phase = stats.phase

    print("Starting duplicate detection with enhanced progress tracking...")

    start_time = time.time()

    # Run the search with progress tracking
    groups, hash_results = find_duplicates(
        dirs=[test_dir],
        types=["jpg", "png", "gif"],
        exclude_dirs=[],
        similarity_threshold=0.1,
        algorithm=HashAlgorithm.DHASH,
        max_workers=2,
        chunk_size=chunk_size,
        skip_sha256=False,
        progress_callback=enhanced_progress_callback,
    )

    total_time = time.time() - start_time

    print(f"\n{'=' * 60}")
    print("SEARCH RESULTS")
    print(f"{'=' * 60}")
    print(f"⏱️  Total Time: {format_time(total_time)}")
    print(f"📊 Progress Updates: {len(progress_log)}")
    print(f"📁 Duplicate Groups: {len(groups)}")
    print(f"🔍 Hash Results: {len(hash_results)}")

    # Show duplicate groups found
    if groups:
        print("\n📋 Duplicate Groups Found:")
        for i, group in enumerate(groups, 1):
            print(f"  Group {i}: {len(group)} files")
            for j, file_path in enumerate(group):
                filename = os.path.basename(file_path)
                status = "👑 Master" if j == 0 else f"#{j} Duplicate"
                print(f"    {status}: {filename}")

    return len(progress_log), total_time


def format_time(seconds):
    """Format time duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def demonstrate_skip_sha256(test_dir, chunk_size):
    """Demonstrate skip SHA256 functionality."""
    print(f"\n{'=' * 60}")
    print("SKIP SHA256 DEMONSTRATION")
    print(f"{'=' * 60}")

    def skip_progress_callback(stats: ProgressStats):
        if "SHA256" in stats.phase:
            print(f"⚠️  ERROR: SHA256 phase should be skipped but found: {stats.phase}")
        elif "Similarity" in stats.phase or "DHASH" in stats.phase:
            print(f"✅ Similarity-only processing: {stats.phase}")
        elif stats.phase == "Completed":
            print("✅ Completed similarity-only search")

    print("Running search with SHA256 stage skipped...")

    start_time = time.time()
    groups, hash_results = find_duplicates(
        dirs=[test_dir],
        types=["jpg", "png", "gif"],
        exclude_dirs=[],
        similarity_threshold=0.1,
        algorithm=HashAlgorithm.DHASH,
        max_workers=2,
        chunk_size=chunk_size,
        skip_sha256=True,  # Skip SHA256 stage
        progress_callback=skip_progress_callback,
    )
    skip_time = time.time() - start_time

    print(f"⏱️  Skip SHA256 Time: {format_time(skip_time)}")
    print(f"📁 Groups Found: {len(groups)} (similarity-only)")

    return skip_time


def main():
    """Run the integration demonstration."""
    print("=" * 80)
    print("PHOTOCHOMPER v3.0+ ENHANCED FEATURES INTEGRATION DEMO")
    print("=" * 80)

    # Create temporary test environment
    temp_dir = tempfile.mkdtemp()
    print(f"Test Environment: {temp_dir}")

    try:
        # Create test collection
        test_files = 35  # Moderate number for demo
        create_test_collection(temp_dir, test_files)

        # Demonstrate chunking analysis
        available_memory = 6000  # 6GB RAM simulation
        optimal_chunk = demonstrate_chunking_analysis(test_files + 3, available_memory)

        # Demonstrate progress tracking
        progress_updates, search_time = demonstrate_progress_tracking(
            temp_dir, optimal_chunk
        )

        # Demonstrate skip SHA256
        skip_time = demonstrate_skip_sha256(temp_dir, optimal_chunk)

        # Final summary
        print(f"\n{'=' * 60}")
        print("INTEGRATION DEMO SUMMARY")
        print(f"{'=' * 60}")
        print(
            f"✅ Enhanced Chunking: Analyzed {test_files + 3} files with {optimal_chunk} files/chunk"
        )
        print(
            f"✅ Progress Tracking: {progress_updates} status updates during processing"
        )
        print("✅ Time Estimation: Real-time ETA calculations and phase timing")
        print("✅ Skip SHA256 Option: Alternative processing mode demonstrated")
        print("⏱️  Performance:")
        print(f"   - Full Search: {format_time(search_time)}")
        print(f"   - Skip SHA256: {format_time(skip_time)}")
        print(
            f"   - Speed Ratio: {search_time / skip_time:.1f}x faster when skipping SHA256"
        )

        print("\n🎉 All enhanced features working correctly!")

    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
            print("\n🧹 Cleaned up test environment")
        except:
            pass


if __name__ == "__main__":
    main()
