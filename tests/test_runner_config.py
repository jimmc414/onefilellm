"""
Configuration management for the OneFileLLM unified test runner.

This module defines the configuration dataclass and related utilities
for controlling test execution across different frameworks.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import os


@dataclass
class TestConfig:
    """Configuration for test execution."""
    
    # Verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)
    verbosity: int = 2
    
    # Test selection flags
    run_integration: bool = False
    run_slow: bool = False
    
    # Output formatting
    output_format: str = "rich"  # Options: "rich", "plain", "json"
    
    # Execution options
    parallel_execution: bool = False
    max_workers: Optional[int] = None
    
    # Framework selection
    framework: str = "all"  # Options: "unittest", "pytest", "all"
    
    # Pytest-specific options
    snapshot_update: bool = False
    
    # Test filtering
    test_pattern: Optional[str] = None
    test_files: List[str] = field(default_factory=list)
    
    # Environment variables
    github_token: Optional[str] = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN"))
    
    # CI/CD options
    ci_mode: bool = field(default_factory=lambda: os.environ.get("CI", "false").lower() == "true")
    fail_fast: bool = False
    
    # Reporting options
    generate_report: bool = False
    report_format: str = "html"  # Options: "html", "xml", "json"
    report_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values."""
        if self.verbosity not in range(4):
            raise ValueError(f"Verbosity must be between 0 and 3, got {self.verbosity}")
        
        if self.output_format not in ["rich", "plain", "json"]:
            raise ValueError(f"Invalid output format: {self.output_format}")
        
        if self.framework not in ["unittest", "pytest", "all"]:
            raise ValueError(f"Invalid framework: {self.framework}")
        
        if self.report_format not in ["html", "xml", "json"]:
            raise ValueError(f"Invalid report format: {self.report_format}")
        
        if self.parallel_execution and self.max_workers is not None and self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
    
    @classmethod
    def from_environment(cls) -> 'TestConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override from environment
        if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() == "true":
            config.run_integration = True
        
        if os.environ.get("RUN_SLOW_TESTS", "").lower() == "true":
            config.run_slow = True
        
        if os.environ.get("TEST_VERBOSITY"):
            try:
                config.verbosity = int(os.environ["TEST_VERBOSITY"])
            except ValueError:
                pass
        
        if os.environ.get("NO_COLOR", "").lower() == "1":
            config.output_format = "plain"
        
        return config
    
    @classmethod
    def from_args(cls, args) -> 'TestConfig':
        """Create configuration from command line arguments.
        
        Args:
            args: Parsed argparse namespace
            
        Returns:
            TestConfig instance
        """
        config = cls.from_environment()
        
        # Override with command line arguments
        if hasattr(args, 'verbosity') and args.verbosity is not None:
            config.verbosity = args.verbosity
        
        if hasattr(args, 'integration') and args.integration:
            config.run_integration = True
            
        if hasattr(args, 'slow') and args.slow:
            config.run_slow = True
            
        if hasattr(args, 'framework') and args.framework:
            config.framework = args.framework
            
        if hasattr(args, 'parallel') and args.parallel:
            config.parallel_execution = True
            
        if hasattr(args, 'workers') and args.workers:
            config.max_workers = args.workers
            
        if hasattr(args, 'snapshot_update') and args.snapshot_update:
            config.snapshot_update = True
            
        if hasattr(args, 'output_format') and args.output_format:
            config.output_format = args.output_format
            
        if hasattr(args, 'no_color') and args.no_color:
            config.output_format = "plain"
            
        if hasattr(args, 'pattern') and args.pattern:
            config.test_pattern = args.pattern
            
        if hasattr(args, 'test_files') and args.test_files:
            config.test_files = args.test_files
            
        if hasattr(args, 'generate_report') and args.generate_report:
            config.generate_report = True
            
        if hasattr(args, 'report_format') and args.report_format:
            config.report_format = args.report_format
            
        if hasattr(args, 'report_path') and args.report_path:
            config.report_path = args.report_path
            
        if hasattr(args, 'fail_fast') and args.fail_fast:
            config.fail_fast = True
        
        return config
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "verbosity": self.verbosity,
            "run_integration": self.run_integration,
            "run_slow": self.run_slow,
            "output_format": self.output_format,
            "parallel_execution": self.parallel_execution,
            "max_workers": self.max_workers,
            "framework": self.framework,
            "snapshot_update": self.snapshot_update,
            "test_pattern": self.test_pattern,
            "test_files": self.test_files,
            "ci_mode": self.ci_mode,
            "fail_fast": self.fail_fast,
            "generate_report": self.generate_report,
            "report_format": self.report_format,
            "report_path": self.report_path
        }
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'TestConfig':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary with configuration values
            
        Returns:
            TestConfig instance
        """
        # Filter out any keys that aren't TestConfig attributes
        valid_keys = {
            'verbosity', 'run_integration', 'run_slow', 'output_format',
            'parallel_execution', 'max_workers', 'framework', 'snapshot_update',
            'test_pattern', 'test_files', 'github_token', 'ci_mode', 'fail_fast',
            'generate_report', 'report_format', 'report_path'
        }
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}
        return cls(**filtered_dict)