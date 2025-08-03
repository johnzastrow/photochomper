# PhotoChomper

PhotoChomper is a Python-based tool for managing and organizing photo collections by identifying and reporting duplicate images. It features a terminal user interface (TUI) for easy setup and configuration, supports advanced metadata analysis, and can be scheduled to run automatically.

---

## Table of Contents

- [PhotoChomper](#photochomper)
  - [Table of Contents](#table-of-contents)
  - [1. Platform \& Performance](#1-platform--performance)
  - [2. Duplicate Detection Features](#2-duplicate-detection-features)
  - [3. Duplicate Handling \& Actions](#3-duplicate-handling--actions)
    - [Options for Duplicate Handling](#options-for-duplicate-handling)
    - [Reporting and Exporting](#reporting-and-exporting)
    - [Custom Reports and Alerts](#custom-reports-and-alerts)
    - [Notifications](#notifications)
    - [User Interface](#user-interface)
    - [Configuration](#configuration)
    - [Scheduling](#scheduling)
    - [Setup](#setup)
    - [Help](#help)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Interactive Setup](#interactive-setup)
    - [Run Duplicate Search](#run-duplicate-search)
    - [Schedule Repeated Searches](#schedule-repeated-searches)
    - [Specify Config Directory/File](#specify-config-directoryfile)
  - [Troubleshooting](#troubleshooting)
  - [Acknowledgements](#acknowledgements)
  - [Versioning](#versioning)
  - [License](#license)
  - [Contact](#contact)
  - [Credits](#credits)
  - [FAQ](#faq)
  - [Updates](#updates)
  - [Disclaimer](#disclaimer)
  - [TODO](#todo)

---

## 1. Platform & Performance

- **Cross-platform:** Works on Windows, macOS, and Linux.
- **Efficient scanning:** Recursively scans directories for images and videos.
- **Multi-threaded hashing:** Fast duplicate detection using SHA-256.

## 2. Duplicate Detection Features

- **File content hashing:** Finds exact duplicates using SHA-256.
- **Metadata analysis:** Considers file size, creation/modification dates, IPTC and XMP tags.
- **Configurable similarity threshold:** (default: exact match).
- **Flexible file type support:** JPG, PNG, GIF, BMP, TIFF, and more.

## 3. Duplicate Handling & Actions

### Options for Duplicate Handling

- **Master selection:** Choose master by filename length, path length, or modification date.
- **Exclude directories:** Easily skip folders you don't want scanned.

### Reporting and Exporting

- **CSV & JSON reports:** Detailed exports with all relevant metadata.
- **Custom output file names:** Optionally include date/time in report names.
- **Log file:** Tracks actions, config used, output files, and execution time.

### Custom Reports and Alerts

- **Rich metadata:** Reports include IPTC/XMP tags, file attributes, and reasons for duplicate detection.

### Notifications

- **Terminal notifications:** Clear progress and summary output.

### User Interface

- **TUI setup:** Interactive configuration with sensible defaults.
- **Command-line options:** Easy to run and schedule searches.

### Configuration

- **Config file management:** Save/load multiple configurations, choose config interactively if more than one exists.

### Scheduling

- **Automated scans:** Schedule duplicate searches at regular intervals.

### Setup

- **Interactive setup:** Guided prompts for all options, with defaults.

### Help

- **Usage instructions:** Shown if no arguments are provided.

---

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/photochomper.git
   cd photochomper/photochomper
   ```

2. **Install dependencies using [uv](https://github.com/astral-sh/uv):**
   ```sh
   uv pip install -r requirements.txt
   ```
   *Recommended: `iptcinfo3`, `python-xmp-toolkit`, `rich`*

---

## Usage

### Interactive Setup

```sh
uv pip install -r requirements.txt  # If not already done
python main.py --setup
```
Follow the prompts to configure directories, file types, and output options.

### Run Duplicate Search

```sh
python main.py --search
```

### Schedule Repeated Searches

```sh
python main.py --schedule 1
```
(Runs every 1 hour)

### Specify Config Directory/File

```sh
python main.py --configdir "path/to/configs" --config "photochomper_config_YYYYMMDD_HHMMSS.json"
```

---

## Troubleshooting

- If the program runs without error but produces no output, ensure you provided a valid command-line argument (`--setup`, `--search`, or `--schedule`).
- If multiple config files exist, you will be prompted to choose one.
- Check `photochomper.log` for details on actions, config used, and output files.

---

## Acknowledgements

- [Rich](https://github.com/Textualize/rich) for TUI
- [iptcinfo3](https://github.com/jamesacampbell/iptcinfo3) for IPTC support
- [python-xmp-toolkit](https://github.com/python-xmp-toolkit/python-xmp-toolkit) for XMP support

---

## Versioning

- See [Changelog](#changelog) for updates.

---

## License

MIT License

---

## Contact

For questions, feedback, or support, open an issue or contact the maintainer.

---

## Credits

PhotoChomper by [Your Name or Organization]

---

## FAQ

**Q:** What image types are supported?  
**A:** JPG, PNG, GIF, BMP, TIFF, and more.

**Q:** Can I run this on my NAS or external drive?  
**A:** Yes, just specify the directory in setup.

---

## Updates

See [Release Notes](#release-notes) for the latest features and fixes.

---

## Disclaimer

PhotoChomper is provided as-is. Always review duplicates before deleting

---

## TODO

PhotoChomper is actively being developed. The following features and requirements from the [requirements](docs/requirements.md) are not yet fully implemented:

- **Advanced Duplicate Detection**
  - Perceptual hashing (phash, dhash, image similarity for near-duplicates)
  - Video file hashing and metadata extraction
  - Advanced image comparison algorithms for different formats

- **Metadata Extraction**
  - Full EXIF, GPS, camera model, lens, and software metadata extraction and comparison

- **Image Quality Analysis**
  - Metrics such as resolution, sharpness, color balance, Laplacian variance, Radon transform

- **Custom Actions & Tagging**
  - Tag, rate, rename, or move duplicates via TUI
  - Custom rules for handling duplicates

- **Batch Processing**
  - Batch delete/move/tag actions with confirmation and backup
  - Import actions from exported reports

- **Reporting & Logging**
  - More attributes in reports (dimensions, EXIF, GPS, software, etc.)
  - Custom and summary reports based on user criteria
  - More detailed logging of actions and errors

- **Notifications & Alerts**
  - Desktop notifications or email alerts for duplicate events

- **Localization**
  - Support for multiple languages in TUI and reports

- **Scheduling**
  - Integration with OS schedulers (Windows Task Scheduler, cron) for background scans

- **User Documentation**
  - Comprehensive user and troubleshooting guides
  - In-app help section in TUI

- **Unit Testing**
  - Unit tests for all major functions

- **Performance**
  - Multi-threading/multiprocessing for scanning and hashing large directories
  - Optimized file I/O and hashing

- **Configuration**
  - Saving/loading multiple configurations
  - Exclusion/inclusion by keywords in directory names
  - Custom rules for identifying duplicates

- **Security & Privacy**
  - Ensure no personal data is stored or reported
  - Clear privacy information in documentation

- **Other**
  - Tagging images for categorization

---

*See [requirements.md](docs/requirements.md) for the full specification