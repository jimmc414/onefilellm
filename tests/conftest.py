"""
Pytest configuration file for onefilellm test suite.
Provides global fixtures, markers, and configuration for all tests.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


# Register custom markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (may require network access)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (takes more than 30 seconds)"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "github: mark test as requiring GitHub API access"
    )
    config.addinivalue_line(
        "markers", "crawl: mark test as a web crawling test"
    )
    config.addinivalue_line(
        "markers", "cli: mark test as a CLI command test"
    )
    config.addinivalue_line(
        "markers", "alias: mark test as an alias system test"
    )


# Note: Global timeout is configured in pytest.ini
# The pytest-timeout plugin must be installed for timeout support
# pip install pytest-timeout


# Fixtures for common test needs
@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses to avoid rate limiting."""
    with patch('requests.get') as mock_get:
        # Mock successful repository response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'test-repo',
            'description': 'Test repository',
            'default_branch': 'main'
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_web_requests():
    """Mock web requests to avoid actual network calls."""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text.return_value = '<html><body>Test content</body></html>'
        mock_response.read.return_value = b'<html><body>Test content</body></html>'
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        yield mock_session


@pytest.fixture
def temp_test_dir(tmp_path):
    """Create a temporary directory with test files."""
    # Create some test files
    (tmp_path / "test.txt").write_text("Test content")
    (tmp_path / "test.py").write_text("print('Hello world')")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("Nested content")
    
    return tmp_path


@pytest.fixture(autouse=True)
def set_test_environment():
    """Set environment variables for testing."""
    original_env = os.environ.copy()
    
    # Disable real network calls unless explicitly testing integration
    os.environ['ONEFILELLM_TEST_MODE'] = 'true'
    
    # Set a dummy GitHub token to avoid rate limiting warnings
    if 'GITHUB_TOKEN' not in os.environ:
        os.environ['GITHUB_TOKEN'] = 'dummy-token-for-testing'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Skip slow tests by default unless --slow flag is passed
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    # Skip integration tests if --unit-only flag is passed
    if hasattr(config.option, "unit_only") and config.option.unit_only:
        skip_integration = pytest.mark.skip(reason="running unit tests only")
        for item in items:
            if "integration" in item.keywords or "network" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--slow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--unit-only", action="store_true", default=False, help="run only unit tests"
    )
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )