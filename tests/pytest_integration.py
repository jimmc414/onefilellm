"""
Pytest Integration Module for OneFileLLM Unified Test Runner

This module implements the PytestRunner class which provides pytest-specific
test discovery, execution, and result parsing functionality.
"""

from typing import List, Optional, Dict, Any
import os
import sys
import glob
import time
from datetime import datetime
from pathlib import Path
import json
import subprocess

# Add proper import path handling
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing from tests directory first, then relative import
try:
    from tests.test_runner_core import TestRunner, TestResults
    from tests.test_runner_config import TestConfig
except ImportError:
    from test_runner_core import TestRunner, TestResults
    from test_runner_config import TestConfig

# Try to import pytest (graceful fallback if not available)
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


class PytestRunner(TestRunner):
    """
    Pytest-specific test runner implementation.
    
    Handles discovery and execution of recorded tests using pytest framework,
    including snapshot testing functionality.
    """
    
    def discover_tests(self, config: TestConfig) -> List[str]:
        """
        Discover all pytest test files (test_recorded_*.py).
        
        Args:
            config: TestConfig instance
            
        Returns:
            List of test file paths
        """
        test_files = []
        
        # Start from the tests directory
        test_dir = Path(__file__).parent
        
        # Handle specific test files if provided
        if config.test_files:
            for file_pattern in config.test_files:
                if os.path.isabs(file_pattern):
                    if os.path.exists(file_pattern):
                        test_files.append(file_pattern)
                else:
                    # Search for files matching the pattern
                    matches = list(test_dir.glob(file_pattern))
                    test_files.extend(str(f) for f in matches if f.is_file())
        else:
            # Default: find all test_recorded_*.py files
            pattern = config.test_pattern or "test_recorded_*.py"
            test_files = glob.glob(str(test_dir / pattern))
        
        # Sort for consistent ordering
        test_files.sort()
        
        return test_files
    
    def configure_pytest(self, config: TestConfig) -> List[str]:
        """
        Configure pytest with appropriate arguments based on TestConfig.
        
        Args:
            config: TestConfig instance with user preferences
            
        Returns:
            List of pytest command line arguments
        """
        args = []
        
        # Verbosity mapping
        if config.verbosity == 0:
            args.append("-q")
        elif config.verbosity == 1:
            pass  # Normal verbosity
        elif config.verbosity == 2:
            args.append("-v")
        elif config.verbosity >= 3:
            args.extend(["-vv", "-s"])
        
        # Output format
        if config.output_format == "json":
            args.append("--json-report")
            args.append("--json-report-file=pytest_report.json")
        
        # Snapshot testing
        if config.snapshot_update:
            args.append("--snapshot-update")
        
        # Parallel execution
        if config.parallel_execution:
            # Use pytest-xdist if available
            try:
                import xdist
                workers = config.max_workers or "auto"
                args.append(f"-n{workers}")
            except ImportError:
                pass  # Fall back to sequential execution
        
        # Fail fast
        if config.fail_fast:
            args.append("-x")
        
        # Test filtering
        if config.test_pattern and not config.test_files:
            args.append(f"-k {config.test_pattern}")
        
        # Disable warnings in CI mode
        if config.ci_mode:
            args.append("--disable-warnings")
        
        # Report generation
        if config.generate_report:
            if config.report_format == "html":
                args.append("--html=pytest_report.html")
                args.append("--self-contained-html")
            elif config.report_format == "xml":
                args.append("--junit-xml=pytest_report.xml")
        
        return args
    
    def run_tests(self, tests: List[str], config: TestConfig) -> TestResults:
        """
        Execute pytest tests programmatically.
        
        Args:
            tests: List of test files to run
            config: TestConfig instance
            
        Returns:
            TestResults instance
        """
        if not PYTEST_AVAILABLE:
            # Fallback to subprocess if pytest not available
            return self._run_tests_subprocess(tests, config)
        
        start_time = time.time()
        
        # Configure pytest arguments
        pytest_args = self.configure_pytest(config)
        pytest_args.extend(tests)
        
        # Run pytest programmatically
        exit_code = pytest.main(pytest_args)
        
        duration = time.time() - start_time
        
        # Parse results
        results = self._parse_pytest_results(exit_code, duration, config)
        
        return results
    
    def _run_tests_subprocess(self, tests: List[str], config: TestConfig) -> TestResults:
        """
        Run pytest as a subprocess (fallback when pytest not installed).
        
        Args:
            tests: List of test files to run
            config: TestConfig instance
            
        Returns:
            TestResults instance
        """
        start_time = time.time()
        
        # Build command
        cmd = [sys.executable, "-m", "pytest"]
        cmd.extend(self.configure_pytest(config))
        cmd.extend(tests)
        
        # Run subprocess
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            duration = time.time() - start_time
            
            # Basic parsing of output
            output_lines = result.stdout.splitlines()
            passed = failed = skipped = errors = 0
            
            for line in output_lines:
                if "passed" in line:
                    try:
                        passed = int(line.split()[0])
                    except:
                        pass
                if "failed" in line:
                    try:
                        failed = int(line.split()[0])
                    except:
                        pass
                if "skipped" in line:
                    try:
                        skipped = int(line.split()[0])
                    except:
                        pass
                if "error" in line:
                    try:
                        errors = int(line.split()[0])
                    except:
                        pass
            
            total_tests = passed + failed + skipped + errors
            
            return TestResults(
                framework="pytest",
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=duration,
                timestamp=datetime.now(),
                details={
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )
            
        except subprocess.TimeoutExpired:
            return TestResults(
                framework="pytest",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=time.time() - start_time,
                timestamp=datetime.now(),
                details={"error": "Test execution timed out"}
            )
    
    def _parse_pytest_results(self, exit_code: int, duration: float, config: TestConfig) -> TestResults:
        """
        Parse pytest results from exit code and optional JSON report.
        
        Args:
            exit_code: Pytest exit code
            duration: Test execution duration
            config: TestConfig instance
            
        Returns:
            TestResults instance
        """
        # Try to load JSON report if available
        json_report_path = "pytest_report.json"
        if config.output_format == "json" and os.path.exists(json_report_path):
            try:
                with open(json_report_path, 'r') as f:
                    report = json.load(f)
                
                summary = report.get("summary", {})
                return TestResults(
                    framework="pytest",
                    total_tests=summary.get("total", 0),
                    passed=summary.get("passed", 0),
                    failed=summary.get("failed", 0),
                    skipped=summary.get("skipped", 0),
                    errors=summary.get("error", 0),
                    duration=duration,
                    timestamp=datetime.now(),
                    details=report
                )
            except:
                pass  # Fall back to exit code parsing
        
        # Basic interpretation from exit code
        # Exit codes: 0=success, 1=tests failed, 2=interrupted, 3=internal error, 4=usage error, 5=no tests
        if exit_code == 0:
            # All tests passed
            return TestResults(
                framework="pytest",
                total_tests=1,  # Minimum assumption
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                duration=duration,
                timestamp=datetime.now(),
                details={"exit_code": exit_code}
            )
        elif exit_code == 5:
            # No tests collected
            return TestResults(
                framework="pytest",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=duration,
                timestamp=datetime.now(),
                details={"exit_code": exit_code, "message": "No tests found"}
            )
        else:
            # Some kind of failure
            return TestResults(
                framework="pytest",
                total_tests=1,
                passed=0,
                failed=1 if exit_code == 1 else 0,
                skipped=0,
                errors=1 if exit_code > 1 else 0,
                duration=duration,
                timestamp=datetime.now(),
                details={"exit_code": exit_code}
            )
    
    def format_results(self, results: TestResults, config: TestConfig) -> str:
        """
        Format test results for display.
        
        Args:
            results: Test results to format
            config: Test configuration object
            
        Returns:
            Formatted string representation of results
        """
        if config.output_format == "json":
            return json.dumps({
                "framework": results.framework,
                "total_tests": results.total_tests,
                "passed": results.passed,
                "failed": results.failed,
                "skipped": results.skipped,
                "errors": results.errors,
                "duration": results.duration,
                "success_rate": results.success_rate,
                "timestamp": results.timestamp.isoformat()
            }, indent=2)
        
        # Plain text format
        lines = [
            f"\n{'=' * 60}",
            f"Pytest Test Results",
            f"{'=' * 60}",
            f"Total Tests: {results.total_tests}",
            f"Passed:      {results.passed}",
            f"Failed:      {results.failed}",
            f"Skipped:     {results.skipped}",
            f"Errors:      {results.errors}",
            f"Duration:    {results.duration:.2f}s",
            f"Success Rate: {results.success_rate:.1f}%",
            f"{'=' * 60}"
        ]
        
        return "\n".join(lines)