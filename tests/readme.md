# OneFileLLM Test Suite Documentation

## Overview

OneFileLLM has a comprehensive test suite with over 176 tests across two testing frameworks:

1. **Original Test Suite** (`test_all.py`): 57+ unit tests using Python's unittest framework
2. **Recorded Test Suite** (`test_recorded_*.py`): 119 auto-generated tests using pytest with snapshot testing
3. **Unified Test Runner** (`run_all_tests.py`): NEW! A unified runner that executes both test suites with consolidated reporting

## Test Categories

### 1. **Utility Functions** (`TestUtilityFunctions`)
- File I/O operations (encoding handling, binary detection)
- File type detection and filtering
- URL utilities (domain checking, depth validation)
- XML escaping

### 2. **Text Format Detection** (`TestTextFormatDetection`)
- Format detection for: plain text, JSON, HTML, Markdown, YAML
- Parser validation for each format
- Error handling for invalid formats

### 3. **Stream Processing** (`TestStreamProcessing`)
- Standard input (stdin) processing
- Clipboard processing
- Format override functionality
- Error handling for empty/invalid inputs

### 4. **Core Processing** (`TestCoreProcessing`)
- Local file and folder processing
- Excel file conversion to Markdown
- Token counting with XML tag stripping
- XML output combination
- Text preprocessing (when NLTK enabled)

### 5. **Alias System** (`TestAliasSystem`)
- Alias detection logic (validates alias naming rules)
- Alias directory management
- Creating aliases with `--add-alias` command
- Creating aliases from clipboard with `--alias-from-clipboard`
- Loading and resolving aliases
- Alias name validation (rejects invalid characters)

### 6. **Integration Tests** (`TestIntegration`)
- GitHub repository processing
- ArXiv PDF downloading
- YouTube transcript fetching
- Web crawling
- *Note: Disabled by default, requires network access*

### 7. **CLI Functionality** (`TestCLIFunctionality`)
- Help message display
- Command-line argument parsing
- Format override via CLI
- Multiple input handling
- Error message formatting

### 8. **Error Handling** (`TestErrorHandling`)
- Invalid file paths
- Invalid URLs
- Empty inputs
- Network errors

### 9. **Performance Tests** (`TestPerformance`)
- Large file handling (1MB+)
- Unicode character support
- Special character handling

### 10. **Recorded Tests** (`test_recorded_*.py`)
The recorded test suite provides comprehensive coverage of real-world scenarios:
- **Alias Operations**: Core aliases, custom aliases, placeholder expansion
- **ArXiv Integration**: Paper fetching, README generation
- **Complex Scenarios**: Multi-source aggregation, Kubernetes/Istio docs
- **Web Crawling**: Django docs, FastAPI docs, respectful crawling
- **Directory Processing**: Various directory structures and exclusions
- **DOI Resolution**: Academic paper fetching
- **Error Handling**: File not found, invalid URLs, permission errors
- **Format Support**: JSON, Markdown, HTML, YAML output formats
- **GitHub Integration**: Repos, issues, PRs, branches
- **Help System**: Command help, topic-specific help
- **Local Files**: Various file types (CSV, JSON, Python, etc.)
- **Multi-Input**: Multiple sources in single command
- **PMID/PubMed**: Medical literature fetching
- **Standard Input**: Various stdin scenarios
- **Web Pages**: API docs, blogs, React docs
- **YouTube**: Transcript extraction

## Running Tests

### Unified Test Runner (Recommended)

The new unified test runner executes both unittest and pytest suites in a single command:

```bash
# Run all tests (both unittest and pytest)
python tests/run_all_tests.py

# Run only unittest suite
python tests/run_all_tests.py --framework unittest

# Run only pytest suite  
python tests/run_all_tests.py --framework pytest

# Run with integration tests
python tests/run_all_tests.py --integration

# Run pytest with snapshot update
python tests/run_all_tests.py --framework pytest --snapshot-update

# Run tests in parallel (requires pytest-xdist)
python tests/run_all_tests.py --parallel

# Output in different formats
python tests/run_all_tests.py --output-format json
python tests/run_all_tests.py --output-format plain

# Show help
python tests/run_all_tests.py --help
```

### Legacy Test Runners

You can still run the test suites individually:

#### Unittest Suite (test_all.py)

```bash
# Run all basic tests (no network required)
python tests/test_all.py

# Run with quiet output
python tests/test_all.py --quiet

# Run with verbose output
python tests/test_all.py --verbose
```

#### Pytest Suite (test_recorded_*.py)

```bash
# Run all recorded tests
pytest tests/test_recorded_*.py

# Update snapshots
pytest tests/test_recorded_*.py --snapshot-update

# Run specific test file
pytest tests/test_recorded_github_onefilellm.py -v
```

### Integration Tests

Integration tests require network access and are disabled by default:

```bash
# Enable integration tests with unified runner
python tests/run_all_tests.py --integration

# Enable slow tests (ArXiv, web crawling)
python tests/run_all_tests.py --slow

# Run all tests including integration
python tests/run_all_tests.py --integration --slow

# With GitHub token for private repo tests
GITHUB_TOKEN=your_token python tests/run_all_tests.py --integration
```

### Test Configuration

The unified test runner supports configuration through environment variables:

```bash
# Set test verbosity
export TEST_VERBOSITY=3

# Enable integration tests by default
export RUN_INTEGRATION_TESTS=true

# Enable slow tests by default  
export RUN_SLOW_TESTS=true

# Set GitHub token for API tests
export GITHUB_TOKEN=your_token_here
```

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token for API tests
- `RUN_INTEGRATION_TESTS=true`: Enable integration tests
- `RUN_SLOW_TESTS=true`: Enable slow-running tests

## Test Statistics

- **Total Tests**: 42
- **Categories**: 9
- **Coverage Areas**:
  - Utility functions: 7 tests
  - Format detection: 2 tests
  - Stream processing: 5 tests
  - Core processing: 6 tests
  - Alias system: 6 tests
  - Integration: 4 tests (skipped by default)
  - CLI: 5 tests
  - Error handling: 4 tests
  - Performance: 3 tests

## Test Consolidation

All tests are now consolidated in a single `test_all.py` file. This replaces the previous multiple test files:
- ~~`test_onefilellm.py`~~ - Merged into `test_all.py`
- ~~`test_stream_processing.py`~~ - Merged into `test_all.py`
- ~~`test_stream_features.py`~~ - Merged into `test_all.py`
- ~~`run_tests.py`~~ - No longer needed

The consolidated file contains all previous functionality plus expanded test coverage.

## Adding New Tests

To add new tests:

1. Identify the appropriate test class based on functionality
2. Add your test method following the naming convention `test_<feature>`
3. Use descriptive docstrings
4. Follow existing patterns for assertions and mocking

Example:
```python
class TestCoreProcessing(unittest.TestCase):
    def test_new_feature(self):
        """Test description of new feature"""
        # Setup
        test_input = "test data"
        
        # Execute
        result = new_feature_function(test_input)
        
        # Assert
        self.assertEqual(result, expected_output)
```

## Alias System Tests

The alias system tests provide comprehensive coverage of the alias functionality:

### test_handle_add_alias
Tests the `--add-alias` command functionality:
- Creates aliases with multiple target URLs
- Verifies alias files are created in the correct directory
- Ensures all targets are properly saved

### test_handle_alias_from_clipboard
Tests the `--alias-from-clipboard` command:
- Mocks clipboard content with multiple URLs (newline-separated)
- Verifies parsing of clipboard content
- Creates alias files from clipboard data
- Handles mixed content (URLs and local paths)

### test_load_alias
Tests alias resolution:
- Creates test alias files
- Loads and returns target URLs
- Verifies correct parsing of alias files

### test_alias_validation
Tests alias name validation rules:
- Rejects names with invalid characters (/, \, ., :)
- Ensures no files are created for invalid names
- Validates error handling

Example test usage:
```python
# Testing alias creation
with patch('onefilellm.ALIAS_DIR', Path(temp_dir)):
    args = ["--add-alias", "myalias", "https://github.com/repo", "https://example.com"]
    result = handle_add_alias(args, console)
    
# Testing clipboard alias
with patch('pyperclip.paste', return_value="https://url1.com\nhttps://url2.com"):
    args = ["--alias-from-clipboard", "clipalias"]
    result = handle_alias_from_clipboard(args, console)
```

## Common Test Patterns

### Mocking External Services
```python
with patch('requests.get') as mock_get:
    mock_get.return_value.text = "mocked response"
    result = function_that_uses_requests()
```

### Testing File Operations
```python
def test_file_operation(self):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
        f.write("test content")
        f.flush()
        result = process_file(f.name)
```

### Testing CLI Commands
```python
stdout, stderr, returncode = self.run_cli(["--help"])
self.assertEqual(returncode, 0)
self.assertIn("Usage:", stdout)
```

## Continuous Integration

The test suite is designed to work in CI environments:
- All basic tests run without network access
- Integration tests can be enabled via environment variables
- Exit codes: 0 for success, 1 for failure
- Compatible with standard Python test runners

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
2. **Clipboard Tests Failing**: Some environments don't support clipboard access (expected)
3. **Integration Tests Failing**: Check network connectivity and API tokens
4. **Token Count Mismatches**: May vary slightly between tiktoken versions

### Debug Mode

For debugging specific tests:
```python
# Run a specific test class
python -m unittest test_all.TestUtilityFunctions

# Run a specific test method
python -m unittest test_all.TestUtilityFunctions.test_safe_file_read
```

## Unified Test Runner Architecture

The unified test runner provides a seamless way to execute both test frameworks:

### Core Components

1. **test_runner_core.py**: Abstract base class and common functionality
   - `TestRunner` ABC for framework-agnostic interface
   - `TestResults` dataclass for unified result format
   - Result aggregation and formatting methods

2. **test_runner_config.py**: Configuration management
   - `TestConfig` dataclass with all test execution options
   - Environment variable support
   - CLI argument integration

3. **unittest_integration.py**: Unittest framework adapter
   - `UnittestRunner` class implementing TestRunner interface
   - Custom result collector for detailed test tracking
   - Integration with existing test_all.py infrastructure

4. **pytest_integration.py**: Pytest framework adapter
   - `PytestRunner` class for pytest execution
   - Snapshot testing support
   - Parallel execution capabilities

5. **test_runner_utils.py**: Shared utilities
   - Test discovery functions
   - Result aggregation
   - Progress tracking with Rich
   - Output formatting (Rich, plain, JSON)

6. **run_all_tests.py**: Main entry point
   - CLI argument parsing
   - Framework orchestration
   - Unified reporting

### Test Runner Tests

The test runner itself has comprehensive test coverage in `test_runner_tests.py`:
- Configuration validation and defaults
- Result aggregation and formatting
- Framework runner functionality
- CLI argument parsing
- Integration testing
- Performance benchmarks

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run all tests
      run: python tests/run_all_tests.py --output-format plain
      
    - name: Run tests with coverage
      run: |
        coverage run tests/run_all_tests.py
        coverage xml
      
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install -r requirements-test.txt'
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh 'python tests/run_all_tests.py --framework unittest --output-format junit > unittest-results.xml'
            }
        }
        
        stage('Integration Tests') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')]) {
                    sh 'python tests/run_all_tests.py --integration --output-format junit > integration-results.xml'
                }
            }
        }
        
        stage('Recorded Tests') {
            steps {
                sh 'python tests/run_all_tests.py --framework pytest --output-format junit > pytest-results.xml'
            }
        }
    }
    
    post {
        always {
            junit '*-results.xml'
        }
    }
}
```

### GitLab CI Example

```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
    - python tests/run_all_tests.py --output-format plain
  artifacts:
    reports:
      junit: test-results.xml
    expire_in: 1 week

test:integration:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
    - python tests/run_all_tests.py --integration --slow
  only:
    - main
  variables:
    GITHUB_TOKEN: $GITHUB_TOKEN
```

## Test Dependencies

Install test-specific dependencies:

```bash
pip install -r requirements-test.txt
```

Contents of `requirements-test.txt`:
```
pytest>=7.0.0
pytest-snapshot>=0.9.0
pytest-xdist>=3.0.0  # For parallel execution
pytest-timeout>=2.0.0
pytest-mock>=3.0.0
coverage>=7.0.0
```

## Migration Guide

### From Individual Test Runners to Unified Runner

Before:
```bash
# Run unittest tests
python tests/test_all.py --integration

# Run pytest tests separately
pytest tests/test_recorded_*.py
```

After:
```bash
# Run both test suites
python tests/run_all_tests.py --integration
```

### Custom Test Scripts

If you have custom test scripts, update them to use the unified runner:

```python
# Old approach
import subprocess
subprocess.run(['python', 'test_all.py'])
subprocess.run(['pytest', 'tests/'])

# New approach
import subprocess
result = subprocess.run(['python', 'tests/run_all_tests.py'], capture_output=True)
print(f"Tests {'passed' if result.returncode == 0 else 'failed'}")
```