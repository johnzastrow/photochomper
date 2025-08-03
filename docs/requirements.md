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
