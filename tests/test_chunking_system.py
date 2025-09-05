#!/usr/bin/env python3
"""
Test suite for enhanced chunking system in PhotoChomper v3.0+.
Tests memory optimization, chunk size calculations, and adaptive processing.
"""

import unittest
import tempfile
import os
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scanner import (
    get_optimal_chunk_size,
    get_chunk_size_recommendations,
    MemoryStats,
    scan_files_chunked,
)


class TestChunkSizeCalculation(unittest.TestCase):
    """Test optimal chunk size calculation logic."""

    def test_automatic_chunk_sizing(self):
        """Test automatic chunk size calculation based on memory."""
        test_cases = [
            # (total_files, available_memory_mb, expected_range_min, expected_range_max)
            (1000, 8000, 1000, 1000),  # Small collection, high RAM - no chunking
            (10000, 8000, 1000, 10000),  # Medium collection, high RAM
            (100000, 8000, 1500, 10000),  # Large collection, high RAM
            (50000, 2000, 500, 2000),  # Medium collection, low RAM
            (200000, 1000, 100, 1000),  # Large collection, very low RAM
        ]

        for total_files, memory_mb, min_expected, max_expected in test_cases:
            chunk_size = get_optimal_chunk_size(total_files, memory_mb)

            self.assertGreaterEqual(
                chunk_size,
                min_expected,
                f"Chunk size {chunk_size} too small for {total_files} files, {memory_mb}MB RAM",
            )
            self.assertLessEqual(
                chunk_size,
                max_expected,
                f"Chunk size {chunk_size} too large for {total_files} files, {memory_mb}MB RAM",
            )
            self.assertLessEqual(
                chunk_size, total_files, "Chunk size should not exceed total files"
            )

    def test_user_specified_chunk_size(self):
        """Test user-specified chunk sizes override automatic calculation."""
        total_files = 10000
        memory_mb = 4000

        # Test custom chunk size
        custom_size = 1500
        result = get_optimal_chunk_size(total_files, memory_mb, custom_size)
        self.assertEqual(result, custom_size, "Should use user-specified chunk size")

        # Test disabled chunking (0)
        result = get_optimal_chunk_size(total_files, memory_mb, 0)
        self.assertEqual(
            result, total_files, "Should disable chunking when user specifies 0"
        )

        # Test chunk size larger than total files
        large_size = 15000
        result = get_optimal_chunk_size(total_files, memory_mb, large_size)
        self.assertEqual(result, total_files, "Should not exceed total files")

    def test_memory_tier_logic(self):
        """Test that different RAM amounts result in appropriate memory factors."""
        total_files = 50000

        memory_scenarios = [
            (16000, "high-memory"),  # 16GB
            (8000, "high-memory"),  # 8GB
            (4000, "medium-memory"),  # 4GB
            (2000, "low-memory"),  # 2GB
            (1000, "very-low-memory"),  # 1GB
        ]

        chunk_sizes = []
        for memory_mb, description in memory_scenarios:
            chunk_size = get_optimal_chunk_size(total_files, memory_mb)
            chunk_sizes.append((memory_mb, chunk_size, description))

        # Higher memory should generally allow larger chunk sizes
        # (though there are caps, so it's not always strictly increasing)
        print("\n=== Memory Tier Chunk Size Analysis ===")
        for memory_mb, chunk_size, desc in chunk_sizes:
            estimated_chunks = (total_files + chunk_size - 1) // chunk_size
            print(
                f"{desc:15s}: {memory_mb:5d}MB RAM → {chunk_size:4d} files/chunk, {estimated_chunks:3d} chunks"
            )

        # Verify that very low memory uses smaller chunks than high memory
        very_low_memory_chunks = chunk_sizes[-1][1]  # Last one (lowest memory)
        high_memory_chunks = chunk_sizes[0][1]  # First one (highest memory)

        self.assertLessEqual(
            very_low_memory_chunks,
            high_memory_chunks,
            "Very low memory should use smaller or equal chunk sizes",
        )


class TestChunkRecommendations(unittest.TestCase):
    """Test chunk size recommendation system."""

    def test_recommendation_structure(self):
        """Test that recommendations have proper structure and values."""
        total_files = 100000
        available_memory = 6000

        recommendations = get_chunk_size_recommendations(total_files, available_memory)

        # Should have three recommendation types
        expected_types = ["conservative", "balanced", "performance"]
        for rec_type in expected_types:
            self.assertIn(rec_type, recommendations)

            rec = recommendations[rec_type]

            # Check required fields exist
            required_fields = [
                "chunk_size",
                "estimated_chunks",
                "memory_usage_mb",
                "description",
            ]
            for field in required_fields:
                self.assertIn(
                    field, rec, f"Missing field {field} in {rec_type} recommendation"
                )

            # Check value ranges
            self.assertGreater(rec["chunk_size"], 0)
            self.assertLessEqual(rec["chunk_size"], total_files)
            self.assertGreaterEqual(rec["estimated_chunks"], 1)
            self.assertGreater(rec["memory_usage_mb"], 0)
            self.assertLessEqual(rec["memory_usage_mb"], available_memory)
            self.assertIsInstance(rec["description"], str)
            self.assertGreater(len(rec["description"]), 10)

    def test_recommendation_ordering(self):
        """Test that recommendations are ordered by memory usage."""
        total_files = 75000
        available_memory = 8000

        recommendations = get_chunk_size_recommendations(total_files, available_memory)

        conservative_mem = recommendations["conservative"]["memory_usage_mb"]
        balanced_mem = recommendations["balanced"]["memory_usage_mb"]
        performance_mem = recommendations["performance"]["memory_usage_mb"]

        # Memory usage should increase: conservative < balanced < performance
        self.assertLess(
            conservative_mem,
            balanced_mem,
            "Conservative should use less memory than balanced",
        )
        self.assertLess(
            balanced_mem,
            performance_mem,
            "Balanced should use less memory than performance",
        )

        # Chunk sizes should generally increase with memory (though caps may apply)
        conservative_chunk = recommendations["conservative"]["chunk_size"]
        performance_chunk = recommendations["performance"]["chunk_size"]
        self.assertLessEqual(
            conservative_chunk,
            performance_chunk,
            "Performance mode should use larger or equal chunk sizes",
        )

    def test_edge_case_recommendations(self):
        """Test recommendations for edge cases."""
        edge_cases = [
            (100, 1000),  # Very small collection
            (1000000, 2000),  # Massive collection, low RAM
            (50000, 32000),  # Medium collection, huge RAM
        ]

        for total_files, available_memory in edge_cases:
            recommendations = get_chunk_size_recommendations(
                total_files, available_memory
            )

            # All recommendations should be valid
            for rec_type, rec in recommendations.items():
                self.assertGreater(
                    rec["chunk_size"],
                    0,
                    f"Invalid chunk size for {rec_type} with {total_files} files, {available_memory}MB",
                )
                self.assertLessEqual(
                    rec["chunk_size"],
                    total_files,
                    f"Chunk size exceeds total files for {rec_type}",
                )

                # Estimated chunks should make sense
                expected_chunks = (total_files + rec["chunk_size"] - 1) // rec[
                    "chunk_size"
                ]
                self.assertEqual(
                    rec["estimated_chunks"],
                    expected_chunks,
                    f"Incorrect chunk count calculation for {rec_type}",
                )


class TestChunkedFileScanning(unittest.TestCase):
    """Test the chunked file scanning functionality."""

    def setUp(self):
        """Set up test environment with sample files."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []

        # Create test files with different extensions
        file_types = ["jpg", "png", "gif", "bmp", "tiff"]
        for i in range(25):  # Create 25 test files
            file_type = file_types[i % len(file_types)]
            file_path = os.path.join(self.temp_dir, f"test_file_{i:03d}.{file_type}")
            with open(file_path, "w") as f:
                f.write(f"test content {i}")
            self.test_files.append(file_path)

        # Create some files to exclude
        exclude_dir = os.path.join(self.temp_dir, "excluded")
        os.makedirs(exclude_dir)
        for i in range(5):
            file_path = os.path.join(exclude_dir, f"excluded_{i}.jpg")
            with open(file_path, "w") as f:
                f.write(f"excluded content {i}")

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chunked_scanning_basic(self):
        """Test basic chunked file scanning functionality."""
        chunk_size = 10
        chunks = list(
            scan_files_chunked(
                [self.temp_dir],
                ["jpg", "png", "gif", "bmp", "tiff"],
                ["excluded"],
                chunk_size,
            )
        )

        # Should have multiple chunks
        expected_chunks = (len(self.test_files) + chunk_size - 1) // chunk_size
        self.assertEqual(
            len(chunks), expected_chunks, f"Should have {expected_chunks} chunks"
        )

        # Each chunk (except possibly the last) should have chunk_size files
        for i, chunk in enumerate(chunks[:-1]):  # All but last chunk
            self.assertEqual(
                len(chunk), chunk_size, f"Chunk {i} should have {chunk_size} files"
            )

        # Last chunk should have remaining files
        last_chunk_expected = len(self.test_files) % chunk_size
        if last_chunk_expected == 0:
            last_chunk_expected = chunk_size
        self.assertEqual(
            len(chunks[-1]), last_chunk_expected, "Last chunk should have correct size"
        )

        # All files should be accounted for
        all_files_from_chunks = []
        for chunk in chunks:
            all_files_from_chunks.extend(chunk)

        self.assertEqual(
            len(all_files_from_chunks),
            len(self.test_files),
            "All files should be included in chunks",
        )

        # No excluded files should be present
        excluded_files = [f for f in all_files_from_chunks if "excluded" in f]
        self.assertEqual(len(excluded_files), 0, "Should not include excluded files")

    def test_chunked_scanning_file_types(self):
        """Test chunked scanning with file type filtering."""
        # Only scan for JPG files
        chunks = list(scan_files_chunked([self.temp_dir], ["jpg"], ["excluded"], 5))

        all_files = []
        for chunk in chunks:
            all_files.extend(chunk)

        # All returned files should be JPG
        for file_path in all_files:
            self.assertTrue(
                file_path.endswith(".jpg"), f"File {file_path} should be JPG"
            )

        # Should have correct number of JPG files
        expected_jpg_count = len([f for f in self.test_files if f.endswith(".jpg")])
        self.assertEqual(
            len(all_files),
            expected_jpg_count,
            "Should have correct number of JPG files",
        )

    def test_single_large_chunk(self):
        """Test scanning with chunk size larger than file count."""
        large_chunk_size = 1000  # Much larger than our 25 files

        chunks = list(
            scan_files_chunked(
                [self.temp_dir],
                ["jpg", "png", "gif", "bmp", "tiff"],
                ["excluded"],
                large_chunk_size,
            )
        )

        # Should have only one chunk
        self.assertEqual(len(chunks), 1, "Should have only one chunk")
        self.assertEqual(
            len(chunks[0]),
            len(self.test_files),
            "Single chunk should contain all files",
        )


class TestMemoryOptimizationIntegration(unittest.TestCase):
    """Integration tests for memory optimization features."""

    @patch("src.scanner.MemoryStats.current")
    def test_memory_stats_integration(self, mock_memory):
        """Test integration with MemoryStats for chunk size calculation."""
        # Mock different memory scenarios
        memory_scenarios = [
            (MemoryStats(8000, 2000, 25.0), "Low usage, high RAM"),
            (MemoryStats(4000, 3200, 80.0), "High usage, medium RAM"),
            (MemoryStats(2000, 1600, 80.0), "High usage, low RAM"),
        ]

        total_files = 100000

        for mock_stats, description in memory_scenarios:
            mock_memory.return_value = mock_stats

            chunk_size = get_optimal_chunk_size(total_files)

            # Should return reasonable chunk size
            self.assertGreater(chunk_size, 0, f"Invalid chunk size for {description}")
            self.assertLessEqual(
                chunk_size, total_files, f"Chunk size too large for {description}"
            )

            print(f"\n{description}:")
            print(
                f"  Memory: {mock_stats.used_mb:.0f}MB used / {mock_stats.available_mb:.0f}MB available ({mock_stats.percent_used:.1f}%)"
            )
            print(f"  Chunk size: {chunk_size:,} files")
            print(f"  Estimated chunks: {(total_files + chunk_size - 1) // chunk_size}")

    def test_performance_comparison(self):
        """Test and demonstrate performance characteristics of different chunk sizes."""
        total_files = 50000
        available_memory = 6000

        recommendations = get_chunk_size_recommendations(total_files, available_memory)

        print("\n=== Chunk Size Performance Analysis ===")
        print(f"Collection: {total_files:,} files")
        print(f"Available RAM: {available_memory:,} MB")
        print()

        for strategy, rec in recommendations.items():
            memory_percent = (rec["memory_usage_mb"] / available_memory) * 100
            print(
                f"{strategy.title():12s}: {rec['chunk_size']:5,} files/chunk | "
                f"{rec['estimated_chunks']:3d} chunks | "
                f"{rec['memory_usage_mb']:6.1f}MB ({memory_percent:4.1f}%) | "
                f"{rec['description']}"
            )

        # Demonstrate trade-offs
        conservative = recommendations["conservative"]
        performance = recommendations["performance"]

        memory_ratio = performance["memory_usage_mb"] / conservative["memory_usage_mb"]
        chunk_ratio = performance["chunk_size"] / conservative["chunk_size"]

        print("\nPerformance vs Conservative:")
        print(f"  Memory usage: {memory_ratio:.1f}x higher")
        print(f"  Chunk size: {chunk_ratio:.1f}x larger")
        print(
            f"  Expected speed improvement: ~{chunk_ratio:.1f}x (fewer I/O operations)"
        )


class TestRealWorldScenarios(unittest.TestCase):
    """Test chunking system with realistic photo collection scenarios."""

    def test_wedding_photography_scenario(self):
        """Test chunking for a large wedding photography collection."""
        # Scenario: 150,000 wedding photos, 8GB laptop
        total_files = 150000
        available_memory = 8000

        chunk_size = get_optimal_chunk_size(total_files, available_memory)
        estimated_chunks = (total_files + chunk_size - 1) // chunk_size

        print("\n=== Wedding Photography Scenario ===")
        print(f"Collection: {total_files:,} photos")
        print("System: 8GB laptop")
        print(f"Optimal chunk size: {chunk_size:,} files")
        print(f"Total chunks: {estimated_chunks}")
        print(
            f"Memory per chunk: ~{(available_memory * 0.30) / estimated_chunks:.1f}MB"
        )

        # Verify reasonable values
        self.assertLessEqual(
            chunk_size, 3000, "Chunk size should be manageable for 8GB system"
        )
        self.assertGreaterEqual(chunk_size, 1000, "Chunk size should be efficient")
        self.assertLessEqual(estimated_chunks, 200, "Should not need too many chunks")

    def test_family_archive_scenario(self):
        """Test chunking for a family photo archive."""
        # Scenario: 25,000 family photos, 4GB desktop
        total_files = 25000
        available_memory = 4000

        chunk_size = get_optimal_chunk_size(total_files, available_memory)
        estimated_chunks = (total_files + chunk_size - 1) // chunk_size

        print("\n=== Family Archive Scenario ===")
        print(f"Collection: {total_files:,} photos")
        print("System: 4GB desktop")
        print(f"Optimal chunk size: {chunk_size:,} files")
        print(f"Total chunks: {estimated_chunks}")

        # For smaller collections, might process in single chunk
        if chunk_size >= total_files:
            print("Collection fits in single chunk - no chunking needed!")

        # Verify appropriate for medium system
        self.assertLessEqual(chunk_size, 5000, "Should be appropriate for 4GB system")
        self.assertGreaterEqual(estimated_chunks, 1, "Should have at least one chunk")

    def test_professional_studio_scenario(self):
        """Test chunking for a professional photography studio."""
        # Scenario: 500,000 commercial photos, 32GB workstation
        total_files = 500000
        available_memory = 32000

        chunk_size = get_optimal_chunk_size(total_files, available_memory)
        estimated_chunks = (total_files + chunk_size - 1) // chunk_size

        print("\n=== Professional Studio Scenario ===")
        print(f"Collection: {total_files:,} photos")
        print("System: 32GB workstation")
        print(f"Optimal chunk size: {chunk_size:,} files")
        print(f"Total chunks: {estimated_chunks}")
        print("Estimated processing time: ~45 minutes")

        # High-end system should handle larger chunks
        self.assertGreaterEqual(
            chunk_size, 2000, "High-end system should use larger chunks"
        )
        self.assertLessEqual(
            estimated_chunks, 300, "Should be efficient even for huge collections"
        )


if __name__ == "__main__":
    # Run tests with detailed output
    unittest.main(verbosity=2)
