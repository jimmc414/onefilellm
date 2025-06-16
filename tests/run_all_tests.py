#!/usr/bin/env python3
"""
Unified test runner for OneFileLLM project.
Executes both unittest and pytest test suites with unified reporting.
"""

import argparse
import sys
import os
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import test runner components
try:
    from tests.test_runner_config import TestConfig
    from tests.test_runner_core import TestResults, TestResult
    from tests.unittest_integration import UnittestRunner
    from tests.pytest_integration import PytestRunner
except ImportError as e:
    print(f"Error importing test runner components: {e}")
    print("Make sure all test runner files are properly installed.")
    sys.exit(1)

# Try importing Rich for formatted output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Using plain output.")


class TestFramework(Enum):
    """Supported test frameworks."""
    UNITTEST = "unittest"
    PYTEST = "pytest"
    ALL = "all"
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the unified test runner."""
    parser = argparse.ArgumentParser(
        description="Unified test runner for OneFileLLM - runs both unittest and pytest suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests (both unittest and pytest)
  python tests/run_all_tests.py
  
  # Run only unittest suite
  python tests/run_all_tests.py --framework unittest
  
  # Run with integration tests
  python tests/run_all_tests.py --integration
  
  # Run pytest with snapshot update
  python tests/run_all_tests.py --framework pytest --snapshot-update
  
  # Run tests in parallel
  python tests/run_all_tests.py --parallel
"""
    )
    
    # Test selection arguments
    parser.add_argument(
        "--framework",
        choices=["unittest", "pytest", "all"],
        default="all",
        help="Which test framework to run (default: all)"
    )
    
    # Existing test_all.py arguments
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests that require network access"
    )
    
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Run slow tests (comprehensive web crawling tests)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (can be specified multiple times)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output - only show summary"
    )
    
    # New unified runner arguments
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (when supported)"
    )
    
    parser.add_argument(
        "--snapshot-update",
        action="store_true",
        help="Update pytest snapshots"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["rich", "plain", "json"],
        default="rich",
        help="Output format for test results (default: rich)"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode - appropriate defaults for continuous integration"
    )
    
    return parser.parse_args()


def create_test_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Create test configuration from command line arguments."""
    # Adjust verbosity based on quiet flag and CI mode
    verbosity = 0 if args.quiet else args.verbose
    if args.ci:
        verbosity = 1  # Moderate verbosity for CI
    
    config = {
        'verbosity': verbosity,
        'run_integration': args.integration,
        'run_slow': args.slow,
        'output_format': 'plain' if args.ci or args.no_color else args.output_format,
        'parallel_execution': args.parallel,
        'framework': args.framework,
        'snapshot_update': args.snapshot_update,
        'ci_mode': args.ci
    }
    
    # Set environment variables for test runners
    if args.integration:
        os.environ['RUN_INTEGRATION_TESTS'] = 'true'
    if args.slow:
        os.environ['RUN_SLOW_TESTS'] = 'true'
    
    return config


def get_console(config: Dict[str, Any]) -> Any:
    """Get appropriate console for output."""
    if RICH_AVAILABLE and config['output_format'] == 'rich':
        return Console()
    return None


def run_unittest_suite(config: Dict[str, Any], console: Any) -> TestResults:
    """Run the unittest test suite."""
    if console:
        console.print("[bold cyan]Running unittest suite...[/bold cyan]")
    else:
        print("Running unittest suite...")
    
    # Create TestConfig from dict
    test_config = TestConfig(**config)
    
    # Initialize and run UnittestRunner
    runner = UnittestRunner()
    tests = runner.discover_tests(test_config)
    results = runner.run_tests(tests, test_config)
    
    return results


def run_pytest_suite(config: Dict[str, Any], console: Any) -> TestResults:
    """Run the pytest test suite."""
    if console:
        console.print("[bold cyan]Running pytest suite...[/bold cyan]")
    else:
        print("Running pytest suite...")
    
    # Create TestConfig from dict
    test_config = TestConfig(**config)
    
    # Initialize and run PytestRunner
    runner = PytestRunner()
    tests = runner.discover_tests(test_config)
    results = runner.run_tests(tests, test_config)
    
    return results


def aggregate_results(results_list: List[TestResults]) -> TestResults:
    """Aggregate results from multiple test runs."""
    if not results_list:
        return TestResults(
            framework="all",
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            duration=0.0,
            timestamp=datetime.now()
        )
    
    aggregate = TestResults(
        framework="all",
        total_tests=sum(r.total_tests for r in results_list),
        passed=sum(r.passed for r in results_list),
        failed=sum(r.failed for r in results_list),
        skipped=sum(r.skipped for r in results_list),
        errors=sum(r.errors for r in results_list),
        duration=sum(r.duration for r in results_list),
        timestamp=datetime.now()
    )
    
    # Aggregate test results
    for result in results_list:
        aggregate.test_results.extend(result.test_results)
    
    return aggregate


def display_results_rich(results: TestResults, results_list: List[TestResults], console: Console):
    """Display test results using Rich formatting."""
    # Create summary table
    table = Table(title="Test Results Summary", box=box.ROUNDED)
    table.add_column("Framework", style="cyan", justify="left")
    table.add_column("Total", justify="center")
    table.add_column("Passed", style="green", justify="center")
    table.add_column("Failed", style="red", justify="center")
    table.add_column("Skipped", style="yellow", justify="center")
    table.add_column("Errors", style="red", justify="center")
    table.add_column("Duration", justify="center")
    table.add_column("Success Rate", justify="center")
    
    # Add individual framework results
    for r in results_list:
        success_style = "green" if r.failed == 0 and r.errors == 0 else "red"
        table.add_row(
            r.framework.capitalize(),
            str(r.total_tests),
            str(r.passed),
            str(r.failed) if r.failed > 0 else "0",
            str(r.skipped) if r.skipped > 0 else "0",
            str(r.errors) if r.errors > 0 else "0",
            f"{r.duration:.2f}s",
            f"[{success_style}]{r.success_rate:.1f}%[/{success_style}]"
        )
    
    # Add separator if multiple frameworks
    if len(results_list) > 1:
        table.add_section()
        success_style = "green" if results.failed == 0 and results.errors == 0 else "red"
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{results.total_tests}[/bold]",
            f"[bold]{results.passed}[/bold]",
            f"[bold]{results.failed}[/bold]" if results.failed > 0 else "[bold]0[/bold]",
            f"[bold]{results.skipped}[/bold]" if results.skipped > 0 else "[bold]0[/bold]",
            f"[bold]{results.errors}[/bold]" if results.errors > 0 else "[bold]0[/bold]",
            f"[bold]{results.duration:.2f}s[/bold]",
            f"[bold {success_style}]{results.success_rate:.1f}%[/bold {success_style}]"
        )
    
    console.print(table)
    
    # Display failures if any
    failed_tests = [tr for tr in results.test_results if tr.status in ["failed", "error"]]
    if failed_tests:
        console.print("\n[bold red]Failed Tests:[/bold red]")
        for test in failed_tests:
            console.print(f"  • {test.name}: {test.message or 'No message'}")


def display_results_plain(results: TestResults, results_list: List[TestResults]):
    """Display test results in plain text format."""
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    # Individual framework results
    for r in results_list:
        print(f"\n{r.framework.upper()} Tests:")
        print(f"  Total: {r.total_tests}")
        print(f"  Passed: {r.passed}")
        print(f"  Failed: {r.failed}")
        print(f"  Skipped: {r.skipped}")
        print(f"  Errors: {r.errors}")
        print(f"  Duration: {r.duration:.2f}s")
        print(f"  Success Rate: {r.success_rate:.1f}%")
    
    # Aggregate results if multiple frameworks
    if len(results_list) > 1:
        print(f"\nTOTAL:")
        print(f"  Total: {results.total_tests}")
        print(f"  Passed: {results.passed}")
        print(f"  Failed: {results.failed}")
        print(f"  Skipped: {results.skipped}")
        print(f"  Errors: {results.errors}")
        print(f"  Duration: {results.duration:.2f}s")
        print(f"  Success Rate: {results.success_rate:.1f}%")
    
    print("="*60)
    
    # Display failures if any
    failed_tests = [tr for tr in results.test_results if tr.status in ["failed", "error"]]
    if failed_tests:
        print("\nFAILED TESTS:")
        for test in failed_tests:
            print(f"  • {test.name}: {test.message or 'No message'}")


def display_results_json(results: TestResults, results_list: List[TestResults]):
    """Display test results in JSON format."""
    output = {
        "summary": {
            "total": results.total_tests,
            "passed": results.passed,
            "failed": results.failed,
            "skipped": results.skipped,
            "errors": results.errors,
            "duration": results.duration,
            "success_rate": results.success_rate
        },
        "frameworks": [
            {
                "name": r.framework,
                "total": r.total_tests,
                "passed": r.passed,
                "failed": r.failed,
                "skipped": r.skipped,
                "errors": r.errors,
                "duration": r.duration,
                "success_rate": r.success_rate
            }
            for r in results_list
        ],
        "failures": [
            {
                "test": tr.name,
                "status": tr.status,
                "message": tr.message,
                "traceback": tr.traceback
            }
            for tr in results.test_results
            if tr.status in ["failed", "error"]
        ]
    }
    
    print(json.dumps(output, indent=2))


def main() -> int:
    """Main entry point for the unified test runner."""
    args = parse_arguments()
    config = create_test_config(args)
    console = get_console(config)
    
    # Display header
    if console and config['output_format'] == 'rich':
        console.print(Panel.fit(
            "[bold cyan]OneFileLLM Unified Test Runner[/bold cyan]",
            border_style="cyan"
        ))
    else:
        print("\n" + "="*40)
        print("OneFileLLM Unified Test Runner")
        print("="*40)
    
    results_list = []
    
    try:
        # Run appropriate test suites
        if args.framework in ["unittest", "all"]:
            unittest_results = run_unittest_suite(config, console)
            results_list.append(unittest_results)
        
        if args.framework in ["pytest", "all"]:
            pytest_results = run_pytest_suite(config, console)
            results_list.append(pytest_results)
        
        # Aggregate results
        total_results = aggregate_results(results_list)
        
        # Display results based on output format
        if config['output_format'] == 'json':
            display_results_json(total_results, results_list)
        elif console and config['output_format'] == 'rich':
            display_results_rich(total_results, results_list, console)
        else:
            display_results_plain(total_results, results_list)
        
        # Return appropriate exit code
        if total_results.failed > 0 or total_results.errors > 0:
            return 1
        return 0
        
    except KeyboardInterrupt:
        if console:
            console.print("\n[yellow]Test execution interrupted by user[/yellow]")
        else:
            print("\nTest execution interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        if console:
            console.print(f"\n[red]Error: {str(e)}[/red]")
        else:
            print(f"\nError: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())