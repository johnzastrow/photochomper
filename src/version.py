"""
PhotoChomper version tracking.

Version numbering follows semantic versioning: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major architecture changes
- MINOR: New features, enhancements, or significant improvements
- PATCH: Bug fixes, small improvements, or maintenance updates

Current version reflects the enhanced v3.0+ features with:
- Advanced progress tracking and time estimation
- Intelligent memory-based chunking
- SHA256 skip option
- Enhanced TUI with real-time feedback
- LSH-optimized similarity detection
"""

__version__ = "3.1.3"
__version_info__ = (3, 1, 3)

# Version history tracking
VERSION_HISTORY = [
    "3.1.3 - Updated README table of contents to reflect all enhanced features and sections",
    "3.1.2 - Enhanced README with comprehensive UV + PyInstaller Windows executable build instructions",
    "3.1.1 - Updated README with enhanced features documentation and version tracking system", 
    "3.1.0 - Enhanced progress tracking, time estimation, and configurable chunking",
    "3.0.0 - Revolutionary performance optimizations with LSH and two-stage detection",
    "2.0.0 - Enhanced user experience with advanced TUI and selective file actions",
    "1.0.0 - Initial release with basic duplicate detection"
]

def get_version() -> str:
    """Get the current version string."""
    return __version__

def get_version_info() -> tuple:
    """Get version as a tuple for programmatic comparison."""
    return __version_info__

def get_version_history() -> list:
    """Get the version history."""
    return VERSION_HISTORY

def print_version_info():
    """Print detailed version information."""
    print(f"PhotoChomper v{__version__}")
    print("High-performance duplicate photo detection and management")
    print(f"Current version: {__version__}")
    print("\nVersion History:")
    for version in VERSION_HISTORY:
        print(f"  • {version}")