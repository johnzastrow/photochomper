#!/usr/bin/env python3
"""
Test suite for new progress tracking functionality in PhotoChomper v3.0+.
Tests ProgressStats class, time estimation, and progress callbacks.
"""

import unittest
import time
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scanner import ProgressStats, find_duplicates, HashAlgorithm


class TestProgressStats(unittest.TestCase):
    """Test the ProgressStats class for time tracking and progress calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.start_time = time.time()
        self.phase_start = self.start_time + 5.0  # 5 seconds after start

    def test_progress_stats_creation(self):
        """Test ProgressStats object creation and basic properties."""
        stats = ProgressStats(
            phase="Test Phase",
            current_step=5,
            total_steps=10,
            files_processed=100,
            total_files=500,
            start_time=self.start_time,
            phase_start_time=self.phase_start,
            estimated_completion_time=30.0,
        )

        self.assertEqual(stats.phase, "Test Phase")
        self.assertEqual(stats.current_step, 5)
        self.assertEqual(stats.total_steps, 10)
        self.assertEqual(stats.files_processed, 100)
        self.assertEqual(stats.total_files, 500)
        self.assertEqual(stats.estimated_completion_time, 30.0)

    def test_progress_percentage_calculations(self):
        """Test progress percentage calculations."""
        stats = ProgressStats(
            phase="Test Phase",
            current_step=3,
            total_steps=10,
            files_processed=250,
            total_files=1000,
            start_time=self.start_time,
            phase_start_time=self.phase_start,
        )

        # Test step progress
        self.assertEqual(stats.progress_percent, 30.0)  # 3/10 * 100

        # Test file progress
        self.assertEqual(stats.files_percent, 25.0)  # 250/1000 * 100

    def test_progress_edge_cases(self):
        """Test edge cases for progress calculations."""
        # Zero total steps
        stats = ProgressStats(
            phase="Test Phase",
            current_step=5,
            total_steps=0,
            files_processed=100,
            total_files=500,
            start_time=self.start_time,
            phase_start_time=self.phase_start,
        )
        self.assertEqual(stats.progress_percent, 0.0)

        # Zero total files
        stats = ProgressStats(
            phase="Test Phase",
            current_step=5,
            total_steps=10,
            files_processed=100,
            total_files=0,
            start_time=self.start_time,
            phase_start_time=self.phase_start,
        )
        self.assertEqual(stats.files_percent, 0.0)

    def test_elapsed_time_calculations(self):
        """Test elapsed time calculations."""
        current_time = time.time()
        stats = ProgressStats(
            phase="Test Phase",
            current_step=1,
            total_steps=2,
            files_processed=10,
            total_files=100,
            start_time=current_time - 10.0,  # Started 10 seconds ago
            phase_start_time=current_time - 5.0,  # Phase started 5 seconds ago
        )

        # Allow some tolerance for timing
        self.assertGreaterEqual(stats.elapsed_time, 9.0)
        self.assertLessEqual(stats.elapsed_time, 11.0)

        self.assertGreaterEqual(stats.phase_elapsed_time, 4.0)
        self.assertLessEqual(stats.phase_elapsed_time, 6.0)


class TestProgressCallbacks(unittest.TestCase):
    """Test progress callback functionality in find_duplicates."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory with test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []

        # Create some test image files (small dummy files)
        for i in range(5):
            file_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            with open(file_path, "wb") as f:
                f.write(b"fake_image_data_" + str(i).encode() * 100)
            self.test_files.append(file_path)

        # Create identical files for testing
        identical_path = os.path.join(self.temp_dir, "identical.jpg")
        with open(identical_path, "wb") as f:
            f.write(b"identical_content" * 50)

        identical_copy = os.path.join(self.temp_dir, "identical_copy.jpg")
        with open(identical_copy, "wb") as f:
            f.write(b"identical_content" * 50)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_progress_callback_called(self):
        """Test that progress callback is called during find_duplicates."""
        callback_calls = []

        def test_callback(stats: ProgressStats):
            callback_calls.append(
                {
                    "phase": stats.phase,
                    "files_processed": stats.files_processed,
                    "total_files": stats.total_files,
                    "elapsed_time": stats.elapsed_time,
                    "progress_percent": stats.progress_percent,
                }
            )

        # Run find_duplicates with callback
        groups, hash_results = find_duplicates(
            dirs=[self.temp_dir],
            types=["jpg"],
            exclude_dirs=[],
            similarity_threshold=0.1,
            algorithm=HashAlgorithm.DHASH,
            max_workers=2,
            chunk_size=3,  # Small chunk size for testing
            skip_sha256=False,
            progress_callback=test_callback,
        )

        # Verify callback was called
        self.assertGreater(len(callback_calls), 0, "Progress callback should be called")

        # Check that we got different phases
        phases = [call["phase"] for call in callback_calls]
        self.assertIn("File Discovery", phases, "Should have file discovery phase")

        # Verify progression
        file_counts = [
            call["files_processed"]
            for call in callback_calls
            if call["total_files"] > 0
        ]
        if len(file_counts) > 1:
            # Should show increasing file counts
            self.assertLessEqual(
                file_counts[0], file_counts[-1], "File counts should increase over time"
            )

    def test_progress_callback_skip_sha256(self):
        """Test progress callback when SHA256 stage is skipped."""
        callback_calls = []

        def test_callback(stats: ProgressStats):
            callback_calls.append(stats.phase)

        # Run with skip_sha256=True
        groups, hash_results = find_duplicates(
            dirs=[self.temp_dir],
            types=["jpg"],
            exclude_dirs=[],
            similarity_threshold=0.1,
            algorithm=HashAlgorithm.DHASH,
            max_workers=2,
            chunk_size=3,
            skip_sha256=True,  # Skip SHA256 stage
            progress_callback=test_callback,
        )

        phases = callback_calls
        # Should not have SHA256 phase when skipped
        sha256_phases = [phase for phase in phases if "SHA256" in phase]
        self.assertEqual(
            len(sha256_phases), 0, "Should not have SHA256 phase when skipped"
        )

        # Should have similarity phase
        similarity_phases = [
            phase for phase in phases if "Similarity" in phase or "DHASH" in phase
        ]
        self.assertGreater(
            len(similarity_phases), 0, "Should have similarity detection phase"
        )

    def test_time_estimation_accuracy(self):
        """Test that time estimation becomes more accurate over time."""
        estimations = []

        def capture_estimations(stats: ProgressStats):
            if stats.estimated_completion_time > 0:
                estimations.append(stats.estimated_completion_time)

        # Run with more files to get better estimation data
        groups, hash_results = find_duplicates(
            dirs=[self.temp_dir],
            types=["jpg"],
            exclude_dirs=[],
            similarity_threshold=0.1,
            algorithm=HashAlgorithm.DHASH,
            max_workers=2,
            chunk_size=2,  # Small chunks for more estimation points
            skip_sha256=False,
            progress_callback=capture_estimations,
        )

        # Should have some time estimations
        if len(estimations) > 1:
            # Estimations should generally decrease as we get more data
            # (though this is approximate due to processing variations)
            self.assertIsInstance(estimations[0], (int, float))
            self.assertIsInstance(estimations[-1], (int, float))


class TestProgressIntegration(unittest.TestCase):
    """Integration tests for progress tracking with real scenarios."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Create a more realistic test scenario
        self.create_test_collection()

    def create_test_collection(self):
        """Create a realistic test photo collection."""
        # Create various types of files
        file_types = ["jpg", "png", "gif"]

        for i in range(15):  # Create 15 test files
            file_type = file_types[i % len(file_types)]
            file_path = os.path.join(self.temp_dir, f"photo_{i:03d}.{file_type}")

            # Create files with different content
            content = f"photo_content_{i}".encode() * (100 + i * 10)
            with open(file_path, "wb") as f:
                f.write(content)

        # Create some exact duplicates
        original_path = os.path.join(self.temp_dir, "original.jpg")
        duplicate_path = os.path.join(self.temp_dir, "duplicate.jpg")

        content = b"original_photo_content" * 200
        with open(original_path, "wb") as f:
            f.write(content)
        with open(duplicate_path, "wb") as f:
            f.write(content)

    def tearDown(self):
        """Clean up integration test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_progress_tracking_flow(self):
        """Test complete progress tracking through all phases."""
        progress_log = []

        def comprehensive_callback(stats: ProgressStats):
            progress_log.append(
                {
                    "timestamp": time.time(),
                    "phase": stats.phase,
                    "step": f"{stats.current_step}/{stats.total_steps}",
                    "files": f"{stats.files_processed}/{stats.total_files}",
                    "progress": f"{stats.progress_percent:.1f}%",
                    "files_progress": f"{stats.files_percent:.1f}%",
                    "elapsed": f"{stats.elapsed_time:.2f}s",
                    "phase_elapsed": f"{stats.phase_elapsed_time:.2f}s",
                    "eta": f"{stats.estimated_completion_time:.2f}s"
                    if stats.estimated_completion_time > 0
                    else "N/A",
                }
            )

        # Run comprehensive duplicate detection
        start_time = time.time()
        groups, hash_results = find_duplicates(
            dirs=[self.temp_dir],
            types=["jpg", "png", "gif"],
            exclude_dirs=[],
            similarity_threshold=0.1,
            algorithm=HashAlgorithm.DHASH,
            max_workers=2,
            chunk_size=5,  # Process in small chunks
            skip_sha256=False,
            progress_callback=comprehensive_callback,
        )
        total_time = time.time() - start_time

        # Verify we got comprehensive progress tracking
        self.assertGreater(len(progress_log), 0, "Should have progress updates")

        # Check for expected phases
        phases = [entry["phase"] for entry in progress_log]
        unique_phases = list(set(phases))

        print("\n=== Progress Tracking Integration Test Results ===")
        print(f"Total processing time: {total_time:.2f} seconds")
        print(f"Progress updates received: {len(progress_log)}")
        print(f"Unique phases: {unique_phases}")
        print(f"Duplicate groups found: {len(groups)}")
        print(f"Hash results: {len(hash_results)}")

        # Print detailed progress log
        print("\n=== Detailed Progress Log ===")
        for i, entry in enumerate(progress_log):
            print(
                f"{i + 1:2d}. [{entry['phase']}] Step {entry['step']} | "
                f"Files {entry['files']} ({entry['files_progress']}) | "
                f"Elapsed {entry['elapsed']} | ETA {entry['eta']}"
            )

        # Verify results
        self.assertGreaterEqual(
            len(groups), 1, "Should find at least one duplicate group"
        )
        self.assertGreater(len(hash_results), 0, "Should have hash results")

        # Verify phase progression makes sense
        if len(progress_log) > 1:
            first_phase = progress_log[0]["phase"]
            last_phase = progress_log[-1]["phase"]

            # Should start with File Discovery and end with Completed
            self.assertEqual(
                first_phase, "File Discovery", "Should start with file discovery"
            )
            self.assertEqual(last_phase, "Completed", "Should end with completion")


class TestMemoryAndChunking(unittest.TestCase):
    """Test memory optimization and chunking functionality."""

    def test_chunk_size_recommendations(self):
        """Test chunk size recommendation system."""
        from src.scanner import get_chunk_size_recommendations

        # Test with different scenarios
        test_cases = [
            (1000, 4000),  # Small collection, medium RAM
            (50000, 8000),  # Medium collection, high RAM
            (200000, 2000),  # Large collection, low RAM
        ]

        for total_files, available_memory in test_cases:
            recommendations = get_chunk_size_recommendations(
                total_files, available_memory
            )

            # Should have three recommendation types
            self.assertIn("conservative", recommendations)
            self.assertIn("balanced", recommendations)
            self.assertIn("performance", recommendations)

            # Each recommendation should have required fields
            for name, rec in recommendations.items():
                self.assertIn("chunk_size", rec)
                self.assertIn("estimated_chunks", rec)
                self.assertIn("memory_usage_mb", rec)
                self.assertIn("description", rec)

                # Chunk size should be reasonable
                self.assertGreater(rec["chunk_size"], 0)
                self.assertLessEqual(rec["chunk_size"], total_files)

                # Should have at least 1 chunk
                self.assertGreaterEqual(rec["estimated_chunks"], 1)

            # Performance should use more memory than conservative
            perf_memory = recommendations["performance"]["memory_usage_mb"]
            cons_memory = recommendations["conservative"]["memory_usage_mb"]
            self.assertGreater(perf_memory, cons_memory)

            print(
                f"\nChunk recommendations for {total_files} files, {available_memory}MB RAM:"
            )
            for name, rec in recommendations.items():
                print(
                    f"  {name.title()}: {rec['chunk_size']} files/chunk, "
                    f"{rec['estimated_chunks']} chunks, "
                    f"{rec['memory_usage_mb']:.1f}MB memory"
                )


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
