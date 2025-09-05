# PhotoChomper Changelog

All notable changes to PhotoChomper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.7] - 2025-09-05

### Added
- **HEIF/HEIC File Support**: Integrated `pillow-heif` for comprehensive HEIF and HEIC image format support
  - Automatic registration of HEIF opener when pillow-heif is available
  - Graceful fallback when library is not installed
  - Support for Apple's HEIC format commonly used in iOS devices
- **Enhanced Error Suppression**: New `suppress_stdout_stderr()` context manager
  - Silences noisy library output during metadata extraction
  - Prevents console spam from third-party libraries
  - Improves user experience during large batch operations
- **Extended File Type Support**: Added support for additional image and video formats
  - Enhanced default file type detection
  - Better handling of RAW camera formats

### Fixed
- **Metadata Extraction Improvements**: Enhanced IPTC metadata handling
  - Fixed dictionary access patterns for IPTCInfo3
  - Improved error handling for corrupted metadata
  - More robust extraction of keywords, captions, and copyright info
- **Code Organization**: Added extensive documentation and comments throughout scanner.py
  - Clearer function documentation
  - Better import organization
  - Improved maintainability for future development

### Changed
- **pyproject.toml**: Added pillow-heif>=1.1.0 to dependencies
- **Scanner Architecture**: Improved error handling and logging throughout hash computation
- **Import Structure**: Better organization of optional dependencies with fallback handling

### Technical Details
- Duplicate HEIF registration calls removed for cleaner code
- Enhanced type safety in metadata extraction functions
- Improved memory management during large file processing
- Better error logging for debugging persistent hashing issues

## [3.1.6] - 2025-09-05

### Fixed
- **Critical HashCache Comparison Error**: Resolved `'<' not supported between instances of 'HashCache' and 'int'`
  - Added comprehensive type validation in HashCache.get_cached_hash method
  - Enhanced exception handling with proper error logging
  - Implemented graceful fallbacks for data corruption scenarios
- **Database Safety**: Improved handling of corrupted database data
  - Type validation before numeric comparisons
  - Graceful handling of invalid file stat data
  - Better error recovery mechanisms

### Added
- **Comprehensive Test Suite**: Created test_v3.1.6_hashcache_type_validation.py
  - Type validation testing for cached data
  - Corrupted database handling tests  
  - Performance regression testing
  - Exception handling validation
- **Performance Monitoring**: Established v3.1.6 performance baselines

### Technical Details
- Enhanced get_cached_hash method with type safety checks
- Added validation for file_size, file_mtime, cached_size, and cached_mtime types
- Implemented proper error logging for type validation failures
- Created comprehensive regression test framework

## [3.1.5] - 2025-09-05

### Fixed
- **HashCache Comparison Error**: Resolved critical error where HashCache objects were being used in comparison operations causing `'<' not supported between instances of 'HashCache' and 'int'`
- **Type Safety**: Enhanced type checking and validation in hash cache operations
- **Error Handling**: Improved error handling analysis and reporting in TODO.md

### Added
- **Comprehensive Testing Framework**: Implemented version-specific testing infrastructure
  - Version-specific test scripts for each release
  - Regression test suites to prevent rollback of fixes
  - Automated test runner with selective execution
  - Performance baseline monitoring and regression detection
- **Testing Standards**: Established mandatory testing requirements for all future versions
- **Documentation Updates**: Enhanced CLAUDE.md with testing guidelines and examples

### Changed
- **TODO.md**: Replaced raw error logs with comprehensive analysis and structured information
- **Testing Process**: All version increments now require persistent test scripts and regression validation
- **Quality Assurance**: 100% test coverage requirement for version releases

### Technical Details
- Created `tests/version_tests/test_v3.1.5_hashcache_comparison.py` with 7 comprehensive tests
- Created `tests/regression/regression_suite_v3.1.5.py` validating all previous version fixes
- Implemented `tests/run_all_version_tests.py` for automated test execution
- Established performance baseline system in `tests/benchmarks/`
- Added detailed test logging to `tests/logs/`

## [3.1.4] - Previous Release

### Fixed
- Critical SQLite thread safety issues
- Improved ffmpeg error handling

## [3.1.3] - Previous Release

### Updated
- README table of contents to reflect all enhanced features and sections

## [3.1.2] - Previous Release

### Added
- Enhanced README with comprehensive UV + PyInstaller Windows executable build instructions

## [3.1.1] - Previous Release

### Updated
- README with enhanced features documentation and version tracking system

## [3.1.0] - Previous Release

### Added
- Enhanced progress tracking with real-time feedback
- Time estimation and ETA calculations
- Configurable chunking with memory-based optimization
- Skip SHA256 option for specialized workflows
- Enhanced TUI with system memory analysis

### Changed
- Progress monitoring with visual indicators for each phase
- Memory optimization with adaptive chunking strategies
- Configuration system with improved user experience

## [3.0.0] - Performance Revolution

### Added
- **Revolutionary Performance Optimizations**:
  - Two-stage detection: SHA256 exact duplicates → perceptual similarity
  - LSH optimization reducing O(n²) to ~O(n log n) comparisons
  - Progressive similarity thresholds (coarse → fine filtering)
  - SQLite persistent caching with 90%+ speedup on repeated runs
  - Memory-conscious design with stable <2GB usage

### Changed
- **Processing Architecture**: Complete rewrite of duplicate detection algorithms
- **Memory Management**: Adaptive chunking prevents overflow regardless of collection size
- **Performance**: 555x speedup for 200K files (hours → minutes)

## [2.0.0] - Enhanced User Experience

### Added
- Always-on SHA256 hash calculation alongside similarity algorithms
- Enhanced review interface with row numbers and comprehensive metadata
- Selective file action system (choose specific files by row numbers)
- Smart directory memory for move operations
- Improved setup with better defaults display
- Advanced similarity scoring with detailed explanations

### Changed
- User interface significantly enhanced for better usability
- File action system redesigned for more precise control
- Configuration system improved with better validation

## [1.0.0] - Initial Release

### Added
- Basic duplicate detection functionality
- Core scanning and reporting capabilities
- Initial version of interactive review system
- Basic configuration management

---

## Testing History

### v3.1.5 Testing Implementation
- **Test Coverage**: 100% (14/14 tests passed)
- **Version-Specific Tests**: 7 tests validating HashCache comparison fix
- **Regression Tests**: 7 tests ensuring all previous fixes remain functional
- **Performance Baseline**: Established for cache operations
- **Testing Infrastructure**: Complete framework implemented for future versions

### Testing Standards (Established v3.1.5)
- Every version increment MUST include persistent test scripts
- Comprehensive regression testing required before release
- Performance baseline monitoring to detect regressions
- Automated test execution with detailed reporting
- 100% pass rate required for version completion

---

## Development Notes

### Version Numbering
- **MAJOR**: Breaking changes or major architecture changes
- **MINOR**: New features, enhancements, or significant improvements  
- **PATCH**: Bug fixes, small improvements, or maintenance updates

### Release Process (Established v3.1.5)
1. Implement fix or feature
2. Create version-specific test script
3. Update regression test suite
4. Run comprehensive test validation
5. Update version number and changelog
6. Update documentation
7. Validate all changes with test suite

### Quality Assurance
- All releases must pass 100% of tests
- Previous version functionality must be preserved
- Performance regressions are not acceptable
- Documentation must be updated with each release