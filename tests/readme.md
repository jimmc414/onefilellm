# OneFileLLM Test Suite Documentation

## Overview

The comprehensive test suite for OneFileLLM is consolidated in `test_all.py`, which replaces the previous separate test files. This suite provides extensive coverage of all functionality with 38+ tests organized into logical categories.

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

## Running Tests

### Basic Usage

```bash
# Run all basic tests (no network required)
python test_all.py

# Run with quiet output
python test_all.py --quiet

# Run with verbose output
python test_all.py --verbose

# Show help
python test_all.py --help
```

### Integration Tests

Integration tests require network access and are disabled by default:

```bash
# Enable integration tests
python test_all.py --integration

# Enable slow tests (ArXiv, web crawling)
python test_all.py --slow

# Run all tests including integration
python test_all.py --integration --slow

# With GitHub token for private repo tests
GITHUB_TOKEN=your_token python test_all.py --integration
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