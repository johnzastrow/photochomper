# Photochomper Requirements

August 2, 2025

A program to reduce the number of duplicate photos in a user's collection by comparing images across directories and file types, providing a user-friendly interface for managing duplicates, and supporting various features for efficient duplicate handling. It is suitable for users with large photo collections who want to organize and manage their images initially and on an ongoing basis through scheduled scans.

Product Name: Photochomper

Create a full set of documentation for the Photochomper program, including requirements, design, and user documentation. The documentation should be comprehensive and cover all aspects of the program, including building, installation, configuration, usage, and troubleshooting and make it easy for users to understand and use the program effectively and publish it on GitHub.

## 1. Platform & Performance
- Cross-platform: Windows, macOS, Linux.
- Efficient handling of large directories (support for 300,000+ photos).
- Multi-threading to speed up search process.
- Lightweight application; does not consume excessive system resources.
- Can run in the background while the user continues to use their computer.
- Support reading mapped network drives and external storage devices.
- Application can be built as a single executable file for easy distribution.

## 2. Duplicate Detection Features
- Find duplicate photos recursively across directories and file types.
- Compare photos by content (image data, SHA-256 hash) and name.
- Compare metadata tags (EXIF, creation/modification dates, keywords, GPS, camera model, lens, software).
- Advanced image comparison algorithm for different types and formats.
- Support for different image formats (JPEG, PNG, GIF, CR2, DNG, TIFF, BMP, HEIC, WEBP, AVIF, PSD, RAW, etc.) and video formats (MP4, AVI, MOV).
- Analyze image quality (resolution, sharpness, color balance, Laplacian variance, Radon transform).
- Analyze duplicate metadata (EXIF data).
- Analyze duplicate handling performance metrics (time taken, number found, actions taken).

## 3. Duplicate Handling & Actions
- Options to delete, move, tag, or report duplicates (default: report).
- Tag photos as duplicates using image tags for easy searching.
- Provide a mechanism for users to back up images before deletion.
- Allow users to rate images to prioritize which duplicates to keep.
- Allow users to set up custom actions for handling duplicates (move, rename, tag).
- Provide options for batch processing of directories.
- Provide a report of duplicates found in delimited text format.
- Export reports in various formats (CSV, JSON).
- Allow reading exported report to complete suggested actions.
- Generate summary report of duplicate handling actions taken.
- Generate custom reports based on user-defined criteria (file types, directories, image attributes).
- Generate alerts for potential duplicate issues.
- Provide a mechanism for users to set up custom notifications for duplicate handling events.

## 4. User Interface & Experience
- Text User Interface (TUI) guides setup of configuration file for scanning directories and actions.
- TUI allows specifying preferences for master file selection (longest/shortest file name, most/least recent).
- TUI guides setup of preferences for scanning directories into a human-editable text file, reusable for scheduled runs.
- Progress indicator during search and removal process.
- Help section or user guide within the application.
- Support localization for different languages.
- Provide a mechanism for users to save their search preferences.
- Allow users to set up notifications for when duplicates are found.

## 5. Configuration & Customization
- Specify directories to search and exclude (in TUI and config file).
- Search/exclude specific file types (JPEG, PNG, GIF, etc.) in config file.
- Specify similarity threshold for image comparison in config file.
- Search/exclude directories based on keywords in directory names in config file.
- Specify file types to include in search.
- Configure similarity thresholds for image comparison.
- Allow users to set up custom rules for identifying duplicates.

## 6. Duplicate Ranking & Characteristics
- Duplicates weighted so only master is suggested for keeping; others ranked by similarity, file name/path, attributes (creation/modification date, keywords).
- Characteristics for ranking:
  - Keywords in image tags, file names, or paths.
  - Length of file name/path.
  - Modified/created date and time.
  - Image file types.
  - Dimensions (width/height).
  - EXIF data (camera model, lens, GPS/location).
  - File size (larger/smaller than threshold).
  - Creation/modification software (e.g., Photoshop, GIMP).
- Examples:
  1. Mark images with keyword "duplicate" in file name, path, or image tag.
  2. Mark images with longer file path.
  3. Mark images with shorter file name.
  4. Mark images without any or specific image tags.
  5. Mark images with specific creation/modification dates.
  6. Mark images with specific file types.
  7. Mark images with specific dimensions.
  8. Mark images with specific EXIF data.
  9. Mark images with specific GPS coordinates/locations.
  10. Mark images with specific file sizes.
  11. Mark images with specific creation/modification software.

## 7. Reporting & Logging
- Output includes:
  - Full path to image.
  - Starting search directory.
  - Date/time of search.
  - Grouping number for duplicate sets.
  - Attributes used to determine duplicates (file name, path, creation date, modified date, image tags).
  - SHA-256 hash of image content.
  - Suggested action (keep, delete, move, tag).
  - Similarity score compared to master image.
- Log actions taken during duplicate search and removal process.

## 8. Scheduling & Automation
- Mechanism for users to schedule duplicate searches at regular intervals.
- Provide options for scheduling duplicate searches at regular intervals.

## 9. Documentation & Testing
- Comprehensive documentation for users (building, installation, configuration, usage, troubleshooting).
- Publish documentation on GitHub.
- Implement unit tests to ensure reliability and correctness.
- Do not store or report any personal information about the user or their images.

## 10. Miscellaneous
- Feature for tagging images to categorize them.

---

*All requirements above are derived from the original document and reorganized for clarity and logical


A reviewer wrote the following about the alpha version of Photochomper:

Here are further improvements to better meet the requirements:

1. Advanced Duplicate Detection
Implement perceptual hashing (e.g., imagehash, phash, dhash) for similar images, not just exact matches.
Add support for video file hashing and metadata extraction.
2. Metadata Extraction
Use libraries like Pillow or exifread for EXIF, GPS, camera model, lens, and other metadata.
Extract and compare metadata for ranking and reporting.
3. Image Quality Analysis
Integrate image quality metrics (resolution, sharpness, color balance, Laplacian variance, etc.) using OpenCV or PIL.
4. Custom Actions & Tagging
Allow users to tag, rate, or rename duplicates via TUI.
Enable custom rules for handling duplicates (move, rename, tag, etc.).
5. Batch Processing
Add batch delete/move/tag actions with confirmation and backup.
Allow importing actions from exported reports.
6. Reporting & Logging
Include more attributes in reports (creation/modification dates, file size, EXIF, GPS, etc.).
Generate summary and custom reports based on user criteria.
Log all actions and errors with more detail.
7. Notifications & Alerts
Add desktop notifications or email alerts when duplicates are found or actions are taken.
8. Localization
Support multiple languages for the TUI and reports.
9. Scheduling
Integrate with OS schedulers (Windows Task Scheduler, cron) for background scans.
10. User Documentation
Provide comprehensive user and troubleshooting guides.
Add a help section in the TUI.
11. Unit Testing
Add unit tests for all major functions to ensure reliability.
12. Performance
Use multi-threading or multiprocessing for scanning and hashing large directories.
Optimize file I/O and hashing for speed.
13. Configuration
Allow saving/loading multiple configurations.
Support exclusion/inclusion by keywords in directory names.
14. Security & Privacy
Ensure no personal data is stored or reported.
Provide clear privacy information in documentation.

Summary:
Implementing these features will make Photochomper more robust, user-friendly, and fully compliant with your requirements. Most enhancements involve integrating third-party libraries, improving the TUI, and expanding reporting and configuration options.

The plan is to implement these features in the next version of Photochomper, ensuring it meets all outlined requirements and provides a comprehensive solution for managing duplicate photos effectively.

 Perfect! The comprehensive improvement plan for PhotoChomper has been created and approved. The analysis revealed
   that while the current implementation provides a solid foundation, it's missing approximately 70% of the
  required functionality.

  Key Findings:

  Current Implementation Strengths:
  - Clean modular architecture with proper separation of concerns
  - Basic duplicate detection using SHA-256 hashing
  - TUI-based configuration system
  - CSV/JSON reporting capabilities
  - Logging and basic progress tracking

  Critical Gaps Identified:
  - Advanced Detection: Missing perceptual hashing, video support, image quality analysis
  - Action Execution: No delete/move/tag operations, only reporting
  - Performance: Single-threaded, not optimized for large collections (300k+ photos)
  - User Experience: Limited TUI functionality, no interactive duplicate review
  - Automation: Basic scheduling only, no OS integration

  16-Week Implementation Roadmap:

  Phase 1 (Weeks 1-4): Core functionality with perceptual hashing, multi-threading, video support, and action
  execution system

  Phase 2 (Weeks 5-8): Advanced detection with OpenCV integration, enhanced EXIF processing, and custom ranking
  rules

  Phase 3 (Weeks 9-12): Enhanced UX with textual framework, automation/scheduling, and comprehensive reporting

  Phase 4 (Weeks 13-16): Enterprise features including testing, documentation, localization, and plugin
  architecture

  The plan provides a clear path to transform PhotoChomper from a basic duplicate detector into a comprehensive
  photo management solution that fully meets the detailed requirements while maintaining clean, maintainable code
  architecture.



  
● To run PhotoChomper with uv, you have a few options depending on how you want to manage dependencies:

  Option 1: Install dependencies and run directly

  # Install all Phase 1 dependencies using uv
  uv pip install pandas rich pillow imagehash opencv-python ffmpeg-python exifread psutil textual typer

  # Then run the application
  python main.py --setup
  python main.py --search
  python main.py --review

  Option 2: Use uv with the pyproject.toml file

  Since the project has a pyproject.toml file with all dependencies defined:

  # Install the project and its dependencies
  uv pip install -e .

  # Then run normally
  python main.py --setup
  python main.py --review

  Option 3: Use uv run (if you have uv 0.2.0+)

  # Run directly with uv managing dependencies
  uv run python main.py --setup
  uv run python main.py --review

  Option 4: Create a virtual environment with uv

  # Create and activate virtual environment
  uv venv photochomper-env
  source photochomper-env/bin/activate  # On Windows: photochomper-env\Scripts\activate

  # Install dependencies
  uv pip install -e .

  # Run the application
  python main.py --setup
  python main.py --review

  Testing the enhanced features

  Once dependencies are installed, you can test the new Phase 1 features:

  # Test the core functionality
  python test_perceptual.py
  python test_video.py
  python test_actions.py
  python test_interactive_review.py

  # Test the full interactive review workflow
  python main.py --setup    # Configure with new perceptual hashing options
  python main.py --review   # Interactive duplicate review with actions

  Dependencies installed by uv

  The Phase 1 implementation requires these packages:
  - pandas - Data processing for reports
  - rich - Rich terminal UI components
  - pillow - Image processing
  - imagehash - Perceptual hashing algorithms
  - opencv-python - Image quality analysis
  - ffmpeg-python - Video metadata extraction
  - exifread - Enhanced EXIF reading
  - psutil - Memory optimization
  - textual - Advanced TUI components
  - typer - CLI enhancements

  The fastest approach is usually Option 1 if you just want to try the features quickly, or Option 2 if you want a proper installation.

  error: Failed to inspect Python interpreter from virtual environment at `.venv\Scripts\python.exe`
  Caused by: Python interpreter not found at `C:\Users\br8kw\Github\photochomper\photochomper\.venv\Scripts\python.exe`

 uv pip install threw this error:

● I notice you mentioned that uv pip install threw an error, but I don't see the actual error message in your message. Could you please share the
  specific error you encountered?

  In the meantime, here are some common issues and solutions when using uv with this project:

  Common uv pip install issues:

  1. If you get a "pyproject.toml not found" error:

  # Make sure you're in the right directory
  pwd
  ls -la pyproject.toml

  2. If you get dependency resolution errors:

  # Try installing dependencies individually
  uv pip install pandas rich pillow
  uv pip install imagehash opencv-python
  uv pip install ffmpeg-python exifread psutil textual typer

  3. If you get permission errors:

  # Create a virtual environment first
  uv venv
  source .venv/bin/activate  # or .venv\Scripts\activate on Windows
  uv pip install -e .

  4. If opencv-python fails to install:

  # Try the headless version instead
  uv pip install opencv-python-headless

  5. If ffmpeg-python fails:

  # You might need ffmpeg system package first
  sudo apt install ffmpeg  # On Ubuntu/Debian
  # or
  brew install ffmpeg      # On macOS

  Please share the exact error message you're seeing, and I can provide a more targeted solution!

> error: Failed to inspect Python interpreter from virtual environment at `.venv\Scripts\python.exe`
    Caused by: Python interpreter not found at `C:\Users\br8kw\Github\photochomper\photochomper\.venv\Scripts\python.exe`

● This error indicates that the virtual environment wasn't created properly or is corrupted. Let's fix this step by step:

  Solution: Recreate the virtual environment

  # First, remove the existing broken .venv directory
  rm -rf .venv

  # Create a fresh virtual environment with uv
  uv venv

  # Activate the virtual environment
  # On WSL/Linux:
  source .venv/bin/activate
  # OR on Windows Command Prompt (if you're using that):
  # .venv\Scripts\activate

  # Verify Python is working
  python --version

  # Now install the dependencies
  uv pip install -e .

  Alternative approach if the above doesn't work:

  # Remove broken venv
  rm -rf .venv

  # Create venv with explicit Python version
  uv venv --python python3

  # Activate and install
  source .venv/bin/activate
  uv pip install pandas rich pillow imagehash opencv-python ffmpeg-python exifread psutil textual typer

  Quick test without virtual environment:

  If you want to test immediately without a venv:

  # Install directly to your system Python (not recommended for production)
  uv pip install --system pandas rich pillow imagehash opencv-python ffmpeg-python exifread psutil textual typer

  # Then run
  python main.py --setup

  Check your current environment:

  # Verify you're in the right directory
  pwd
  ls -la

  # Check if Python 3 is available
  which python3
  python3 --version

  The key issue is that uv tried to find a Python interpreter in a Windows-style path (C:\Users\...) but you're in WSL, so the paths don't match up.
  The fresh uv venv command should create a proper WSL-compatible virtual environment.

  Try the first solution and let me know if you encounter any other errors!


  Looking at the code in src/tui.py:298-300, the Quality score is calculated as:

  if metadata['width'] and metadata['height']:
      pixels = metadata['width'] * metadata['height']
      quality_score = f"{(pixels * stat.st_size) / 1000000:.1f}"

  What the Quality Score Represents

  The Quality score is a composite metric that combines:
  - Image resolution (width × height = total pixels)
  - File size (in bytes)

  How It's Calculated

  Formula: (pixels × file_size_bytes) / 1,000,000

  Example:
  - Image: 1920×1080 pixels = 2,073,600 pixels
  - File size: 2.1 MB = 2,100,000 bytes
  - Quality score = (2,073,600 × 2,100,000) ÷ 1,000,000 = 4,354.6

  What Higher Scores Mean

  A higher quality score indicates:
  - Better resolution (more pixels)
  - Larger file size (less compression/higher quality)
  - Better overall image quality

  This helps identify which duplicate is the "best" version to keep - typically the one with higher resolution and
  less compression artifacts.

  The score is used to help determine the "master" file (shown in green with 👑) when multiple duplicates are
  found.

  