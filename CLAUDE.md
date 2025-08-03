# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhotoChomper is a Python-based tool for managing and organizing photo collections by identifying and reporting duplicate images. It features a terminal user interface (TUI) for easy setup and configuration, supports advanced metadata analysis, and can be scheduled to run automatically.

## Development Commands

### Setup and Installation
```bash
# Install dependencies using uv (recommended package manager)
uv pip install -r requirements.txt

# Alternative: Install dependencies from pyproject.toml
uv pip install -e .
```

### Running the Application
```bash
# Interactive setup (creates configuration file)
python main.py --setup

# Run duplicate search using existing config
python main.py --search

# Schedule repeated searches (runs every N hours)
python main.py --schedule 1

# Specify custom config directory/file
python main.py --configdir "path/to/configs" --config "photochomper_config_YYYYMMDD_HHMMSS.conf"
```

### Testing and Quality
Note: No specific test commands are currently defined in the project configuration. Check with the user for testing procedures.

## Architecture and Code Structure

### Core Modules

- **main.py**: Entry point with argument parsing and main execution flow
- **src/config.py**: Configuration file management (JSON-based .conf files with timestamp naming)
- **src/tui.py**: Terminal User Interface for interactive setup and configuration
- **src/scanner.py**: Core duplicate detection logic using SHA-256 file hashing
- **src/report.py**: Report generation and export functionality (CSV/JSON formats)
- **src/old_chomper.py**: Legacy code (likely previous implementation)

### Key Dependencies

- **pandas**: Data manipulation and analysis for reports
- **pillow**: Image processing capabilities
- **rich**: Terminal UI and formatting for TUI components

### Configuration System

- Uses JSON-format configuration files with `.conf` extension
- Automatic timestamp naming: `photochomper_config_YYYYMMDD_HHMMSS.conf`
- Configuration includes: directories to scan, file types, exclusion rules, similarity thresholds, master file preferences
- Multiple configs supported with interactive selection when multiple exist

### Duplicate Detection Algorithm

- SHA-256 hash-based exact duplicate detection
- Recursive directory scanning with exclusion support
- File type filtering (jpg, png, gif, bmp, tiff, etc.)
- Master file selection based on path length and filename preferences

### Logging and Output

- Automatic logging to `photochomper.log` with timestamps
- Export formats: CSV and JSON with comprehensive metadata
- Report naming includes timestamps for organization

## Important Implementation Notes

### File Structure Conventions
- Configuration files use `.conf` extension but contain JSON data
- Reports generated with timestamp suffixes for uniqueness
- Log files append-only for tracking execution history

### TUI Design Patterns
- Uses Rich library for colored terminal output and input prompts
- Provides sensible defaults for all configuration options
- Interactive selection menus for multiple configuration files

### Future Development Areas
The project has extensive TODO items including:
- Advanced duplicate detection (perceptual hashing, video support)
- Enhanced metadata extraction (EXIF, GPS, camera data)
- Image quality analysis and ranking
- Batch processing capabilities
- Desktop notifications and scheduling integration
- Multi-language support

### Error Handling
- Graceful handling of file read errors in hash calculation
- Configuration loading/saving with error logging
- User input validation in TUI components