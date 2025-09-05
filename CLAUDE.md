# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhotoChomper is a high-performance Python-based tool for managing and organizing massive photo collections (200K+ files) by identifying duplicate images and videos. Version 3.1+ introduces revolutionary performance optimizations that reduce processing time from hours/days to minutes through advanced algorithmic improvements and memory-conscious design.

## Version Management

**CRITICAL: Version numbers must be incremented with every code change!**

### Version Tracking System
- Version information is stored in `src/version.py`
- Current version: **3.1.8** (Improved user experience with progress feedback and enhanced error handling)
- Follows semantic versioning: MAJOR.MINOR.PATCH

### Version Increment Rules
**Every time the code is modified, you MUST:**

1. **Update `src/version.py`:**
   - Increment `__version__` string
   - Update `__version_info__` tuple
   - Add entry to `VERSION_HISTORY` list

2. **Version Increment Guidelines:**
   - **PATCH** (+0.0.1): Bug fixes, small improvements, documentation updates
   - **MINOR** (+0.1.0): New features, enhancements, significant improvements
   - **MAJOR** (+1.0.0): Breaking changes, major architecture changes

3. **Example Version Update:**
   ```python
   # Before change
   __version__ = "3.1.0"
   __version_info__ = (3, 1, 0)
   
   # After documentation update
   __version__ = "3.1.1"
   __version_info__ = (3, 1, 1)
   VERSION_HISTORY = [
       "3.1.1 - Updated README with enhanced features documentation and version tracking system",
       "3.1.0 - Enhanced progress tracking, time estimation, and configurable chunking",
       # ... existing history
   ]
   ```

### Version Display
- Version is shown on all command executions: `python main.py --setup`
- Dedicated version command: `python main.py --version`
- Help text includes version: `python main.py --help`

### Key Features
- **Scalable Performance**: Handles 200K+ photos with 100-1000x speedup through LSH-based optimization
- **Memory-Efficient Processing**: Stable memory usage regardless of collection size via chunked processing
- **Two-Stage Detection**: Fast SHA256 exact duplicates + perceptual similarity for remaining files
- **Persistent Caching**: SQLite-based hash caching provides 90%+ speedup on repeated runs
- **Advanced TUI**: Interactive setup, duplicate review, and selective file actions
- **Comprehensive Reporting**: CSV/JSON/Markdown exports with detailed analysis

## Development Commands

### Setup and Installation

#### Dependency Tiers

**Minimal Setup** (SHA256 exact duplicates only):
```bash
# No additional dependencies needed - uses built-in libraries only
python main.py --setup
```

**Standard Setup** (recommended for most users - includes perceptual similarity):
```bash
# Core dependencies for full duplicate detection capabilities
pip install Pillow imagehash psutil rich pandas

# Or using uv (recommended package manager)
uv pip install Pillow imagehash psutil rich pandas
```

**Full Setup** (all advanced features):
```bash
# All dependencies including advanced metadata extraction and video processing
pip install Pillow imagehash opencv-python ffmpeg-python iptcinfo3 python-xmp-toolkit exifread psutil rich pandas

# Or using uv
uv pip install Pillow imagehash opencv-python ffmpeg-python iptcinfo3 python-xmp-toolkit exifread psutil rich pandas
```

#### Optional Dependencies Breakdown

**Core Image/Video Processing:**
- `Pillow` + `imagehash`: Required for perceptual hashing (dhash, phash, ahash, whash)
- `ffmpeg-python`: Video duplicate detection with frame-based analysis
- `opencv-python`: Advanced image quality analysis and ranking

**Metadata Extraction:**
- `iptcinfo3`: IPTC metadata from images (keywords, captions, copyright)
- `python-xmp-toolkit`: XMP metadata support
- `exifread`: Enhanced EXIF data reading (GPS, camera settings)

**Performance & UI:**
- `psutil`: Memory usage monitoring and system statistics
- `rich`: Enhanced terminal UI with colors and interactive tables
- `pandas`: Advanced data analysis and reporting capabilities

#### Graceful Fallbacks
PhotoChomper automatically adapts when optional dependencies are missing:
- **Without Pillow/imagehash**: Falls back to SHA256-only exact duplicate detection
- **Without psutil**: Uses basic resource monitoring
- **Without opencv**: Skips advanced image quality analysis
- **Without ffmpeg**: Treats videos as regular files (SHA256 only)
- **Without rich**: Uses basic console output
- **Without pandas**: Provides limited reporting features

### Running the Application
```bash
# Interactive setup (creates configuration file)
python main.py --setup

# Run duplicate search using existing config
# Generates CSV, JSON, and SQLite database outputs
python main.py --search

# Interactive duplicate review with file actions
python main.py --review

# Generate markdown summary from existing reports
python main.py --summary

# Schedule repeated searches (runs every N hours)
python main.py --schedule 1

# Specify custom config directory/file
python main.py --configdir "path/to/configs" --config "photochomper_config_YYYYMMDD_HHMMSS.conf"
```

### Testing and Quality

**CRITICAL REQUIREMENT: Every version increment MUST include persistent test scripts to verify fixes**

#### Test Script Requirements

**For every version increment and bug fix, Claude MUST:**

1. **Create Version-Specific Test Scripts**: 
   - Create test files in `/tests/version_tests/` directory
   - Name format: `test_v{version}_{fix_description}.py`
   - Include the exact version number in comments and metadata
   - Test scripts must be persistent and reusable

2. **Test Script Structure**:
   ```python
   """
   Test script for PhotoChomper v{version}
   Created: {date}
   Purpose: Verify fix for {specific_issue}
   
   This test verifies that {specific_problem} has been resolved.
   """
   
   def test_{fix_name}_v{version}():
       # Test implementation
       pass
   
   def regression_test_previous_fixes():
       # Verify all previous version fixes still work
       pass
   ```

3. **Mandatory Test Categories**:
   - **Unit Tests**: Test the specific fix in isolation
   - **Integration Tests**: Test the fix within the full application
   - **Regression Tests**: Verify all previous fixes remain functional
   - **Performance Tests**: Ensure no performance degradation

#### Version-Specific Testing Protocol

**Example for v3.1.5 (HashCache comparison error fix):**

```bash
# Create test script
tests/version_tests/test_v3.1.5_hashcache_comparison.py

# Test the specific fix
python tests/version_tests/test_v3.1.5_hashcache_comparison.py

# Run full regression suite
python tests/run_all_version_tests.py

# Performance validation
python tests/performance_regression_tests.py
```

#### Test Automation Requirements

**Claude must create these files for EVERY version increment:**

1. **`tests/version_tests/test_v{version}_{issue}.py`**
   - Specific test for the current fix
   - Must reproduce the original issue and verify the fix
   - Include negative tests (edge cases that should still fail safely)

2. **`tests/regression/regression_suite_v{version}.py`**
   - Comprehensive test of ALL previous version fixes
   - Automated execution of all version-specific tests
   - Performance benchmarking against previous versions

3. **`tests/integration/integration_v{version}.py`**
   - End-to-end testing with the fix in place
   - Real-world scenario testing
   - Memory usage and error handling validation

#### Test Execution Protocol

**Before marking any fix as complete, Claude MUST:**

1. **Immediate Testing**: Run the new test script to verify the fix works
2. **Integration Testing**: Run full application tests with the fix
3. **Regression Testing**: Execute ALL previous version test scripts
4. **Performance Testing**: Verify no performance degradation
5. **Documentation**: Update test documentation with results

#### Test Documentation Requirements

**Each test script must include:**
- **Version Created**: Exact version number (e.g., "Created for PhotoChomper v3.1.5")
- **Issue Reference**: Link to TODO.md or issue description
- **Test Methodology**: How the test validates the fix
- **Expected Results**: Clear pass/fail criteria
- **Dependencies**: Required setup or test data
- **Execution Instructions**: How to run the test

#### Manual Testing Procedures

```bash
# Standard manual testing workflow
python main.py --setup
python main.py --search
python main.py --review
python main.py --summary

# Version-specific testing
python tests/version_tests/test_v{current_version}_{fix}.py

# Full regression testing
python tests/run_all_version_tests.py --verbose
```

#### Test Data Management

**Claude must maintain:**
- **`tests/test_data/`**: Sample files for testing
- **`tests/expected_results/`**: Expected output files for comparison
- **`tests/benchmarks/`**: Performance baseline data
- **`tests/logs/`**: Test execution logs by version

#### Testing Implementation Success (v3.1.5 Example)

**v3.1.5 serves as the reference implementation for all future versions:**

✅ **Version-Specific Test**: `tests/version_tests/test_v3.1.5_hashcache_comparison.py`
- 7 comprehensive tests validating HashCache comparison error fix
- Type safety validation and error handling verification
- Performance baseline establishment

✅ **Regression Test Suite**: `tests/regression/regression_suite_v3.1.5.py`
- Validates functionality from v3.1.4 back to v1.0.0
- Thread safety, LSH optimization, chunking, configuration testing
- Version tracking and error handling regression tests

✅ **Automated Test Runner**: `tests/run_all_version_tests.py`
- Single-command execution: `python tests/run_all_version_tests.py`
- Selective testing: `--version-tests`, `--regression-tests`, `--verbose`
- Detailed logging with timestamps and performance metrics

✅ **Test Results**: 100% pass rate across all test categories
- Version-specific: 7/7 tests passed
- Regression: 7/7 tests passed
- Performance: Baseline established and monitored

#### Future Version Testing Checklist

For every new version (e.g., v3.1.6), Claude must:

1. ☐ Create `tests/version_tests/test_v{version}_{fix_description}.py`
2. ☐ Update `tests/regression/regression_suite_v{version}.py`
3. ☐ Run complete test suite: `python tests/run_all_version_tests.py`
4. ☐ Verify 100% pass rate before considering version complete
5. ☐ Update benchmarks and validate performance
6. ☐ Update documentation with test results

## Architecture and Code Structure

### Core Modules

- **main.py**: Entry point with argument parsing and command routing
- **src/config.py**: Configuration file management (JSON-based .conf files with timestamp naming)
- **src/tui.py**: Terminal User Interface for interactive setup, duplicate review, and file actions
- **src/scanner.py**: Core duplicate detection with multiple algorithms (SHA256, dhash, phash, ahash, whash)
- **src/report.py**: Report generation and export functionality (CSV/JSON/Markdown formats)
- **src/actions.py**: File action system for delete/move operations with backup and rollback
- **src/old_chomper.py**: Legacy code (previous implementation)

### Key Dependencies

- **rich**: Terminal UI and formatting for TUI components
- **pandas**: Data manipulation and analysis for reports
- **pillow**: Image processing capabilities
- **imagehash**: Perceptual hashing algorithms (dhash, phash, ahash, whash)
- **opencv-python**: Advanced image quality analysis (optional)
- **ffmpeg-python**: Video file analysis and frame extraction (optional)
- **pathlib**: Modern path handling
- **concurrent.futures**: Multi-threading for performance

### Configuration System

- Uses JSON-format configuration files with `.conf` extension
- Automatic timestamp naming: `photochomper_config_YYYYMMDD_HHMMSS.conf`
- Configuration includes:
  - Directories to scan and exclude
  - File types and similarity thresholds
  - Hash algorithm selection (dhash, phash, ahash, whash)
  - Master file preferences and quality ranking
  - Move directory for duplicate management
  - Performance settings (threads, memory optimization)
- Multiple configs supported with interactive selection when multiple exist
- Auto-adds "report" to filenames for --summary compatibility

### Duplicate Detection System (v3.0 Optimizations)

PhotoChomper v3.0 introduces revolutionary performance optimizations specifically designed for massive photo collections (200K+ files).

#### Two-Stage Detection Architecture
**Stage 1: Fast SHA256 Exact Duplicates** (scanner.py:638-687)
- Lightning-fast SHA256 computation identifies 30-70% of duplicates instantly
- Eliminates need for expensive perceptual hashing on identical files
- Parallel processing with memory-conscious chunking

**Stage 2: LSH-Optimized Perceptual Similarity** (scanner.py:824-899)
- Only processes files with unique SHA256 hashes
- Locality-Sensitive Hashing reduces O(n²) to ~O(n log n) comparisons
- Progressive similarity thresholds (coarse → fine filtering)
- SQLite caching provides 90%+ speedup on repeated runs

#### Performance Comparison

| Collection Size | v2.0 Comparisons | v3.0 Comparisons | Speedup Factor |
|----------------|-----------------|------------------|----------------|
| 10K files | 50M | 500K | 100x |
| 50K files | 1.25B | 12M | 104x |
| 200K files | 20B | 36M | 555x |

#### Similarity Algorithms
- **dhash**: Difference hash (recommended, good balance of speed/accuracy)
- **phash**: Perceptual hash (best for rotated/scaled images)
- **ahash**: Average hash (fastest, less accurate)  
- **whash**: Wavelet hash (best for edited images, slower)

#### Advanced Optimization Features

**LSH-Based Similarity Grouping** (scanner.py:901-1007)
- Buckets similar hashes to eliminate unnecessary comparisons
- Reduces 20 billion comparisons to ~36 million for 200K files
- Memory-efficient processing prevents system overload

**Progressive Similarity Thresholds** (scanner.py:758-847)
- Coarse filtering eliminates obvious non-matches quickly
- Fine-grained analysis only for promising candidates
- ~50% reduction in expensive similarity calculations

**SQLite Hash Caching** (scanner.py:51-168)
- Persistent cache across multiple runs
- Automatic file change detection and cache invalidation
- 90%+ speedup on repeated scans of same collection

**Memory-Conscious Processing** (scanner.py:247-294)
- Adaptive chunk sizing based on available memory
- Automatic garbage collection between chunks
- Stable memory usage regardless of collection size
- Real-time memory monitoring with warnings

#### Video File Support
- Frame-based analysis with multiple sample points (25%, 50%, 75%)
- Perceptual hashing of extracted frames
- Combined hash signatures for video comparison
- Graceful fallback to file-level hashing when ffmpeg unavailable

### Interactive Review System

#### Enhanced Display
- Row-numbered table with comprehensive metadata
- Color-coded status indicators (green=master, white=duplicate, red=error)
- Full SHA256 hashes and similarity scores
- File details: size (KB), creation date, resolution
- Master file highlighting with crown (👑) indicator

#### Selective File Actions
- **File Selection**: Users can select specific files by row numbers (e.g., "2,3,5")
- **Smart Directory Memory**: Remembers move directories within review sessions
- **Action Previews**: Shows exactly which files will be affected
- **Confirmation Prompts**: Prevents accidental operations
- **Available Actions**:
  - `k` (keep): Choose specific file to keep, delete others
  - `d` (delete): Select specific files to delete
  - `m` (move): Select specific files to move to configured directory
  - `s` (skip): Skip group without changes
  - `a` (auto): Automatic processing with strategy selection
  - `q` (quit): Exit review

### Reporting and Analysis

#### Output Formats
- **CSV**: Detailed tabular data with all metadata, includes Master column showing "Yes" for master photos
- **JSON**: Structured data for programmatic use
- **SQLite**: Relational database with indexed tables and pre-built analysis views for advanced queries
- **Markdown**: Human-readable summaries with analysis and explanations

#### SQLite Database Features
The `--search` command automatically generates a SQLite database (`duplicates_report.db`) alongside CSV and JSON outputs, providing powerful SQL-based analysis capabilities:

**Main Table Structure:**
- Primary key (`id`) for unique record identification
- Master column with "Yes" for master photos, empty for duplicates
- All metadata fields from CSV export (file paths, sizes, dates, camera info, etc.)
- Indexed columns for fast querying (group_id, master, file, size, camera_make, file_type)

**Pre-built Analysis Views:**
- `summary_stats`: Overall statistics (groups, files, masters, duplicates, sizes, file types)
- `groups_by_size`: Duplicate groups ordered by size and file count
- `masters_summary`: Each master with duplicate count and space savings potential
- `file_type_analysis`: Breakdown by file type (JPEG, PNG, etc.)
- `camera_analysis`: Statistics by camera make/model
- `size_analysis`: Files categorized by size ranges with potential savings
- `match_reasons_analysis`: Why files were considered duplicates
- `directory_analysis`: Statistics by directory path

**Example SQL Queries:**
```sql
-- Get overall summary
SELECT * FROM summary_stats;

-- Find largest duplicate groups
SELECT * FROM groups_by_size LIMIT 10;

-- See masters with most duplicates
SELECT master_name, duplicate_count, duplicates_total_size 
FROM masters_summary ORDER BY duplicate_count DESC;

-- Analyze potential space savings by directory
SELECT path, duplicate_count, potential_savings 
FROM directory_analysis WHERE duplicate_count > 0 
ORDER BY potential_savings DESC;

-- Find all Canon camera duplicates
SELECT * FROM duplicates WHERE camera_make = 'Canon';
```

#### Advanced Summary Features
- Executive summary with key statistics
- File counts per directory with averages
- Search parameter detection and explanation
- Detailed section explanations for user guidance
- Auto-discovery of existing report files (must contain "report" in filename)

### File Action System

#### Action Types
- **DELETE**: Remove files with backup capability
- **MOVE**: Relocate files to specified directories
- **Batch Processing**: Handle multiple actions with progress tracking
- **Rollback Support**: Undo operations if needed

#### Safety Features
- Backup creation before destructive operations
- Confirmation prompts for all actions
- Progress tracking with detailed feedback
- Error handling with graceful fallbacks

## Important Implementation Notes

### File Structure Conventions
- Configuration files use `.conf` extension but contain JSON data
- Reports generated with timestamp suffixes for uniqueness
- Auto-naming ensures "report" appears in filenames for --summary compatibility
- Log files append-only for tracking execution history

### TUI Design Patterns
- Uses Rich library for colored terminal output and interactive tables
- Provides sensible defaults for all configuration options with clear explanations
- Interactive selection menus for multiple configurations
- Enhanced visual feedback with emojis and color coding
- Responsive table layouts with text wrapping

### Performance Optimization (v3.0 Breakthrough)

PhotoChomper v3.0 delivers unprecedented performance for massive photo collections through multiple algorithmic innovations:

#### Core Optimizations

**Two-Stage Hashing Strategy**
- Stage 1: Fast SHA256 for exact duplicates (30-70% reduction)
- Stage 2: Expensive perceptual hashing only for unique files
- Eliminates millions of unnecessary image processing operations

**Locality-Sensitive Hashing (LSH)**
- Reduces similarity comparisons from O(n²) to ~O(n log n)
- Buckets similar hashes to avoid comparing dissimilar files
- 100-1000x reduction in hash comparison operations

**Progressive Similarity Filtering**
- Coarse threshold filtering (fast) → Fine threshold analysis (precise)
- Eliminates obvious non-matches before expensive calculations
- Additional 50% reduction in similarity computations

**SQLite Persistent Caching**
- Stores computed hashes with file modification time tracking
- 90%+ speedup on repeated scans of same collections
- Automatic cache invalidation when files change
- Scales efficiently to millions of cached entries

#### Memory Management

**Adaptive Chunked Processing**
- Dynamic chunk sizing based on available system memory
- Prevents memory overflow regardless of collection size
- Garbage collection between chunks maintains stable usage
- Conservative memory estimation ensures system stability

**Real-Time Memory Monitoring**
- Continuous memory usage tracking with psutil integration
- Automatic warnings when usage exceeds 85%
- Graceful fallback monitoring when psutil unavailable
- Memory usage caps prevent system instability

#### Performance Metrics for Large Collections

| Metric | 50K Files | 100K Files | 200K Files |
|--------|-----------|------------|------------|
| **Processing Time** | 2-5 minutes | 5-10 minutes | 10-20 minutes |
| **Memory Usage** | <1GB stable | <1.5GB stable | <2GB stable |
| **Cache Benefit** | 90% faster | 92% faster | 95% faster |
| **Disk I/O** | Minimized | Chunked | Optimized |

#### Multi-Threading Enhancements
- Configurable worker threads (default: 4, max: CPU cores)
- Separate I/O and CPU-bound thread pools
- Optimized file reading with buffering
- Progress tracking with detailed completion estimates

### Error Handling and Safety
- Graceful handling of file read errors in hash calculation
- Configuration loading/saving with comprehensive error logging
- User input validation in TUI components
- UTF-8 encoding for cross-platform compatibility (fixes Windows Unicode issues)
- Comprehensive exception handling with user-friendly error messages

### Data Flow Architecture
1. **Setup Phase**: Interactive TUI collects configuration
2. **Scanning Phase**: Multi-threaded file discovery and hashing
3. **Analysis Phase**: Similarity grouping and master file selection
4. **Review Phase**: Interactive duplicate management with selective actions
5. **Action Phase**: Batch execution of user-selected operations
6. **Reporting Phase**: Comprehensive analysis and summary generation

### Key Design Decisions
- **Dual Hash System**: Always calculate SHA256 alongside similarity hashes
- **Selective Actions**: Users can choose specific files rather than entire groups
- **Directory Memory**: Session-based memory for move directories
- **Auto-Discovery**: Filename patterns enable automatic report finding
- **Rich Metadata**: Comprehensive file information for informed decisions
- **Safety First**: Multiple confirmation layers and backup systems

### Version History and Major Enhancements

#### Version 3.0 (Performance Revolution)
**Revolutionary optimizations for massive photo collections (200K+ files):**
- **Two-Stage Detection**: SHA256 exact duplicates → perceptual similarity for unique files only
- **LSH Optimization**: Locality-Sensitive Hashing reduces O(n²) to ~O(n log n) comparisons  
- **Progressive Thresholds**: Coarse → fine filtering eliminates 50% of expensive calculations
- **SQLite Caching**: Persistent hash storage with 90%+ speedup on repeated runs
- **Memory-Conscious Design**: Adaptive chunking prevents overflow, stable <2GB usage
- **Performance Metrics**: 555x speedup for 200K files, minutes instead of hours/days
- **Graceful Fallbacks**: Works without optional dependencies (psutil, PIL, etc.)
- **Enhanced Logging**: Detailed optimization metrics and memory usage tracking

#### Version 2.0 (Enhanced User Experience)  
- Enhanced review interface with row numbers and comprehensive metadata
- Selective file action system (choose specific files by row numbers)
- Always-on SHA256 calculation alongside similarity algorithms
- Smart directory memory for move operations
- Improved setup with better defaults display
- Advanced similarity scoring with detailed explanations
- Comprehensive reporting with executive summaries and analysis

### Future Development Areas
Building on the v3.0 performance foundation, planned enhancements include:
- **Ultra-Scale Processing**: Optimizations for 1M+ file collections using distributed processing
- **Advanced AI Integration**: Machine learning-based duplicate detection and quality scoring
- **Cloud Storage Support**: Direct processing of Google Photos, iCloud, and other cloud services
- **Advanced Metadata Extraction**: GPS clustering, camera timeline analysis, duplicate origin tracking
- **Real-Time Monitoring**: File system watchers for automatic duplicate detection
- **API Integration**: REST API for integration with photo management applications
- **Multi-language Support**: Internationalization for global user base
- **Desktop Integration**: Native file manager plugins and system tray applications

### Debugging and Troubleshooting

#### Performance Monitoring
- Check `photochomper.log` for detailed optimization metrics and timing information
- Memory usage warnings appear when usage exceeds 85% with adaptive chunk reduction
- Cache hit rates and LSH reduction factors logged for performance analysis
- Progress tracking with ETA calculations and processing speed metrics

#### Common Issues and Solutions
- **High Memory Usage**: Reduce chunk size or enable more aggressive garbage collection
- **Slow Performance**: Ensure Standard Setup dependencies installed (Pillow, imagehash, psutil)
- **Cache Issues**: Delete `photochomper_hash_cache.db` to rebuild cache if corrupted
- **Missing Dependencies**: Application gracefully falls back with reduced functionality
- **Large Collections**: Use chunk size optimization for collections >100K files

#### Advanced Troubleshooting
- **LSH Bucket Analysis**: Review bucket distribution in logs for similarity threshold tuning
- **Stage Distribution**: Monitor SHA256 vs perceptual processing ratios for optimization
- **Memory Profiling**: Use psutil integration for detailed memory usage patterns
- **Cache Performance**: Track cache hit/miss ratios to optimize storage strategies
- **Thread Optimization**: Adjust worker thread count based on CPU cores and I/O characteristics