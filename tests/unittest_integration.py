"""
Unittest framework integration for the OneFileLLM unified test runner.

This module provides the implementation for running tests using the
unittest framework, preserving compatibility with the existing test_all.py.
"""

import sys
import os
import unittest
import time
from typing import List, Optional, TextIO
from datetime import datetime
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Try importing from tests directory first, then relative import
try:
    from tests.test_runner_core import TestRunner, TestResults, TestResult
    from tests.test_runner_config import TestConfig
except ImportError:
    from test_runner_core import TestRunner, TestResults, TestResult
    from test_runner_config import TestConfig


class UnittestResultCollector(unittest.TextTestResult):
    """Custom test result class that collects individual test results."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
        self.test_start_time = {}
        
    def startTest(self, test):
        super().startTest(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.test_start_time[test] = time.time()
        
    def addSuccess(self, test):
        super().addSuccess(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        duration = time.time() - self.test_start_time.get(test, 0)
        self.test_results.append(TestResult(
            name=test_name,
            status="passed",
            duration=duration
        ))
        
    def addError(self, test, err):
        super().addError(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        duration = time.time() - self.test_start_time.get(test, 0)
        import traceback
        tb = "".join(traceback.format_exception(*err))
        self.test_results.append(TestResult(
            name=test_name,
            status="error",
            duration=duration,
            message=str(err[1]),
            traceback=tb
        ))
        
    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        duration = time.time() - self.test_start_time.get(test, 0)
        import traceback
        tb = "".join(traceback.format_exception(*err))
        self.test_results.append(TestResult(
            name=test_name,
            status="failed",
            duration=duration,
            message=str(err[1]),
            traceback=tb
        ))
        
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        duration = time.time() - self.test_start_time.get(test, 0)
        self.test_results.append(TestResult(
            name=test_name,
            status="skipped",
            duration=duration,
            message=reason
        ))


class UnittestRunner(TestRunner):
    """Test runner implementation for the unittest framework."""
    
    def __init__(self):
        """Initialize the unittest runner."""
        self.loader = unittest.TestLoader()
        
    def discover_tests(self, config: TestConfig) -> List[str]:
        """
        Discover unittest tests based on the provided configuration.
        
        Args:
            config: Test configuration object
            
        Returns:
            List of test identifiers
        """
        tests = []
        
        try:
            if config.test_files:
                # Load specific test files
                for test_file in config.test_files:
                    if test_file.endswith('.py'):
                        # Import the test module
                        module_name = test_file.replace('.py', '').replace('/', '.').replace('\\', '.')
                        if module_name.startswith('tests.'):
                            module_name = module_name[6:]  # Remove 'tests.' prefix
                        
                        try:
                            module = __import__(f"tests.{module_name}", fromlist=[module_name])
                            suite = self.loader.loadTestsFromModule(module)
                            for test_group in suite:
                                for test in test_group:
                                    test_name = f"{test.__class__.__name__}.{test._testMethodName}"
                                    tests.append(test_name)
                        except ImportError as e:
                            # Log the error but continue with other files
                            if config.verbosity > 1:
                                print(f"Warning: Could not import {test_file}: {e}")
            else:
                # Default to test_all.py
                try:
                    from tests import test_all
                    # Get all test classes from test_all
                    test_classes = [
                        getattr(test_all, name) for name in dir(test_all)
                        if name.startswith('Test') and isinstance(getattr(test_all, name), type)
                    ]
                    
                    for test_class in test_classes:
                        if issubclass(test_class, unittest.TestCase):
                            suite = self.loader.loadTestsFromTestCase(test_class)
                            for test in suite:
                                test_name = f"{test.__class__.__name__}.{test._testMethodName}"
                                tests.append(test_name)
                except ImportError as e:
                    # Return empty list if test_all cannot be imported
                    if config.verbosity > 1:
                        print(f"Warning: Could not import test_all module: {e}")
                    return []
            
            # Apply pattern filtering if specified
            if config.test_pattern:
                import re
                pattern = re.compile(config.test_pattern)
                tests = [t for t in tests if pattern.search(t)]
            
        except Exception as e:
            # Handle any unexpected errors
            if config.verbosity > 0:
                print(f"Error during test discovery: {e}")
            return []
        
        return tests
    
    def run_tests(self, tests: List[str], config: TestConfig) -> TestResults:
        """
        Run the specified unittest tests with the given configuration.
        
        Args:
            tests: List of test identifiers to run
            config: Test configuration object
            
        Returns:
            Unified test results
        """
        start_time = time.time()
        
        try:
            # Create test suite
            suite = unittest.TestSuite()
            
            # Import test_all module
            try:
                from tests import test_all
            except ImportError as e:
                return TestResults(
                    framework="unittest",
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=0,
                    duration=time.time() - start_time,
                    timestamp=datetime.now(),
                    details={"error": f"Could not import test_all module: {str(e)}"},
                    test_results=[]
                )
            
            # Load tests from test_all based on configuration
            if not tests:
                # Run all tests
                test_classes = []
                
                # Get test classes based on config
                if hasattr(test_all, 'TestUtilityFunctions'):
                    test_classes.append(test_all.TestUtilityFunctions)
                if hasattr(test_all, 'TestTextFormatDetection'):
                    test_classes.append(test_all.TestTextFormatDetection)
                if hasattr(test_all, 'TestStreamProcessing'):
                    test_classes.append(test_all.TestStreamProcessing)
                if hasattr(test_all, 'TestCoreProcessing'):
                    test_classes.append(test_all.TestCoreProcessing)
                if hasattr(test_all, 'TestAliasSystem2'):
                    test_classes.append(test_all.TestAliasSystem2)
                if hasattr(test_all, 'TestAdvancedAliasFeatures'):
                    test_classes.append(test_all.TestAdvancedAliasFeatures)
                
                # Include integration tests if configured
                if config.run_integration:
                    if hasattr(test_all, 'TestIntegration'):
                        test_classes.append(test_all.TestIntegration)
                    if hasattr(test_all, 'TestGitHubIssuesPullRequests'):
                        test_classes.append(test_all.TestGitHubIssuesPullRequests)
                    if hasattr(test_all, 'TestAdvancedWebCrawler'):
                        test_classes.append(test_all.TestAdvancedWebCrawler)
                
                # Include other test classes
                if hasattr(test_all, 'TestCLIFunctionality'):
                    test_classes.append(test_all.TestCLIFunctionality)
                if hasattr(test_all, 'TestErrorHandling'):
                    test_classes.append(test_all.TestErrorHandling)
                if hasattr(test_all, 'TestPerformance'):
                    test_classes.append(test_all.TestPerformance)
                if hasattr(test_all, 'TestMultipleInputProcessing'):
                    test_classes.append(test_all.TestMultipleInputProcessing)
            
                for test_class in test_classes:
                    suite.addTests(self.loader.loadTestsFromTestCase(test_class))
            else:
                # Run specific tests
                for test_name in tests:
                    if '.' in test_name:
                        class_name, method_name = test_name.rsplit('.', 1)
                        if hasattr(test_all, class_name):
                            test_class = getattr(test_all, class_name)
                            if hasattr(test_class, method_name):
                                suite.addTest(test_class(method_name))
            
            # Check if we're using Rich output
            if config.output_format == "rich" and hasattr(test_all, 'RichTestRunner'):
                # Use the existing RichTestRunner
                stream = StringIO() if config.verbosity == 0 else sys.stderr
                runner = test_all.RichTestRunner(
                    verbosity=config.verbosity,
                    stream=stream,
                    resultclass=UnittestResultCollector
                )
            else:
                # Use standard text runner with our collector
                stream = StringIO() if config.verbosity == 0 else sys.stderr
                runner = unittest.TextTestRunner(
                    verbosity=config.verbosity,
                    stream=stream,
                    resultclass=UnittestResultCollector
                )
            
            # Run the tests
            result = runner.run(suite)
            duration = time.time() - start_time
            
            # Extract results
            total_tests = result.testsRun
            failures = len(result.failures)
            errors = len(result.errors)
            skipped = len(result.skipped)
            passed = total_tests - failures - errors - skipped
            
            # Get individual test results if available
            test_results = []
            if hasattr(result, 'test_results'):
                test_results = result.test_results
            
            return TestResults(
                framework="unittest",
                total_tests=total_tests,
                passed=passed,
                failed=failures,
                skipped=skipped,
                errors=errors,
                duration=duration,
                timestamp=datetime.now(),
                details={
                    "stream_output": stream.getvalue() if isinstance(stream, StringIO) else ""
                },
                test_results=test_results
            )
        except Exception as e:
            # Handle any unexpected errors during test execution
            import traceback
            return TestResults(
                framework="unittest",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=time.time() - start_time,
                timestamp=datetime.now(),
                details={
                    "error": f"Unexpected error during test execution: {str(e)}",
                    "traceback": traceback.format_exc()
                },
                test_results=[]
            )
    
    def format_results(self, results: TestResults, config: TestConfig) -> str:
        """
        Format unittest results for display.
        
        Args:
            results: Test results to format
            config: Test configuration object
            
        Returns:
            Formatted string representation of results
        """
        if config.output_format == "rich":
            return self.format_results_rich(results, config)
        elif config.output_format == "json":
            return results.to_json()
        else:
            return self.format_results_plain(results, config)