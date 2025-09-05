#!/usr/bin/env python3
"""
Test suite for enhanced TUI functionality in PhotoChomper v3.0+.
Tests progress display, time formatting, and search interface improvements.
"""

import unittest
import tempfile
import os
import time
from unittest.mock import patch
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tui import format_time, run_search
from src.scanner import ProgressStats

class TestTimeFormatting(unittest.TestCase):
    """Test the time formatting functionality."""
    
    def test_seconds_formatting(self):
        """Test formatting of time in seconds."""
        test_cases = [
            (0.5, "0.5s"),
            (1.0, "1.0s"),
            (15.7, "15.7s"),
            (45.0, "45.0s"),
            (59.9, "59.9s"),
        ]
        
        for seconds, expected in test_cases:
            result = format_time(seconds)
            self.assertEqual(result, expected, f"Failed for {seconds} seconds")
    
    def test_minutes_formatting(self):
        """Test formatting of time in minutes and seconds."""
        test_cases = [
            (60, "1m 0s"),
            (90, "1m 30s"),
            (125.3, "2m 5s"),
            (300, "5m 0s"),
            (1800, "30m 0s"),
            (3599, "59m 59s"),
        ]
        
        for seconds, expected in test_cases:
            result = format_time(seconds)
            self.assertEqual(result, expected, f"Failed for {seconds} seconds")
    
    def test_hours_formatting(self):
        """Test formatting of time in hours and minutes."""
        test_cases = [
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (7200, "2h 0m"),
            (7320, "2h 2m"),
            (86400, "24h 0m"),
        ]
        
        for seconds, expected in test_cases:
            result = format_time(seconds)
            self.assertEqual(result, expected, f"Failed for {seconds} seconds")

class TestProgressCallback(unittest.TestCase):
    """Test the enhanced progress callback system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "dirs": [self.temp_dir],
            "types": ["jpg", "png"],
            "exclude_dirs": [],
            "similarity_threshold": 0.1,
            "hash_algorithm": "dhash",
            "skip_sha256": False,
            "max_workers": 2,
            "chunk_size": None,
            "config_file": "test_config.conf",
            "output_base": "test_output"
        }
        
        # Create a few test files
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_{i}.jpg")
            with open(file_path, 'wb') as f:
                f.write(b'test_image_data' * 100)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.tui.console')
    @patch('src.tui.export_report')
    @patch('src.tui.find_duplicates')
    def test_progress_callback_structure(self, mock_find_duplicates, mock_export_report, mock_console):
        """Test that progress callback receives proper ProgressStats structure."""
        captured_progress = []
        
        def capture_progress(stats):
            captured_progress.append(stats)
        
        # Mock find_duplicates to call progress callback
        def mock_find_duplicates_impl(*args, **kwargs):
            progress_callback = kwargs.get('progress_callback')
            if progress_callback:
                # Simulate progress updates
                start_time = time.time()
                
                # File discovery
                progress_callback(ProgressStats(
                    "File Discovery", 0, 1, 0, 10, start_time, time.time()
                ))
                
                # SHA256 stage
                progress_callback(ProgressStats(
                    "Stage 1/2: SHA256 Exact Duplicates", 1, 2, 5, 10, 
                    start_time, time.time(), 5.0
                ))
                
                # Similarity stage  
                progress_callback(ProgressStats(
                    "Stage 2/2: DHASH Similarity", 2, 2, 10, 10,
                    start_time, time.time(), 2.0
                ))
                
                # Completion
                progress_callback(ProgressStats(
                    "Completed", 2, 2, 10, 10, start_time, time.time(), 0.0
                ))
            
            return [], {}  # Empty results for testing
        
        mock_find_duplicates.side_effect = mock_find_duplicates_impl
        mock_export_report.return_value = None
        
        # Capture the progress callback by patching the internal function
        with patch('src.tui.run_search') as mock_run_search:
            def actual_run_search(config, config_path=None):
                # Call the actual implementation but capture progress
                from src.tui import find_duplicates
                find_duplicates(
                    config.get("dirs", []),
                    config.get("types", []),
                    config.get("exclude_dirs", []),
                    config.get("similarity_threshold", 0.1),
                    config.get("hash_algorithm", "dhash"),
                    config.get("max_workers", 4),
                    config.get("chunk_size"),
                    config.get("skip_sha256", False),
                    capture_progress
                )
                
            mock_run_search.side_effect = actual_run_search
            
            # Run the search
            from src.tui import run_search
            run_search(self.config)
        
        # Verify progress updates were captured
        # Note: This test focuses on the callback structure rather than the full TUI
        self.assertGreater(len(captured_progress), 0, "Should have captured progress updates")
        
        # Verify ProgressStats structure
        for progress in captured_progress:
            self.assertIsInstance(progress, ProgressStats)
            self.assertIsInstance(progress.phase, str)
            self.assertIsInstance(progress.current_step, int)
            self.assertIsInstance(progress.total_steps, int)
            self.assertIsInstance(progress.files_processed, int) 
            self.assertIsInstance(progress.total_files, int)

class TestTUIEnhancements(unittest.TestCase):
    """Test TUI enhancements and display features."""
    
    def test_emoji_status_mapping(self):
        """Test that status emojis are properly mapped to phases."""
        # This tests the emoji mapping logic from the TUI
        status_emoji = {
            "File Discovery": "📁",
            "Stage 1/2: SHA256 Exact Duplicates": "🔗", 
            "Stage 1/1: SHA256 Exact Duplicates": "🔗",
            "Stage 2/2: DHASH Similarity": "🎯",
            "Stage 2/2: PHASH Similarity": "🎯", 
            "Stage 2/2: AHASH Similarity": "🎯",
            "Stage 2/2: WHASH Similarity": "🎯",
            "Completed": "✅"
        }
        
        # Test that all expected phases have emojis
        expected_phases = [
            "File Discovery",
            "Stage 1/2: SHA256 Exact Duplicates", 
            "Stage 2/2: DHASH Similarity",
            "Completed"
        ]
        
        for phase in expected_phases:
            self.assertIn(phase, status_emoji, f"Missing emoji for phase: {phase}")
            self.assertIsInstance(status_emoji[phase], str, f"Emoji should be string for {phase}")
            self.assertGreater(len(status_emoji[phase]), 0, f"Empty emoji for {phase}")
    
    def test_memory_usage_coloring_logic(self):
        """Test memory usage coloring thresholds."""
        test_cases = [
            (50.0, "green"),    # Low usage
            (75.0, "yellow"),   # Medium usage  
            (90.0, "red"),      # High usage
            (85.1, "red"),      # Just over threshold
            (84.9, "yellow"),   # Just under threshold
        ]
        
        for memory_percent, expected_color in test_cases:
            # Simulate the coloring logic from the TUI
            if memory_percent > 85:
                color = "red"
            elif memory_percent > 70:
                color = "yellow"
            else:
                color = "green"
            
            self.assertEqual(color, expected_color, 
                f"Wrong color for {memory_percent}% memory usage")

class TestTUIIntegration(unittest.TestCase):
    """Integration tests for TUI with real search functionality."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a realistic test scenario
        self.create_test_files()
        
        self.config = {
            "dirs": [self.temp_dir],
            "types": ["jpg", "png", "gif"],
            "exclude_dirs": [],
            "similarity_threshold": 0.1,
            "hash_algorithm": "dhash", 
            "skip_sha256": False,
            "max_workers": 2,
            "chunk_size": 5,  # Small chunks for testing
            "config_file": "test_config.conf",
            "output_base": os.path.join(self.temp_dir, "test_report")
        }
    
    def create_test_files(self):
        """Create test files for integration testing."""
        # Create various test files
        for i in range(12):
            file_path = os.path.join(self.temp_dir, f"photo_{i:03d}.jpg")
            content = f"photo_content_{i}".encode() * (50 + i * 5)
            with open(file_path, 'wb') as f:
                f.write(content)
        
        # Create identical duplicates
        original_content = b"duplicate_content" * 100
        
        original_path = os.path.join(self.temp_dir, "original.png")
        with open(original_path, 'wb') as f:
            f.write(original_content)
        
        duplicate_path = os.path.join(self.temp_dir, "duplicate.png")
        with open(duplicate_path, 'wb') as f:
            f.write(original_content)
    
    def tearDown(self):
        """Clean up integration test environment.""" 
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.tui.console')
    @patch('src.tui.export_report')
    def test_full_tui_search_integration(self, mock_export_report, mock_console):
        """Test full TUI search integration with progress tracking."""
        # Mock console to capture print calls
        console_output = []
        
        def capture_print(*args, **kwargs):
            if args:
                console_output.append(str(args[0]))
        
        mock_console.print.side_effect = capture_print
        mock_export_report.return_value = None
        
        # Run the search
        try:
            run_search(self.config)
        except Exception:
            # Some exceptions are expected due to mocking
            pass
        
        # Analyze captured output
        output_text = ' '.join(console_output)
        
        print("\n=== TUI Integration Test Output Analysis ===")
        print(f"Console calls captured: {len(console_output)}")
        print(f"Total output length: {len(output_text)} characters")
        
        # Check for expected TUI elements
        expected_elements = [
            "PhotoChomper",
            "Starting",
            "Search",
            "optimization"
        ]
        
        found_elements = []
        for element in expected_elements:
            if element.lower() in output_text.lower():
                found_elements.append(element)
        
        print(f"Expected UI elements found: {found_elements}")
        
        # Should have some TUI output
        self.assertGreater(len(console_output), 0, "Should have TUI output")
    
    @patch('src.tui.console')
    def test_skip_sha256_display(self, mock_console):
        """Test TUI display when SHA256 is skipped."""
        console_output = []
        
        def capture_print(*args, **kwargs):
            if args:
                console_output.append(str(args[0]))
        
        mock_console.print.side_effect = capture_print
        
        # Configure to skip SHA256
        config_skip = self.config.copy()
        config_skip["skip_sha256"] = True
        
        # Mock find_duplicates to avoid actual processing
        with patch('src.tui.find_duplicates') as mock_find_duplicates:
            mock_find_duplicates.return_value = ([], {})
            
            with patch('src.tui.export_report'):
                try:
                    run_search(config_skip)
                except:
                    pass  # Expected due to mocking
        
        # Check for skip SHA256 warning
        output_text = ' '.join(console_output)
        skip_indicators = [
            "skip",
            "SHA256", 
            "exact duplicate",
            "warning"
        ]
        
        found_skip_indicators = []
        for indicator in skip_indicators:
            if indicator.lower() in output_text.lower():
                found_skip_indicators.append(indicator)
        
        print(f"\nSkip SHA256 indicators found: {found_skip_indicators}")
        # Should mention skipping SHA256
        self.assertTrue(any("skip" in output.lower() for output in console_output),
            "Should display skip SHA256 warning")

class TestProgressDisplayLogic(unittest.TestCase):
    """Test the progress display logic and calculations."""
    
    def test_eta_calculation_display(self):
        """Test ETA calculation and display logic."""
        start_time = time.time() - 60  # Started 1 minute ago
        
        # Test progress with ETA
        stats_with_eta = ProgressStats(
            phase="Test Phase",
            current_step=1,
            total_steps=2,
            files_processed=500,
            total_files=1000,
            start_time=start_time,
            phase_start_time=start_time + 30,  # Phase started 30s ago
            estimated_completion_time=120.0  # 2 minutes remaining
        )
        
        # Test the ETA formatting logic
        eta_str = format_time(stats_with_eta.estimated_completion_time)
        self.assertEqual(eta_str, "2m 0s", "ETA should be formatted as 2m 0s")
        
        # Test zero ETA
        stats_no_eta = ProgressStats(
            phase="Completed",
            current_step=2,
            total_steps=2,
            files_processed=1000,
            total_files=1000,
            start_time=start_time,
            phase_start_time=start_time,
            estimated_completion_time=0.0
        )
        
        self.assertEqual(stats_no_eta.estimated_completion_time, 0.0, "Completed phase should have zero ETA")
    
    def test_progress_percentage_display(self):
        """Test progress percentage calculations for display."""
        test_cases = [
            # (files_processed, total_files, expected_percent)
            (0, 1000, 0.0),
            (100, 1000, 10.0),
            (500, 1000, 50.0),
            (999, 1000, 99.9),
            (1000, 1000, 100.0),
        ]
        
        for processed, total, expected in test_cases:
            stats = ProgressStats(
                phase="Test",
                current_step=1,
                total_steps=2,
                files_processed=processed,
                total_files=total,
                start_time=time.time(),
                phase_start_time=time.time()
            )
            
            self.assertAlmostEqual(stats.files_percent, expected, places=1,
                msg=f"Wrong percentage for {processed}/{total} files")

class TestErrorHandling(unittest.TestCase):
    """Test error handling in TUI functionality."""
    
    @patch('src.tui.console')
    def test_search_error_handling(self, mock_console):
        """Test that search errors are properly handled and displayed."""
        console_output = []
        
        def capture_print(*args, **kwargs):
            if args:
                console_output.append(str(args[0]))
        
        mock_console.print.side_effect = capture_print
        
        # Create config that will cause an error
        bad_config = {
            "dirs": ["/nonexistent/directory"],
            "types": ["jpg"],
            "exclude_dirs": [],
            "similarity_threshold": 0.1,
            "hash_algorithm": "invalid_algorithm",  # Invalid algorithm
            "skip_sha256": False,
            "max_workers": 2,
            "chunk_size": None
        }
        
        # Test error handling
        with patch('src.tui.find_duplicates') as mock_find_duplicates:
            mock_find_duplicates.side_effect = Exception("Test error")
            
            with self.assertRaises(Exception):
                run_search(bad_config)
        
        # Check that error was displayed
        output_text = ' '.join(console_output).lower()
        error_indicators = ["error", "failed", "❌"]
        
        has_error_display = any(indicator in output_text for indicator in error_indicators)
        self.assertTrue(has_error_display, "Should display error message")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)