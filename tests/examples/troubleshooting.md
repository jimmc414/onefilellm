# OneFileLLM Test Runner Troubleshooting Guide

This guide helps resolve common issues when running the OneFileLLM test suite.

## Common Issues and Solutions

### 1. Import Errors

#### Problem: `ModuleNotFoundError: No module named 'pytest'`

**Solution:**
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or install pytest directly
pip install pytest pytest-snapshot pytest-xdist
```

#### Problem: `ImportError: cannot import name 'TestRunner' from 'test_runner_core'`

**Solution:**
```bash
# Ensure you're in the project root
cd /path/to/onefilellm

# Run with proper Python path
PYTHONPATH=. python tests/run_all_tests.py
```

### 2. Test Discovery Issues

#### Problem: No tests are discovered

**Solution:**
```bash
# Check test file locations
ls tests/test*.py

# Verify test file naming
# Unittest: test_*.py or *_test.py
# Pytest: test_*.py or *_test.py

# Run discovery manually
python -m unittest discover tests/
pytest --collect-only tests/
```

#### Problem: Specific tests not found

**Solution:**
```bash
# Use full module path
python -m unittest tests.test_all.TestUtilityFunctions

# For pytest, use -k flag
pytest tests/ -k "test_safe_file_read"
```

### 3. Environment Issues

#### Problem: Tests fail due to missing environment variables

**Solution:**
```bash
# Set required environment variables
export GITHUB_TOKEN="your_token_here"
export RUN_INTEGRATION_TESTS=true

# Or use .env file
echo "GITHUB_TOKEN=your_token_here" > .env
python tests/run_all_tests.py
```

#### Problem: Clipboard tests fail in headless environment

**Solution:**
```bash
# Install clipboard backend for Linux
sudo apt-get install xclip

# Or mock clipboard in tests
export MOCK_CLIPBOARD=true
python tests/run_all_tests.py
```

### 4. Network-Related Failures

#### Problem: Integration tests fail with connection errors

**Solution:**
```bash
# Check network connectivity
ping github.com

# Run without integration tests
python tests/run_all_tests.py --no-integration

# Use proxy if needed
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
python tests/run_all_tests.py --integration
```

#### Problem: GitHub API rate limit exceeded

**Solution:**
```bash
# Use authenticated requests
export GITHUB_TOKEN="your_personal_access_token"

# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

### 5. Snapshot Test Failures

#### Problem: Snapshot mismatches in recorded tests

**Solution:**
```bash
# View differences
pytest tests/test_recorded_*.py -vv

# Update snapshots if changes are expected
pytest tests/test_recorded_*.py --snapshot-update

# Update specific test snapshots
pytest tests/test_recorded_github_onefilellm.py --snapshot-update
```

#### Problem: Snapshot files missing

**Solution:**
```bash
# Generate initial snapshots
pytest tests/test_recorded_*.py --snapshot-update

# Check snapshot directory
ls tests/snapshots/

# Ensure snapshots are committed to git
git add tests/snapshots/
git commit -m "Add test snapshots"
```

### 6. Performance Issues

#### Problem: Tests run very slowly

**Solution:**
```bash
# Run in parallel
python tests/run_all_tests.py --parallel

# Skip slow tests
python tests/run_all_tests.py --no-slow

# Run specific fast test subset
python tests/run_all_tests.py --framework unittest --pattern "test_util*"
```

#### Problem: Tests timeout

**Solution:**
```bash
# Increase timeout
pytest tests/ --timeout=300

# Or in pytest.ini
echo "[pytest]
timeout = 300" > pytest.ini
```

### 7. Output and Reporting Issues

#### Problem: No output visible

**Solution:**
```bash
# Use verbose mode
python tests/run_all_tests.py --verbose

# Force plain output
python tests/run_all_tests.py --output-format plain

# Check stderr as well
python tests/run_all_tests.py 2>&1
```

#### Problem: Rich formatting broken in CI

**Solution:**
```bash
# Force plain output in CI
python tests/run_all_tests.py --output-format plain

# Or detect CI environment
if [ "$CI" = "true" ]; then
    python tests/run_all_tests.py --output-format plain
else
    python tests/run_all_tests.py
fi
```

### 8. Platform-Specific Issues

#### Problem: Tests fail on Windows

**Solution:**
```bash
# Use cross-platform paths
# Bad: tests/test_all.py
# Good: tests\\test_all.py or Path("tests/test_all.py")

# Handle line ending differences
git config core.autocrlf true
```

#### Problem: Tests fail on macOS

**Solution:**
```bash
# Install required dependencies
brew install python@3.11

# Handle case-sensitive filesystem
# Ensure consistent file naming
```

### 9. Dependency Conflicts

#### Problem: Version conflicts between requirements

**Solution:**
```bash
# Create clean virtual environment
python -m venv test_env
source test_env/bin/activate  # or test_env\\Scripts\\activate on Windows

# Install exact versions
pip install -r requirements.txt
pip install -r requirements-test.txt

# Check for conflicts
pip check
```

### 10. Debugging Failed Tests

#### Enable detailed debugging:
```bash
# Python unittest debug mode
python -m unittest tests.test_all.TestUtilityFunctions -v

# Pytest debug mode
pytest tests/test_all.py::TestUtilityFunctions::test_safe_file_read -vv -s

# Use Python debugger
python -m pdb tests/run_all_tests.py
```

#### Capture test output:
```bash
# Save all output
python tests/run_all_tests.py --verbose > test_output.txt 2>&1

# Filter for errors
python tests/run_all_tests.py 2>&1 | grep -E "(ERROR|FAIL|Exception)"
```

## Getting Help

If you continue to experience issues:

1. Check the [project issues](https://github.com/jimmc414/onefilellm/issues)
2. Review recent commits for breaking changes
3. Ensure you have the latest version
4. Create a minimal reproducible example
5. Include full error messages and environment details when reporting issues

## Environment Information Script

Save this as `debug_env.py` to gather debugging information:

```python
#!/usr/bin/env python3
import sys
import platform
import subprocess
import os

print("=== Environment Debug Info ===")
print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Working Directory: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

print("\n=== Installed Packages ===")
subprocess.run([sys.executable, "-m", "pip", "list"])

print("\n=== Test Discovery ===")
subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "tests/", "--quiet"])

print("\n=== Environment Variables ===")
for key in ['GITHUB_TOKEN', 'RUN_INTEGRATION_TESTS', 'CI']:
    print(f"{key}: {'Set' if os.environ.get(key) else 'Not set'}")
```

Run it with: `python debug_env.py`