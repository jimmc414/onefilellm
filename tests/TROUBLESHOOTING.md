# OneFileLLM Test Suite Troubleshooting Guide

## Common Issues and Solutions

### 1. Import Errors

#### Problem: "ModuleNotFoundError: No module named 'pytest'"
**Solution:**
```bash
pip install -r requirements-test.txt
```

#### Problem: "ImportError: cannot import name 'process_github_repo'"
**Solution:**
Make sure you're running tests from the project root:
```bash
cd /path/to/onefilellm
python tests/run_all_tests.py
```

#### Problem: "No module named 'tests.test_runner_config'"
**Solution:**
The test runner files are missing. Ensure all these files exist:
- `tests/test_runner_config.py`
- `tests/test_runner_core.py`
- `tests/unittest_integration.py`
- `tests/pytest_integration.py`

### 2. Test Failures

#### Problem: Snapshot tests failing with differences
**Symptoms:**
```
AssertionError: Snapshot differs from actual output
```

**Solutions:**
1. Review the differences - are they expected?
2. If changes are intentional, update snapshots:
   ```bash
   pytest tests/test_recorded_*.py --snapshot-update
   ```
3. If unexpected, investigate what changed in the code

#### Problem: Network-related test failures
**Symptoms:**
- Timeouts
- Connection errors
- 404 errors for external resources

**Solutions:**
1. Check your internet connection
2. Verify external services are accessible
3. Skip integration tests if offline:
   ```bash
   python tests/run_all_tests.py --framework unittest
   ```

#### Problem: GitHub API rate limiting
**Symptoms:**
```
Error: API rate limit exceeded
```

**Solutions:**
1. Set a GitHub token:
   ```bash
   export GITHUB_TOKEN=your_personal_access_token
   python tests/run_all_tests.py --integration
   ```
2. Wait for rate limit to reset (usually 1 hour)
3. Run tests without integration:
   ```bash
   python tests/run_all_tests.py
   ```

### 3. Environment Issues

#### Problem: Tests pass locally but fail in CI
**Common Causes:**
- Different Python versions
- Missing environment variables
- Platform-specific behavior

**Solutions:**
1. Test with the same Python version as CI:
   ```bash
   python3.11 tests/run_all_tests.py
   ```
2. Set required environment variables:
   ```bash
   export CI=true
   export NO_COLOR=1
   python tests/run_all_tests.py --output-format plain
   ```
3. Use Docker to replicate CI environment

#### Problem: Clipboard tests failing
**Symptoms:**
```
pyperclip.PyperclipException: Could not find a copy/paste mechanism
```

**Solutions:**
1. Install clipboard dependencies:
   - Linux: `sudo apt-get install xclip`
   - macOS: Should work out of the box
   - Windows: Should work out of the box
2. Run in headless mode:
   ```bash
   export DISPLAY=:0  # Linux only
   ```
3. Skip clipboard tests if running headless

### 4. Performance Issues

#### Problem: Tests running very slowly
**Solutions:**
1. Run tests in parallel:
   ```bash
   pip install pytest-xdist
   python tests/run_all_tests.py --parallel
   ```
2. Skip slow tests:
   ```bash
   python tests/run_all_tests.py  # Skips slow tests by default
   ```
3. Run only specific test framework:
   ```bash
   python tests/run_all_tests.py --framework unittest
   ```

#### Problem: Tests timing out
**Solutions:**
1. Increase timeout for specific tests
2. Check for infinite loops or deadlocks
3. Skip integration tests if network is slow

### 5. Platform-Specific Issues

#### Windows
**Problem:** Path-related test failures
**Solution:** The tests handle path normalization, but ensure you're using:
```python
from pathlib import Path
# Instead of hardcoded forward/backward slashes
```

#### macOS
**Problem:** SSL certificate errors
**Solution:**
```bash
pip install --upgrade certifi
```

#### Linux/WSL
**Problem:** Permission errors
**Solution:**
```bash
# Fix permissions
chmod +x onefilellm.py
# Or run with proper permissions
sudo python tests/run_all_tests.py
```

### 6. Test Runner Issues

#### Problem: "Rich library not available"
**Solution:**
```bash
pip install rich
# Or use plain output
python tests/run_all_tests.py --output-format plain
```

#### Problem: JSON output is malformed
**Solution:**
Ensure no print statements in test code are corrupting JSON output

### 7. Debugging Techniques

#### Enable Maximum Verbosity
```bash
python tests/run_all_tests.py -vvv
```

#### Run Single Test File
```bash
# Pytest
pytest tests/test_recorded_github_onefilellm.py -v -s

# Unittest
python -m unittest tests.test_all.TestUtilityFunctions -v
```

#### Use Python Debugger
```python
import pdb; pdb.set_trace()  # Add to test code
```

#### Check Test Logs
```bash
# Run with output capture disabled
pytest tests/test_recorded_*.py -s
```

### 8. Common Error Messages

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `FileNotFoundError` | Missing test data | Ensure `tests/test_data/` exists |
| `KeyError: 'GITHUB_TOKEN'` | Missing env var | Set `GITHUB_TOKEN` or skip integration tests |
| `AssertionError: Output should not be empty` | Command failed silently | Check stderr output, run with `-vv` |
| `subprocess.TimeoutExpired` | Long-running operation | Increase timeout or optimize code |
| `PermissionError` | File access issues | Check file permissions |

### 9. Getting Help

1. **Check Documentation**
   - `tests/readme.md` - Comprehensive test documentation
   - `tests/QUICKSTART.md` - Getting started guide
   - `CLAUDE.md` - Project conventions

2. **Review Test Output**
   - Run with `-vv` for detailed output
   - Check both stdout and stderr
   - Look for traceback details

3. **Isolate the Problem**
   - Run failing test in isolation
   - Disable parallel execution
   - Use plain output format

4. **Report Issues**
   - Include full error message
   - Specify Python version and OS
   - Provide steps to reproduce

### Quick Fixes Checklist

- [ ] All dependencies installed? `pip install -r requirements.txt -r requirements-test.txt`
- [ ] Running from project root? `cd /path/to/onefilellm`
- [ ] Python 3.8 or higher? `python --version`
- [ ] Internet connection for integration tests?
- [ ] GitHub token set if running integration tests?
- [ ] Correct test command? `python tests/run_all_tests.py`

### Emergency Recovery

If nothing works:
```bash
# Clean install
rm -rf venv
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt -r requirements-test.txt

# Run minimal test
python tests/test_all.py --quiet

# If that works, try the full suite
python tests/run_all_tests.py
```