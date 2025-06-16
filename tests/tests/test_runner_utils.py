"""
Test Runner Utilities for OneFileLLM Unified Test Runner

This module provides shared utility functions for test discovery, execution,
progress tracking, and result parsing across both unittest and pytest frameworks.
"""

import os
import sys
import time
import re
from typing import List, Dict, Any, Tuple, Optional, Union
from pathlib import Path
import glob
from datetime import datetime
import json

# Try to import Rich for better console output
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def discover_test_files(test_dir: str = "tests", pattern: str = "test_*.py") -> List[str]:
    """
    Discover test files matching a given pattern.
    
    Args:
        test_dir: Directory to search for test files
        pattern: Glob pattern to match test files
        
    Returns:
        List of absolute paths to test files
    """
    test_path = Path(test_dir)
    if not test_path.exists():
        return []
    
    # Handle both relative and absolute paths
    if not test_path.is_absolute():
        test_path = Path.cwd() / test_path
    
    # Find all matching files
    test_files = []
    for file_path in test_path.glob(pattern):
        if file_path.is_file() and file_path.name != "__init__.py":
            test_files.append(str(file_path))
    
    # Sort for consistent ordering
    test_files.sort()
    return test_files


def get_unittest_tests(test_dir: str = "tests") -> List[str]:
    """
    Discover unittest test files (typically test_all.py).
    
    Args:
        test_dir: Directory to search
        
    Returns:
        List of unittest test file paths
    """
    test_path = Path(test_dir)
    if not test_path.is_absolute():
        test_path = Path.cwd() / test_path
    
    # Look for the main unittest file
    test_all_path = test_path / "test_all.py"
    if test_all_path.exists():
        return [str(test_all_path)]
    
    # Fallback: find any test files that aren't recorded tests
    unittest_files = []
    for file_path in test_path.glob("test_*.py"):
        if file_path.is_file() and not file_path.name.startswith("test_recorded_"):
            unittest_files.append(str(file_path))
    
    return unittest_files


def get_pytest_tests(test_dir: str = "tests") -> List[str]:
    """
    Discover pytest test files (test_recorded_*.py pattern).
    
    Args:
        test_dir: Directory to search
        
    Returns:
        List of pytest test file paths
    """
    return discover_test_files(test_dir, "test_recorded_*.py")


def parse_test_output(output: str, framework: str) -> Dict[str, Any]:
    """
    Parse test output from either unittest or pytest.
    
    Args:
        output: Raw test output string
        framework: Either "unittest" or "pytest"
        
    Returns:
        Dictionary with parsed test results
    """
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "total": 0,
        "duration": 0.0
    }
    
    if framework == "unittest":
        # Parse unittest output format
        # Example: "Ran 57 tests in 12.345s"
        ran_match = re.search(r"Ran (\d+) tests? in ([\d.]+)s", output)
        if ran_match:
            results["total"] = int(ran_match.group(1))
            results["duration"] = float(ran_match.group(2))
        
        # Look for OK/FAILED status
        if "OK" in output:
            results["passed"] = results["total"]
        elif "FAILED" in output:
            # Parse "FAILED (failures=2, errors=1, skipped=3)"
            failed_match = re.search(r"FAILED \(([^)]+)\)", output)
            if failed_match:
                parts = failed_match.group(1).split(", ")
                for part in parts:
                    key, value = part.split("=")
                    if key == "failures":
                        results["failed"] = int(value)
                    elif key == "errors":
                        results["errors"] = int(value)
                    elif key == "skipped":
                        results["skipped"] = int(value)
                results["passed"] = results["total"] - results["failed"] - results["errors"] - results["skipped"]
    
    elif framework == "pytest":
        # Parse pytest output format
        # Example: "5 passed, 2 failed, 1 skipped in 10.22s"
        summary_pattern = r"(\d+) passed|(\d+) failed|(\d+) skipped|(\d+) error|in ([\d.]+)s"
        
        for match in re.finditer(summary_pattern, output):
            if match.group(1):
                results["passed"] = int(match.group(1))
            elif match.group(2):
                results["failed"] = int(match.group(2))
            elif match.group(3):
                results["skipped"] = int(match.group(3))
            elif match.group(4):
                results["errors"] = int(match.group(4))
            elif match.group(5):
                results["duration"] = float(match.group(5))
        
        results["total"] = results["passed"] + results["failed"] + results["skipped"] + results["errors"]
    
    return results


def measure_test_duration(start_time: float) -> str:
    """
    Calculate and format test execution duration.
    
    Args:
        start_time: Test start time from time.time()
        
    Returns:
        Formatted duration string (e.g., "2m 35s")
    """
    duration = time.time() - start_time
    
    if duration < 60:
        return f"{duration:.1f}s"
    elif duration < 3600:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        return f"{hours}h {minutes}m"


def create_progress_tracker(total_tests: int, description: str = "Running tests"):
    """
    Create a progress tracking object for test execution.
    
    Args:
        total_tests: Total number of tests to run
        description: Description for the progress bar
        
    Returns:
        Progress tracker instance (Rich progress bar or None if not available)
    """
    if not RICH_AVAILABLE:
        return None
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=Console()
    )
    
    task_id = progress.add_task(description, total=total_tests)
    progress.task_id = task_id  # Store task_id for later updates
    
    return progress


def aggregate_results(unittest_results: Optional[Dict[str, Any]], 
                     pytest_results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from both test frameworks into unified format.
    
    Args:
        unittest_results: Results from unittest framework (or None)
        pytest_results: Results from pytest framework (or None)
        
    Returns:
        Combined results dictionary
    """
    # Initialize combined results
    combined = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": 0.0,
        "frameworks_run": [],
        "details": {}
    }
    
    # Add unittest results if available
    if unittest_results:
        combined["frameworks_run"].append("unittest")
        combined["total_tests"] += unittest_results.get("total_tests", 0)
        combined["passed"] += unittest_results.get("passed", 0)
        combined["failed"] += unittest_results.get("failed", 0)
        combined["skipped"] += unittest_results.get("skipped", 0)
        combined["errors"] += unittest_results.get("errors", 0)
        combined["duration"] += unittest_results.get("duration", 0.0)
        combined["details"]["unittest"] = unittest_results
    
    # Add pytest results if available
    if pytest_results:
        combined["frameworks_run"].append("pytest")
        combined["total_tests"] += pytest_results.get("total_tests", 0)
        combined["passed"] += pytest_results.get("passed", 0)
        combined["failed"] += pytest_results.get("failed", 0)
        combined["skipped"] += pytest_results.get("skipped", 0)
        combined["errors"] += pytest_results.get("errors", 0)
        combined["duration"] += pytest_results.get("duration", 0.0)
        combined["details"]["pytest"] = pytest_results
    
    # Calculate success rate
    if combined["total_tests"] > 0:
        combined["success_rate"] = (combined["passed"] / combined["total_tests"]) * 100
    else:
        combined["success_rate"] = 0.0
    
    combined["was_successful"] = combined["failed"] == 0 and combined["errors"] == 0
    
    return combined


def format_test_summary(results: Dict[str, Any], verbose: bool = False, use_rich: bool = True) -> str:
    """
    Format test results into a human-readable summary.
    
    Args:
        results: Aggregated test results
        verbose: Whether to include detailed information
        use_rich: Whether to use Rich formatting (if available)
        
    Returns:
        Formatted summary string
    """
    if use_rich and RICH_AVAILABLE:
        console = Console()
        
        # Create summary table
        table = Table(title="Test Results Summary", show_header=True, header_style="bold magenta")
        table.add_column("Framework", style="cyan", no_wrap=True)
        table.add_column("Total", justify="right")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Errors", justify="right", style="red")
        table.add_column("Duration", justify="right")
        
        # Add rows for each framework
        frameworks = results.get("frameworks_run", [])
        details = results.get("details", {})
        
        for fw in frameworks:
            if fw in details:
                fw_results = details[fw]
                table.add_row(
                    fw.capitalize(),
                    str(fw_results.get("total_tests", 0)),
                    str(fw_results.get("passed", 0)),
                    str(fw_results.get("failed", 0)),
                    str(fw_results.get("skipped", 0)),
                    str(fw_results.get("errors", 0)),
                    f"{fw_results.get('duration', 0):.2f}s"
                )
        
        # Add total row
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{results.get('total_tests', 0)}[/bold]",
            f"[bold green]{results.get('passed', 0)}[/bold green]",
            f"[bold red]{results.get('failed', 0)}[/bold red]",
            f"[bold yellow]{results.get('skipped', 0)}[/bold yellow]",
            f"[bold red]{results.get('errors', 0)}[/bold red]",
            f"[bold]{results.get('duration', 0):.2f}s[/bold]",
            style="bold"
        )
        
        # Convert to string
        from io import StringIO
        string_buffer = StringIO()
        temp_console = Console(file=string_buffer, force_terminal=True)
        temp_console.print(table)
        
        summary = string_buffer.getvalue()
        
        # Add success rate
        success_rate = results.get("success_rate", 0)
        if results.get("was_successful", False):
            summary += f"\n✅ All tests passed! Success rate: {success_rate:.1f}%"
        else:
            summary += f"\n❌ Some tests failed. Success rate: {success_rate:.1f}%"
        
        return summary
    
    else:
        # Plain text format
        lines = [
            "\n" + "=" * 60,
            "Test Results Summary",
            "=" * 60,
            f"Total Tests: {results.get('total_tests', 0)}",
            f"Passed:      {results.get('passed', 0)}",
            f"Failed:      {results.get('failed', 0)}",
            f"Skipped:     {results.get('skipped', 0)}",
            f"Errors:      {results.get('errors', 0)}",
            f"Duration:    {results.get('duration', 0):.2f}s",
            f"Success Rate: {results.get('success_rate', 0):.1f}%",
            "=" * 60
        ]
        
        if verbose and "details" in results:
            lines.append("\nDetailed Results:")
            for fw, fw_results in results["details"].items():
                lines.append(f"\n{fw.upper()}:")
                lines.append(f"  Total: {fw_results.get('total_tests', 0)}")
                lines.append(f"  Passed: {fw_results.get('passed', 0)}")
                lines.append(f"  Failed: {fw_results.get('failed', 0)}")
                lines.append(f"  Skipped: {fw_results.get('skipped', 0)}")
                lines.append(f"  Errors: {fw_results.get('errors', 0)}")
                lines.append(f"  Duration: {fw_results.get('duration', 0):.2f}s")
        
        if results.get("was_successful", False):
            lines.append("\n✅ All tests passed!")
        else:
            lines.append("\n❌ Some tests failed.")
        
        return "\n".join(lines)


def ensure_test_environment() -> None:
    """
    Ensure the test environment is properly configured.
    
    Checks for required dependencies, environment variables, etc.
    """
    warnings = []
    
    # Check Python version
    if sys.version_info < (3, 7):
        warnings.append("Warning: Python 3.7+ is recommended for optimal test runner performance")
    
    # Check for pytest
    try:
        import pytest
    except ImportError:
        warnings.append("Warning: pytest not installed. Install with: pip install pytest pytest-snapshot")
    
    # Check for pytest-snapshot
    try:
        import pytest_snapshot
    except ImportError:
        warnings.append("Warning: pytest-snapshot not installed. Snapshot tests may fail.")
    
    # Check for Rich (optional but recommended)
    if not RICH_AVAILABLE:
        warnings.append("Info: Rich library not installed. Install for better output: pip install rich")
    
    # Check environment variables
    if not os.environ.get("GITHUB_TOKEN"):
        warnings.append("Info: GITHUB_TOKEN not set. Some integration tests may be skipped.")
    
    # Print warnings if any
    if warnings:
        print("\nTest Environment Check:")
        for warning in warnings:
            print(f"  - {warning}")
        print()


def get_test_count_from_files(test_files: List[str]) -> int:
    """
    Estimate the number of tests in the given test files.
    
    Args:
        test_files: List of test file paths
        
    Returns:
        Estimated number of tests
    """
    test_count = 0
    
    for file_path in test_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Count test methods (rough estimate)
                test_count += len(re.findall(r'def test_\w+\(', content))
        except:
            # If we can't read the file, assume at least 1 test
            test_count += 1
    
    return test_count