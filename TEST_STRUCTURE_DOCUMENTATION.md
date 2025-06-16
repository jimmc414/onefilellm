# OneFileLLM Test Structure Documentation
**Created by Claude 4 - 2025-06-16**

## Critical Discovery: Test File Locations

During the test execution process, I discovered that the test files are organized in a non-standard way that can cause confusion. This document serves to properly document the actual test structure to prevent future issues.

## Actual Test File Locations

### 1. Unit Tests
- **Location**: `/tests/test_all.py`
- **Description**: Main unit test suite with 75 tests covering core functionality
- **Status**: ✅ All tests passing (74 passed, 1 skipped)

### 2. Recorded Test Files (Snapshot Tests)
- **Location**: `/tests/tests/test_recorded_*.py`
- **Count**: 178 recorded test files
- **Note**: These are in a nested `tests/tests/` directory, NOT in the root `tests/` directory

### 3. Snapshot Files
- **Location**: `/tests/snapshots/`
- **Description**: Contains expected output snapshots for recorded tests
- **Files**: Include various .txt files like:
  - alias_*.txt (alias system tests)
  - arxiv_*.txt (ArXiv integration tests)
  - complex_*.txt (complex integration tests)
  - crawl_*.txt (web crawling tests)
  - dir_*.txt (directory tests)
  - format_*.txt (format detection tests)
  - github_*.txt (GitHub integration tests)
  - local_*.txt (local file tests)
  - web_*.txt (web scraping tests)

### 4. Test Infrastructure Files
- **harness_claude1.py**: Located in parent `/tests/` directory (not in worktree by default)
- **conftest.py**: Pytest configuration (may need to be created in worktree)
- **run_all_tests.py**: Missing from repository (referenced but doesn't exist)

## Running Tests Correctly

### From Worktree
```bash
# Unit tests
python tests/test_all.py

# Recorded tests (if copied to worktree)
cd tests/tests/
python -m pytest test_recorded_*.py -v

# Or from worktree root
python -m pytest tests/tests/test_recorded_*.py -v
```

### Environment Variables
```bash
# Set to avoid GitHub token warnings
export GITHUB_TOKEN="dummy-token-for-testing"

# For integration tests
export RUN_INTEGRATION_TESTS="true"

# For slow tests
export RUN_SLOW_TESTS="true"
```

## Issues Found

1. **Nested Directory Structure**: The `tests/tests/` nesting is confusing and non-standard
2. **Missing run_all_tests.py**: Referenced in documentation but doesn't exist
3. **Worktree Isolation**: Test files don't automatically appear in git worktrees - the `tests/tests/` directory exists but is empty in worktrees
4. **Snapshot Paths**: Tests may fail in worktrees due to different relative paths
5. **Git Tracking**: The recorded test files appear to not be tracked in git, which is why they don't appear in worktrees

## Recommendations

1. **Flatten Test Structure**: Move files from `tests/tests/` to `tests/`
2. **Create run_all_tests.py**: Implement the missing test orchestration script
3. **Update Documentation**: Fix references to test file locations
4. **Worktree Setup Script**: Create a script to properly set up test environment in worktrees
5. **Path Independence**: Make tests work regardless of execution directory

## Test Categories

Based on file analysis, the recorded tests cover:

1. **Alias System**: 11 test files
2. **ArXiv Integration**: 3 test files
3. **Complex Scenarios**: 5 test files
4. **Web Crawling**: 7 test files
5. **Directory Processing**: 9 test files
6. **DOI/PMID**: 2 test files
7. **Error Handling**: 4 test files
8. **File Format Detection**: 5 test files
9. **GitHub Integration**: 24 test files
10. **Help System**: 4 test files
11. **Local File Processing**: 10 test files
12. **Multi-Input**: 3 test files
13. **Stdin Processing**: 8 test files
14. **Web Scraping**: 9 test files
15. **YouTube Integration**: 1 test file
16. **Test Runner**: 8 test files

This documentation should help prevent confusion about test locations in future development work.