# OneFileLLM Test Runner Usage Patterns

This document provides common usage patterns and examples for the unified test runner.

## Basic Usage Patterns

### Running All Tests

```bash
# Run all tests with default settings
python tests/run_all_tests.py

# Run all tests with verbose output
python tests/run_all_tests.py --verbose

# Run all tests quietly (minimal output)
python tests/run_all_tests.py --quiet
```

### Framework-Specific Testing

```bash
# Run only unittest tests
python tests/run_all_tests.py --framework unittest

# Run only pytest tests
python tests/run_all_tests.py --framework pytest

# Run specific test file
python tests/run_all_tests.py tests/test_all.py
```

### Integration and Slow Tests

```bash
# Run with integration tests (requires network)
python tests/run_all_tests.py --integration

# Run slow tests (comprehensive crawling, large files)
python tests/run_all_tests.py --slow

# Run everything
python tests/run_all_tests.py --integration --slow
```

### Output Formats

```bash
# Default Rich formatted output
python tests/run_all_tests.py

# Plain text output (good for CI)
python tests/run_all_tests.py --output-format plain

# JSON output (for programmatic processing)
python tests/run_all_tests.py --output-format json > results.json

# JUnit XML output (for CI integration)
python tests/run_all_tests.py --output-format junit > results.xml
```

### Performance Testing

```bash
# Run tests in parallel (requires pytest-xdist)
python tests/run_all_tests.py --parallel

# Run with specific number of workers
python tests/run_all_tests.py --parallel --workers 4

# Time individual test execution
python tests/run_all_tests.py --verbose --output-format plain | grep "duration"
```

### Snapshot Testing

```bash
# Run pytest with snapshot testing
python tests/run_all_tests.py --framework pytest

# Update snapshots when output changes are expected
python tests/run_all_tests.py --framework pytest --snapshot-update
```

## Advanced Patterns

### Custom Test Selection

```bash
# Run specific test class
python -m unittest tests.test_all.TestUtilityFunctions

# Run specific test method
python -m unittest tests.test_all.TestUtilityFunctions.test_safe_file_read

# Run tests matching pattern
pytest tests/ -k "github" -v
```

### Environment Configuration

```bash
# Set GitHub token for API tests
export GITHUB_TOKEN=your_token_here
python tests/run_all_tests.py --integration

# Enable integration tests by default
export RUN_INTEGRATION_TESTS=true
python tests/run_all_tests.py

# Set custom verbosity
export TEST_VERBOSITY=3
python tests/run_all_tests.py
```

### Debugging Failed Tests

```bash
# Run with Python debugger
python -m pdb tests/run_all_tests.py

# Run specific failing test with verbose output
python tests/run_all_tests.py --framework unittest --verbose 2>&1 | grep -A 10 "FAIL"

# Generate detailed error report
python tests/run_all_tests.py --output-format json | python -m json.tool | grep -A 5 "failed"
```

### Coverage Analysis

```bash
# Run with coverage measurement
coverage run tests/run_all_tests.py
coverage report
coverage html

# Run specific framework with coverage
coverage run tests/run_all_tests.py --framework unittest
coverage report --include="onefilellm.py,utils.py"

# Generate coverage badge
coverage-badge -o coverage.svg
```

## CI/CD Integration Patterns

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running tests..."
python tests/run_all_tests.py --framework unittest --quiet
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

### Docker Testing

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements*.txt ./
RUN pip install -r requirements.txt -r requirements-test.txt

COPY . .
CMD ["python", "tests/run_all_tests.py", "--output-format", "plain"]
```

### Makefile Integration

```makefile
.PHONY: test test-unit test-integration test-all

test:
	python tests/run_all_tests.py

test-unit:
	python tests/run_all_tests.py --framework unittest

test-integration:
	python tests/run_all_tests.py --integration --slow

test-all: test-unit test-integration

test-coverage:
	coverage run tests/run_all_tests.py
	coverage report
	coverage html
```

## Troubleshooting Common Issues

### Import Errors

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt
pip install -r requirements-test.txt

# Check Python path
python -c "import sys; print(sys.path)"

# Run from project root
cd /path/to/onefilellm
python tests/run_all_tests.py
```

### Snapshot Mismatches

```bash
# View snapshot differences
pytest tests/test_recorded_*.py --snapshot-update --diff

# Update specific snapshots
pytest tests/test_recorded_github_onefilellm.py --snapshot-update

# Clear snapshot cache
rm -rf tests/snapshots/.pytest_cache
```

### Performance Issues

```bash
# Profile test execution
python -m cProfile -s cumulative tests/run_all_tests.py > profile.txt

# Run subset of tests
python tests/run_all_tests.py --framework unittest --pattern "test_util*"

# Skip slow tests
python tests/run_all_tests.py --no-slow
```

## Best Practices

1. **Regular Testing**: Run tests before committing changes
2. **Incremental Testing**: Test specific components during development
3. **CI Integration**: Always run full test suite in CI pipeline
4. **Coverage Goals**: Maintain >80% code coverage
5. **Snapshot Management**: Review snapshot changes carefully
6. **Performance Monitoring**: Track test execution time trends
7. **Environment Isolation**: Use virtual environments for testing