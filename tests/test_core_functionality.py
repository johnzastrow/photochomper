#!/usr/bin/env python3
"""
Core functionality tests that don't require optional dependencies.
Tests basic progress tracking and chunking without pandas, rich, etc.
"""

import unittest
import tempfile
import os
import time
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Test core scanner functionality
from src.scanner import (
    ProgressStats,
    get_optimal_chunk_size,
    get_chunk_size_recommendations,
    scan_files_chunked,
)


class TestCoreProgressStats(unittest.TestCase):
    """Test core ProgressStats functionality."""

    def test_progress_stats_basic(self):
        """Test basic ProgressStats functionality."""
        start_time = time.time() - 10.0  # Started 10 seconds ago
        phase_start = time.time() - 5.0  # Phase started 5 seconds ago

        stats = ProgressStats(
            phase="Test Phase",
            current_step=3,
            total_steps=10,
            files_processed=150,
            total_files=500,
            start_time=start_time,
            phase_start_time=phase_start,
            estimated_completion_time=30.0,
        )

        # Test properties
        self.assertEqual(stats.phase, "Test Phase")
        self.assertEqual(stats.progress_percent, 30.0)  # 3/10 * 100
        self.assertEqual(stats.files_percent, 30.0)  # 150/500 * 100
        self.assertGreater(stats.elapsed_time, 0)
        self.assertGreater(stats.phase_elapsed_time, 0)


class TestCoreChunking(unittest.TestCase):
    """Test core chunking functionality."""

    def test_chunk_size_calculation(self):
        """Test chunk size calculation logic."""
        # Test basic automatic sizing
        chunk_size = get_optimal_chunk_size(10000, 4000)
        self.assertGreater(chunk_size, 0)
        self.assertLessEqual(chunk_size, 10000)

        # Test user override
        user_size = 1500
        result = get_optimal_chunk_size(10000, 4000, user_size)
        self.assertEqual(result, user_size)

        # Test disabled chunking
        result = get_optimal_chunk_size(10000, 4000, 0)
        self.assertEqual(result, 10000)

    def test_chunk_recommendations(self):
        """Test chunk size recommendations."""
        recommendations = get_chunk_size_recommendations(50000, 6000)

        # Should have three types
        self.assertIn("conservative", recommendations)
        self.assertIn("balanced", recommendations)
        self.assertIn("performance", recommendations)

        # Each should have required fields
        for name, rec in recommendations.items():
            self.assertIn("chunk_size", rec)
            self.assertIn("estimated_chunks", rec)
            self.assertIn("memory_usage_mb", rec)
            self.assertIn("description", rec)

            self.assertGreater(rec["chunk_size"], 0)
            self.assertGreaterEqual(rec["estimated_chunks"], 1)


class TestCoreFileScanning(unittest.TestCase):
    """Test file scanning without dependencies."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test files
        for i in range(15):
            file_path = os.path.join(self.temp_dir, f"test_{i:03d}.jpg")
            with open(file_path, "w") as f:
                f.write(f"test content {i}")

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chunked_scanning(self):
        """Test basic chunked file scanning."""
        chunk_size = 5
        chunks = list(scan_files_chunked([self.temp_dir], ["jpg"], [], chunk_size))

        # Should have correct number of chunks
        expected_chunks = (15 + chunk_size - 1) // chunk_size  # Ceiling division
        self.assertEqual(len(chunks), expected_chunks)

        # All chunks except last should have chunk_size files
        for chunk in chunks[:-1]:
            self.assertEqual(len(chunk), chunk_size)

        # Total files should match
        total_files = sum(len(chunk) for chunk in chunks)
        self.assertEqual(total_files, 15)


class TestTimeFormatting(unittest.TestCase):
    """Test time formatting logic without dependencies."""

    def test_format_time_logic(self):
        """Test time formatting calculations."""
        # Test seconds
        self.assertEqual(self._format_time_simple(45.5), "45.5s")

        # Test minutes
        self.assertEqual(self._format_time_simple(90), "1m 30s")
        self.assertEqual(self._format_time_simple(125.3), "2m 5s")

        # Test hours
        self.assertEqual(self._format_time_simple(3660), "1h 1m")
        self.assertEqual(self._format_time_simple(7320), "2h 2m")

    def _format_time_simple(self, seconds):
        """Simple time formatting implementation for testing."""
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


class TestMemoryOptimization(unittest.TestCase):
    """Test memory optimization scenarios."""

    def test_memory_tiers(self):
        """Test different memory tier calculations."""
        scenarios = [
            (50000, 16000, "high-memory"),
            (50000, 4000, "medium-memory"),
            (50000, 2000, "low-memory"),
        ]

        results = []
        for total_files, memory_mb, tier in scenarios:
            chunk_size = get_optimal_chunk_size(total_files, memory_mb)
            estimated_chunks = (total_files + chunk_size - 1) // chunk_size
            results.append((tier, memory_mb, chunk_size, estimated_chunks))

            # Basic validation
            self.assertGreater(chunk_size, 0)
            self.assertLessEqual(chunk_size, total_files)
            self.assertGreaterEqual(estimated_chunks, 1)

        print("\n=== Memory Tier Test Results ===")
        for tier, memory, chunk_size, chunks in results:
            print(
                f"{tier:15s}: {memory:5d}MB → {chunk_size:5d} files/chunk, {chunks:3d} chunks"
            )

    def test_extreme_scenarios(self):
        """Test extreme memory and file count scenarios."""
        extreme_cases = [
            (1000000, 32000, "massive-collection-high-ram"),
            (1000000, 2000, "massive-collection-low-ram"),
            (100, 8000, "tiny-collection-high-ram"),
            (100, 1000, "tiny-collection-low-ram"),
        ]

        print("\n=== Extreme Scenario Test Results ===")
        for total_files, memory_mb, description in extreme_cases:
            chunk_size = get_optimal_chunk_size(total_files, memory_mb)
            estimated_chunks = (total_files + chunk_size - 1) // chunk_size

            print(
                f"{description:30s}: {total_files:7d} files, {memory_mb:5d}MB → {chunk_size:5d}/chunk, {estimated_chunks:4d} chunks"
            )

            # Validation
            self.assertGreater(chunk_size, 0, f"Invalid chunk size for {description}")
            self.assertLessEqual(
                chunk_size, total_files, f"Chunk size exceeds files for {description}"
            )


class TestProgressCalculations(unittest.TestCase):
    """Test progress calculation logic."""

    def test_percentage_calculations(self):
        """Test percentage calculation edge cases."""
        test_cases = [
            (0, 100, 0.0),
            (50, 100, 50.0),
            (100, 100, 100.0),
            (0, 0, 0.0),  # Edge case: no files
        ]

        for processed, total, expected in test_cases:
            if total == 0:
                percent = 0.0
            else:
                percent = (processed / total) * 100

            self.assertAlmostEqual(percent, expected, places=1)

    def test_time_estimations(self):
        """Test time estimation logic."""
        start_time = time.time() - 60  # Started 1 minute ago

        # Simulate progress
        files_processed = 250
        total_files = 1000
        elapsed_time = 60.0  # 1 minute elapsed

        # Calculate ETA
        if files_processed > 0:
            estimated_total_time = (elapsed_time / files_processed) * total_files
            estimated_remaining = estimated_total_time - elapsed_time
        else:
            estimated_remaining = 0.0

        # Should estimate 3 more minutes (4 minutes total - 1 minute elapsed)
        expected_eta = 180.0  # 3 minutes in seconds
        self.assertAlmostEqual(estimated_remaining, expected_eta, delta=1.0)


if __name__ == "__main__":
    # Run tests with verbose output
    print("=== PhotoChomper Core Functionality Tests ===")
    print("Testing enhanced features without optional dependencies")
    print()

    unittest.main(verbosity=2)
