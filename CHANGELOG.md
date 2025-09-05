# PhotoChomper Changelog

All notable changes to PhotoChomper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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