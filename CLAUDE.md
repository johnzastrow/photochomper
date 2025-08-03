# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhotoChomper is a Python-based tool for managing and organizing photo collections by identifying duplicate images and videos. It features an advanced terminal user interface (TUI) for interactive setup and configuration, supports multiple similarity detection algorithms, provides interactive duplicate review with selective file actions, and includes comprehensive reporting capabilities.

## Development Commands

### Setup and Installation
```bash
# Install dependencies using uv (recommended package manager)
uv pip install -r requirements.txt

# Alternative: Install dependencies from pyproject.toml
uv pip install -e .

# Optional dependencies for enhanced features
uv pip install opencv-python ffmpeg-python iptcinfo3 python-xmp-toolkit exifread
```

### Running the Application
```bash
# Interactive setup (creates configuration file)
python main.py --setup

# Run duplicate search using existing config
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
```bash
# Run basic functionality test
python main.py --setup
python main.py --search
python main.py --review

# Test summary generation
python main.py --summary

# No specific test framework configured - manual testing recommended
```

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

### Duplicate Detection System

#### Always-Calculated SHA256
- SHA256 hash computed for every file regardless of similarity algorithm
- Used for exact duplicate detection and verification
- Stored alongside similarity hashes for comprehensive analysis

#### Similarity Algorithms
- **dhash**: Difference hash (recommended, good balance of speed/accuracy)
- **phash**: Perceptual hash (best for rotated/scaled images)
- **ahash**: Average hash (fastest, less accurate)
- **whash**: Wavelet hash (best for edited images, slower)

#### Advanced Features
- Video file support with frame-based analysis
- Memory-efficient chunked processing for large collections (100k+ files)
- Multi-threading with configurable worker threads
- Quality ranking with image analysis metrics
- Similarity scoring with configurable thresholds

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
- **CSV**: Detailed tabular data with all metadata
- **JSON**: Structured data for programmatic use
- **Markdown**: Human-readable summaries with analysis and explanations

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

### Performance Optimization
- Multi-threading with configurable worker threads (default: 4)
- Memory-efficient chunked processing for large collections
- Real-time memory usage monitoring and warnings
- Optimized file I/O with progress tracking
- Garbage collection between processing chunks

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

### Recent Major Enhancements (Version 2.0)
- Enhanced review interface with row numbers and comprehensive metadata
- Selective file action system (choose specific files by row numbers)
- Always-on SHA256 calculation alongside similarity algorithms
- Smart directory memory for move operations
- Improved setup with better defaults display
- Advanced similarity scoring with detailed explanations
- Comprehensive reporting with executive summaries and analysis

### Future Development Areas
The project continues to evolve with planned enhancements:
- Advanced metadata extraction (GPS, camera data, software info)
- Enhanced image quality analysis and ranking algorithms
- Desktop notifications and email alerts
- Integration with OS schedulers for background operation
- Multi-language support for international users
- Enhanced batch processing capabilities
- Performance optimizations for very large collections (1M+ files)

### Debugging and Troubleshooting
- Check `photochomper.log` for detailed operation logs
- Memory usage warnings appear when usage exceeds 85%
- Configuration validation with clear error messages
- Progress tracking with percentage completion and time estimates
- Comprehensive error reporting with suggested solutions