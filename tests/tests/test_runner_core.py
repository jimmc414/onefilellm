"""
Core test runner architecture for OneFileLLM unified test runner.

This module provides the abstract base class and common functionality
for running tests across different testing frameworks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from rich.console import Console
from rich.table import Table
from rich.text import Text


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: str  # "passed", "failed", "error", "skipped"
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestResults:
    """Unified test results format for all test frameworks."""
    framework: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    test_results: List[TestResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of tests."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    @property
    def was_successful(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.errors == 0
    
    def to_json(self) -> str:
        """Convert results to JSON string."""
        data = {
            "framework": self.framework,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "success_rate": self.success_rate,
            "was_successful": self.was_successful,
            "details": self.details,
            "test_results": [
                {
                    "name": tr.name,
                    "status": tr.status,
                    "duration": tr.duration,
                    "message": tr.message,
                    "traceback": tr.traceback
                }
                for tr in self.test_results
            ]
        }
        return json.dumps(data, indent=2)


class TestRunner(ABC):
    """Abstract base class for test framework runners."""
    
    @abstractmethod
    def discover_tests(self, config: 'TestConfig') -> List[str]:
        """
        Discover tests based on the provided configuration.
        
        Args:
            config: Test configuration object
            
        Returns:
            List of test identifiers
        """
        pass
    
    @abstractmethod
    def run_tests(self, tests: List[str], config: 'TestConfig') -> TestResults:
        """
        Run the specified tests with the given configuration.
        
        Args:
            tests: List of test identifiers to run
            config: Test configuration object
            
        Returns:
            Unified test results
        """
        pass
    
    @abstractmethod
    def format_results(self, results: TestResults, config: 'TestConfig') -> str:
        """
        Format test results for display.
        
        Args:
            results: Test results to format
            config: Test configuration object
            
        Returns:
            Formatted string representation of results
        """
        pass
    
    def aggregate_results(self, results_list: List[TestResults]) -> TestResults:
        """
        Aggregate multiple test results into a single result.
        
        Args:
            results_list: List of test results to aggregate
            
        Returns:
            Aggregated test results
        """
        if not results_list:
            return TestResults(
                framework="all",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                timestamp=datetime.now(),
                details={},
                test_results=[]
            )
        
        total_tests = sum(r.total_tests for r in results_list)
        passed = sum(r.passed for r in results_list)
        failed = sum(r.failed for r in results_list)
        skipped = sum(r.skipped for r in results_list)
        errors = sum(r.errors for r in results_list)
        duration = sum(r.duration for r in results_list)
        
        # Aggregate all individual test results
        all_test_results = []
        for result in results_list:
            all_test_results.extend(result.test_results)
        
        details = {
            "frameworks": [r.framework for r in results_list],
            "individual_results": results_list
        }
        
        return TestResults(
            framework="all",
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            timestamp=datetime.now(),
            details=details,
            test_results=all_test_results
        )
    
    def format_results_rich(self, results: TestResults, config: 'TestConfig') -> str:
        """
        Format test results using Rich formatting.
        
        Args:
            results: Test results to format
            config: Test configuration object
            
        Returns:
            Formatted string representation of results
        """
        console = Console()
        
        # Create summary table
        table = Table(title=f"{results.framework.upper()} Test Summary", 
                     show_header=True, 
                     header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Count", justify="right", width=10)
        table.add_column("Status", width=20)
        
        # Add rows
        table.add_row("Tests Run", str(results.total_tests), "")
        
        table.add_row("Passed", str(results.passed), 
                     Text("✓", style="bold green") if results.passed > 0 else "")
        
        table.add_row("Failed", str(results.failed), 
                     Text("✗", style="bold red") if results.failed > 0 else Text("✓", style="bold green"))
        
        table.add_row("Errors", str(results.errors), 
                     Text("✗", style="bold red") if results.errors > 0 else Text("✓", style="bold green"))
        
        table.add_row("Skipped", str(results.skipped), 
                     Text("⚠", style="yellow") if results.skipped > 0 else "")
        
        table.add_row("", "", "")
        table.add_row("Duration", f"{results.duration:.2f}s", "")
        table.add_row("Success Rate", f"{results.success_rate:.1f}%", 
                     Text("✓", style="bold green") if results.success_rate == 100 else 
                     Text("⚠", style="yellow") if results.success_rate >= 80 else 
                     Text("✗", style="bold red"))
        
        # Convert to string
        with console.capture() as capture:
            console.print(table)
        
        output = capture.get()
        
        # Add failed tests if verbosity is high enough
        if config.verbosity > 1 and (results.failed > 0 or results.errors > 0):
            failed_tests = [tr for tr in results.test_results if tr.status in ["failed", "error"]]
            if failed_tests:
                output += "\n\n[bold red]Failed Tests:[/bold red]\n"
                for test in failed_tests:
                    output += f"  [red]• {test.name}[/red]\n"
                    if config.verbosity > 2 and test.message:
                        output += f"    {test.message}\n"
        
        return output
    
    def format_results_plain(self, results: TestResults, config: 'TestConfig') -> str:
        """
        Format test results as plain text.
        
        Args:
            results: Test results to format
            config: Test configuration object
            
        Returns:
            Plain text representation of results
        """
        lines = []
        lines.append(f"\n{results.framework.upper()} Test Summary")
        lines.append("=" * 50)
        lines.append(f"Tests Run:    {results.total_tests}")
        lines.append(f"Passed:       {results.passed}")
        lines.append(f"Failed:       {results.failed}")
        lines.append(f"Errors:       {results.errors}")
        lines.append(f"Skipped:      {results.skipped}")
        lines.append(f"Duration:     {results.duration:.2f}s")
        lines.append(f"Success Rate: {results.success_rate:.1f}%")
        
        if results.was_successful:
            lines.append("\n✅ All tests passed!")
        else:
            lines.append("\n❌ Some tests failed!")
            
            if config.verbosity > 1:
                failed_tests = [tr for tr in results.test_results if tr.status in ["failed", "error"]]
                if failed_tests:
                    lines.append("\nFailed Tests:")
                    for test in failed_tests:
                        lines.append(f"  • {test.name}")
                        if config.verbosity > 2 and test.message:
                            lines.append(f"    {test.message}")
        
        return "\n".join(lines)