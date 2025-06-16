#!/usr/bin/env python3
"""
Test the unittest integration module.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_runner_config import TestConfig
from tests.unittest_integration import UnittestRunner


def test_basic_functionality():
    """Test basic unittest runner functionality."""
    # Create config
    config = TestConfig(
        verbosity=1,
        framework="unittest",
        output_format="plain"
    )
    
    # Create runner
    runner = UnittestRunner()
    
    # Discover tests
    tests = runner.discover_tests(config)
    print(f"Discovered {len(tests)} tests")
    
    # Run a few tests
    if tests:
        sample_tests = tests[:5]  # Run first 5 tests
        results = runner.run_tests(sample_tests, config)
        
        print(f"\nTest Results:")
        print(f"Total: {results.total_tests}")
        print(f"Passed: {results.passed}")
        print(f"Failed: {results.failed}")
        print(f"Errors: {results.errors}")
        print(f"Skipped: {results.skipped}")
        print(f"Success Rate: {results.success_rate:.1f}%")
        
        # Format results
        formatted = runner.format_results(results, config)
        print("\nFormatted Output:")
        print(formatted)


if __name__ == "__main__":
    test_basic_functionality()