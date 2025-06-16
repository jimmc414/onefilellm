# OneFileLLM Test Infrastructure Quick Start Guide

## Overview

Welcome to the OneFileLLM test infrastructure! This guide will help you get started with running and understanding our comprehensive test suite.

## Prerequisites

1. **Python 3.8+** installed
2. **Clone the repository** with OneFileLLM
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests - The Easy Way

### Run All Tests (Recommended)
```bash
python tests/run_all_tests.py
```

This runs both unittest and pytest suites with beautiful Rich formatting.

### Run Specific Test Framework
```bash
# Run only unittest tests
python tests/run_all_tests.py --framework unittest

# Run only pytest recorded tests
python tests/run_all_tests.py --framework pytest
```

### Run with Different Output Formats
```bash
# Plain text output (good for CI/CD)
python tests/run_all_tests.py --output-format plain

# JSON output (for parsing)
python tests/run_all_tests.py --output-format json
```

## Understanding the Test Structure

### Two Test Suites

1. **Manual Tests** (`test_all.py`)
   - 57+ hand-written unit tests
   - Tests core functionality
   - Uses Python's unittest framework

2. **Recorded Tests** (`test_recorded_*.py`)
   - 119 auto-generated tests
   - Captures real command executions
   - Uses pytest with snapshot testing

### Test Categories

- **Utility Functions**: File I/O, format detection
- **Stream Processing**: stdin, clipboard handling
- **Core Processing**: Local files, directories
- **GitHub Integration**: Repos, issues, PRs
- **Web Crawling**: Advanced web scraping
- **Alias System**: Command shortcuts
- **Error Handling**: Edge cases, failures

## Common Tasks

### Update Test Snapshots
When output format changes:
```bash
python tests/run_all_tests.py --framework pytest --snapshot-update
```

### Run Integration Tests
Tests that require network access:
```bash
python tests/run_all_tests.py --integration
```

### Run Tests in Parallel
Faster execution (requires pytest-xdist):
```bash
pip install pytest-xdist
python tests/run_all_tests.py --parallel
```

### Debug a Failing Test
```bash
# Run with verbose output
python tests/run_all_tests.py -vv

# Run specific test file
pytest tests/test_recorded_github_onefilellm.py -v

# Run specific test class
python -m unittest tests.test_all.TestUtilityFunctions
```

## Environment Variables

```bash
# Enable integration tests by default
export RUN_INTEGRATION_TESTS=true

# Enable slow tests
export RUN_SLOW_TESTS=true

# Set GitHub token for API tests
export GITHUB_TOKEN=your_token_here
```

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the project root
cd /path/to/onefilellm

# Install test dependencies
pip install pytest pytest-snapshot
```

### Test Failures
1. Check if it's an environment issue (network, permissions)
2. Review the error message and traceback
3. Run the specific test in isolation
4. Check test documentation in `tests/readme.md`

### Snapshot Mismatches
```bash
# Update snapshots if output format changed intentionally
pytest tests/test_recorded_*.py --snapshot-update
```

## Test Development

### Adding a New Unit Test
Edit `tests/test_all.py` and add to appropriate class:
```python
def test_my_new_feature(self):
    """Test description"""
    result = my_function()
    self.assertEqual(result, expected)
```

### Recording a New Test
Use the recording system (see `TEST_RECORDING_QUICKSTART.md`)

## CI/CD Integration

The test suite is designed for CI/CD:
- Exit code 0 = all tests passed
- Exit code 1 = test failures
- Supports multiple output formats
- Can run in headless environments

## Need Help?

1. Check `tests/readme.md` for detailed documentation
2. Review existing tests for examples
3. Ask the team - we're here to help!

## Quick Reference

```bash
# Most common commands
python tests/run_all_tests.py              # Run everything
python tests/run_all_tests.py --quiet       # Minimal output
python tests/run_all_tests.py --integration # Include network tests
python tests/run_all_tests.py --help        # See all options
```

Happy testing! 🚀