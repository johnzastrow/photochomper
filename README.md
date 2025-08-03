# PhotoChomper

PhotoChomper is a Python-based tool for managing and organizing photo collections by identifying duplicate images and videos. It features an advanced terminal user interface (TUI) for easy setup and configuration, supports multiple similarity detection algorithms, provides interactive duplicate review with selective actions, and includes comprehensive reporting capabilities.

---

## Table of Contents

- [PhotoChomper](#photochomper)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Recent Updates](#recent-updates)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
  - [Usage](#usage)
    - [Interactive Setup](#interactive-setup)
    - [Run Duplicate Search](#run-duplicate-search)
    - [Interactive Duplicate Review](#interactive-duplicate-review)
    - [Generate Summary Reports](#generate-summary-reports)
    - [Schedule Repeated Searches](#schedule-repeated-searches)
  - [Duplicate Detection Methods](#duplicate-detection-methods)
  - [Interactive Review Features](#interactive-review-features)
  - [Reporting and Analysis](#reporting-and-analysis)
  - [Configuration](#configuration)
  - [Advanced Usage](#advanced-usage)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)

---

## Key Features

### **🔍 Advanced Duplicate Detection**
- **Multiple algorithms**: SHA256 (exact), dhash, phash, ahash, whash (perceptual)
- **Dual hash system**: SHA256 always calculated alongside similarity algorithm
- **Video support**: Frame-based analysis for video files
- **Configurable similarity thresholds**: Fine-tune detection sensitivity
- **Memory optimization**: Chunked processing for large collections

### **🎯 Interactive Review System**
- **Rich visual interface**: Color-coded display with status indicators
- **Selective file actions**: Choose specific files by row numbers (e.g., "2,3,5")
- **Comprehensive metadata**: SHA256 hashes, similarity scores, file details
- **Smart directory handling**: Remembers move directories across sessions
- **Action previews**: See exactly what will happen before confirmation

### **📊 Advanced Reporting**
- **Multiple formats**: CSV, JSON, and Markdown summaries
- **Comprehensive analysis**: File counts, search parameters, detailed explanations
- **Auto-discovery**: Finds existing reports automatically
- **Executive summaries**: Key statistics and recommendations

### **⚙️ Smart Configuration**
- **Guided setup**: Interactive TUI with clear defaults and explanations
- **Session memory**: Remembers choices within review sessions
- **Flexible file management**: Custom move directories and naming
- **Multi-threading**: Configurable worker threads for performance

---

## Recent Updates

### **Version 2.0** - Major Feature Release
- ✅ **Always-on SHA256**: SHA256 hashes calculated for all files regardless of similarity algorithm
- ✅ **Enhanced Review Interface**: Added row numbers, SHA256 display, and similarity scores
- ✅ **Selective File Actions**: Choose specific files to delete/move instead of entire groups
- ✅ **Smart Directory Memory**: Move directories remembered across review sessions
- ✅ **Improved Setup**: Better defaults display and move directory configuration
- ✅ **Advanced Similarity**: Perceptual hashing with detailed similarity scores
- ✅ **Comprehensive Reporting**: Enhanced summaries with search parameters and explanations

---

## Installation

### **Prerequisites**
- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### **Install Dependencies**

**Using uv (recommended):**
```bash
git clone https://github.com/yourusername/photochomper.git
cd photochomper/photochomper
uv pip install -r requirements.txt
```

**Using pip:**
```bash
pip install -r requirements.txt
```

### **Optional Dependencies for Enhanced Features**
```bash
# For advanced image processing
uv pip install opencv-python

# For video analysis
uv pip install ffmpeg-python

# For metadata extraction
uv pip install iptcinfo3 python-xmp-toolkit exifread
```

### **Building Single Executable for Windows**

PhotoChomper can be built as a single `.exe` file for easy distribution on Windows systems without requiring Python installation.

**Prerequisites for Building:**
- Windows 10/11
- Python 3.8+ installed
- All PhotoChomper dependencies installed

**Install PyInstaller:**
```bash
# Using uv (recommended)
uv pip install pyinstaller

# Or using pip
pip install pyinstaller
```

**Build Single Executable:**
```bash
# Navigate to PhotoChomper directory
cd photochomper/photochomper

# Build single executable (recommended)
pyinstaller --onefile --name="PhotoChomper" --add-data "src;src" main.py

# Alternative: Build with console window (for debugging)
pyinstaller --onefile --console --name="PhotoChomper-Debug" --add-data "src;src" main.py

# Advanced build with icon (if you have an icon file)
pyinstaller --onefile --name="PhotoChomper" --add-data "src;src" --icon="icon.ico" main.py
```

**Build Output:**
- Executable will be created in `dist/PhotoChomper.exe`
- File size: ~50-100MB (includes Python runtime and all dependencies)
- No Python installation required on target machines

**Advanced Build Options:**
```bash
# Build with hidden imports (if you encounter import errors)
pyinstaller --onefile --name="PhotoChomper" ^
    --add-data "src;src" ^
    --hidden-import="PIL" ^
    --hidden-import="imagehash" ^
    --hidden-import="cv2" ^
    --hidden-import="ffmpeg" ^
    main.py

# Build with specific Python optimizations
pyinstaller --onefile --name="PhotoChomper" ^
    --add-data "src;src" ^
    --optimize=2 ^
    --strip ^
    main.py
```

**Testing the Executable:**
```bash
# Test the built executable
cd dist
PhotoChomper.exe --help
PhotoChomper.exe --setup
```

**Distribution:**
- Copy `PhotoChomper.exe` to any Windows machine
- No additional installation required
- Run directly from command prompt or create desktop shortcut

**Troubleshooting Build Issues:**

**Missing modules error:**
```bash
# Add missing modules explicitly
pyinstaller --onefile --name="PhotoChomper" ^
    --add-data "src;src" ^
    --collect-all="rich" ^
    --collect-all="pandas" ^
    --collect-all="PIL" ^
    main.py
```

**Large executable size:**
```bash
# Build directory version (smaller startup time)
pyinstaller --name="PhotoChomper" --add-data "src;src" main.py
# Creates PhotoChomper/ directory with executable and dependencies
```

**Runtime errors:**
```bash
# Build with debug console to see error messages
pyinstaller --onefile --console --name="PhotoChomper-Debug" --add-data "src;src" main.py
```

**Creating Desktop Shortcut:**
1. Right-click on desktop → New → Shortcut
2. Browse to `PhotoChomper.exe`
3. Name: "PhotoChomper - Duplicate Photo Manager"
4. Optional: Change icon in shortcut properties

**Creating Installer (Advanced):**
For professional distribution, consider using NSIS or Inno Setup to create a proper installer:
```bash
# Install NSIS or Inno Setup
# Create installer script that:
# - Copies PhotoChomper.exe to Program Files
# - Creates Start Menu shortcuts
# - Creates Desktop shortcut
# - Adds to Windows Programs list
```

---

## Quick Start

1. **Run Interactive Setup**
   ```bash
   python main.py --setup
   ```

2. **Search for Duplicates**
   ```bash
   python main.py --search
   ```

3. **Review and Manage Duplicates**
   ```bash
   python main.py --review
   ```

4. **Generate Summary Report**
   ```bash
   python main.py --summary
   ```

---

## Usage

### Interactive Setup

```bash
python main.py --setup
```

The setup wizard guides you through:
- **📁 Directories to scan** (with sensible defaults)
- **📄 File types** to include (images and videos)
- **🎯 Similarity detection** algorithm and threshold
- **📂 Move directory** for duplicate management
- **⚡ Performance settings** (threads, memory optimization)
- **📋 Output preferences** (reports, naming conventions)

### Run Duplicate Search

```bash
python main.py --search
```

Performs comprehensive duplicate detection:
- Scans configured directories
- Calculates SHA256 and similarity hashes
- Groups similar/identical files
- Exports results to CSV and JSON

### Interactive Duplicate Review

```bash
python main.py --review
```

**Enhanced Review Interface:**
```
📁 Duplicate Group 1
Found 3 identical/similar files

Row Status      File                Size    Created          Resolution  SHA256                          Similarity
1   👑 MASTER   photo.jpg          245 KB  2023-12-25 14:30 1920x1080   a1b2c3d4e5f6...               MASTER
2   #1 DUPLICATE photo_copy.jpg    245 KB  2023-12-25 14:32 1920x1080   a1b2c3d4e5f6...               0.000
3   #2 DUPLICATE photo_edit.jpg    198 KB  2023-12-25 15:10 1920x1080   b2c3d4e5f6a1...               0.145

💡 Tip: You can select specific files by entering row numbers (e.g., '2,3' for rows 2 and 3)

Choose action [k/d/m/s/q/a]: d
```

**Available Actions:**
- **`k` (keep)**: Choose specific file to keep, delete others
- **`d` (delete)**: Select specific files to delete
- **`m` (move)**: Select specific files to move to folder
- **`s` (skip)**: Skip this group, make no changes
- **`a` (auto)**: Enable automatic processing with chosen strategy
- **`q` (quit)**: Exit review

**Selective Actions Example:**
```
Select files for DELETE (or 'cancel'): 2,3
✅ DELETE: 2 selected file(s)
   #1: photo_copy.jpg
   #2: photo_edit.jpg
Delete 2 selected file(s)? (y/n): y
✅ 2 files queued for deletion
```

### Generate Summary Reports

```bash
# Auto-discover report files
python main.py --summary

# Use specific files
python main.py --summary report1.csv report2.json

# Use wildcard patterns
python main.py --summary *.csv *.json
```

Generates comprehensive Markdown reports with:
- **Executive summary** with key statistics
- **File counts** per directory with averages
- **Search parameters** used for detection
- **Detailed explanations** of each section
- **User guidance** and recommendations

### Schedule Repeated Searches

```bash
python main.py --schedule 24
```
Runs duplicate detection every 24 hours.

---

## Duplicate Detection Methods

### **SHA256 (Always Calculated)**
- **Purpose**: Exact duplicate detection
- **Speed**: Fast
- **Accuracy**: 100% for identical files
- **Use case**: Find perfect copies

### **Similarity Algorithms**
PhotoChomper supports multiple perceptual hashing algorithms:

| Algorithm | Best For | Speed | Accuracy |
|-----------|----------|--------|----------|
| **dhash** | Similar images (recommended) | Fast | High |
| **phash** | Rotated/scaled images | Medium | Very High |
| **ahash** | Quick similarity checks | Fastest | Medium |
| **whash** | Edited/processed images | Slow | Highest |

### **Similarity Thresholds**
- **0.0**: Identical files only
- **0.1**: Very similar (recommended)
- **0.3**: Moderately similar
- **0.5**: Somewhat similar
- **1.0**: Completely different

---

## Interactive Review Features

### **Visual Indicators**
- **🟢 Green**: Master files (recommended to keep)
- **⚪ White**: Duplicate files (candidates for action)
- **🔴 Red**: Missing or error files
- **👑**: Master file indicator
- **#N**: Duplicate numbering

### **Comprehensive Metadata Display**
- **Row numbers**: For easy selection
- **File status**: Master/Duplicate indicators
- **File details**: Size, creation date, resolution
- **SHA256 hashes**: Full 64-character hashes for verification
- **Similarity scores**: Numerical similarity (0.000 = identical)

### **Smart Action Handling**
- **Selective file actions**: Choose specific files by row numbers
- **Directory memory**: Remembers move directories within sessions
- **Action previews**: Shows exactly what will happen
- **Confirmation prompts**: Prevents accidental operations
- **Batch processing**: Handles multiple files efficiently

---

## Reporting and Analysis

### **Output Formats**
- **CSV**: Detailed tabular data for analysis
- **JSON**: Structured data for programmatic use
- **Markdown**: Human-readable summaries with analysis

### **Report Contents**
- **File information**: Paths, sizes, dates, hashes
- **Similarity data**: Algorithms used, scores, thresholds
- **Group analysis**: Master files, duplicate counts
- **Search parameters**: Configuration settings used
- **Execution statistics**: Processing time, file counts

### **Auto-Discovery**
Reports are automatically named with "report" in the filename to enable auto-discovery:
- `duplicates_report_20231225_143022.csv`
- `my_photos_report.json`
- `scan_report_final.csv`

---

## Configuration

### **Configuration Files**
- **Format**: JSON with `.conf` extension
- **Naming**: `photochomper_config_YYYYMMDD_HHMMSS.conf`
- **Location**: Current directory or specified with `--configdir`

### **Key Settings**
```json
{
  "dirs": ["/path/to/photos"],
  "types": ["jpg", "jpeg", "png", "gif", "bmp", "tiff"],
  "exclude_dirs": ["/path/to/exclude"],
  "similarity_threshold": 0.1,
  "hash_algorithm": "dhash",
  "duplicate_move_dir": "/path/to/duplicates_review",
  "max_workers": 4,
  "quality_ranking": false
}
```

### **Multiple Configurations**
When multiple config files exist, PhotoChomper presents an interactive selection menu:
```
Multiple config files found:
  1. photochomper_config_20231225_143022.conf
  2. photochomper_config_20231224_091530.conf
  3. [Create a new config file]
Select config file by number (1-3):
```

---

## Advanced Usage

### **Custom Config and Output Locations**
```bash
python main.py --configdir "/custom/configs" --config "my_config.conf"
```

### **Memory Optimization for Large Collections**
For collections with 100k+ files, enable chunked processing during setup:
- **Auto mode**: Automatically calculates optimal chunk size
- **Manual mode**: Specify custom chunk size
- **Memory monitoring**: Real-time memory usage tracking

### **Multi-threading Configuration**
Adjust worker threads based on your system:
- **4 threads**: Default (good for most systems)
- **8+ threads**: High-end systems with fast storage
- **2 threads**: Older systems or network storage

### **Batch Operations**
```bash
# Process multiple directories
python main.py --search
python main.py --review
python main.py --summary

# Combine operations
python main.py --search && python main.py --summary
```

---

## Troubleshooting

### **Common Issues**

**No duplicates found:**
- Check directory paths are correct
- Verify file types are included in configuration
- Adjust similarity threshold (try 0.3 for more matches)

**Unicode errors on Windows:**
- Issue is automatically handled with UTF-8 encoding
- Reports are saved with proper encoding

**Memory issues with large collections:**
- Enable chunked processing during setup
- Reduce number of worker threads
- Monitor memory usage in logs

**Performance optimization:**
- Use SSD storage for better I/O performance
- Increase worker threads on multi-core systems
- Enable chunked processing for 100k+ files

### **Log Files**
Check `photochomper.log` for detailed information:
- Configuration used
- Processing statistics
- Error messages
- Performance metrics

### **Getting Help**
```bash
python main.py --help
```

Shows all available commands and options.

---

## Contributing

PhotoChomper is actively developed. Contributions are welcome!

### **Development Setup**
```bash
git clone https://github.com/yourusername/photochomper.git
cd photochomper/photochomper
uv pip install -r requirements.txt
```

### **Code Structure**
- `main.py`: Entry point and argument parsing
- `src/scanner.py`: Core duplicate detection algorithms
- `src/tui.py`: Terminal user interface and interactive review
- `src/report.py`: Report generation and analysis
- `src/config.py`: Configuration management
- `src/actions.py`: File action system

### **Testing**
```bash
# Run basic functionality test
python main.py --setup
python main.py --search
python main.py --review
```

---

## License

MIT License - see LICENSE file for details.

---

## Acknowledgements

- [Rich](https://github.com/Textualize/rich) - Beautiful terminal interfaces
- [imagehash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing algorithms
- [Pillow](https://pillow.readthedocs.io/) - Image processing
- [pandas](https://pandas.pydata.org/) - Data analysis and reporting
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) - Video processing

---

*PhotoChomper - Organize your photo collection with confidence* 📸