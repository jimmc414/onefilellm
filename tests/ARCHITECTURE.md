# OneFileLLM Test Infrastructure Architecture

## Overview

The OneFileLLM test infrastructure is a sophisticated dual-framework system designed to provide comprehensive test coverage through both manually written unit tests and automatically recorded integration tests.

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Test Runner                      │
│                   (run_all_tests.py)                        │
├─────────────────────┬───────────────────────────────────────┤
│   Unittest Suite    │         Pytest Suite                  │
│   (test_all.py)     │    (test_recorded_*.py)              │
│                     │                                        │
│   57+ Unit Tests    │    119 Recorded Tests                 │
│   - Core Functions  │    - Real-world Scenarios             │
│   - Edge Cases      │    - Snapshot Validation              │
│   - Mocked APIs     │    - Integration Testing              │
└─────────────────────┴───────────────────────────────────────┘
```

## Component Architecture

### 1. Core Components

#### run_all_tests.py (Main Orchestrator)
- **Purpose**: Unified entry point for all test execution
- **Responsibilities**:
  - Parse command-line arguments
  - Configure test execution environment
  - Delegate to framework-specific runners
  - Aggregate and display results
  - Handle exit codes for CI/CD

#### test_runner_core.py (Abstract Base)
- **Purpose**: Define common interface for test runners
- **Key Classes**:
  - `TestRunner` (ABC): Abstract base for framework runners
  - `TestResults`: Unified result format
  - `TestResult`: Individual test result
- **Features**:
  - Framework-agnostic result format
  - Common formatting methods
  - Result aggregation logic

#### test_runner_config.py (Configuration)
- **Purpose**: Centralized configuration management
- **Key Class**: `TestConfig` dataclass
- **Features**:
  - Environment variable support
  - CLI argument integration
  - Validation and defaults
  - JSON serialization

### 2. Framework Integrations

#### unittest_integration.py
- **Purpose**: Adapter for unittest framework
- **Key Classes**:
  - `UnittestRunner`: Implements TestRunner interface
  - `UnittestResultCollector`: Custom result collector
- **Integration Points**:
  - Loads test_all.py test classes
  - Supports RichTestRunner if available
  - Handles test discovery and filtering

#### pytest_integration.py
- **Purpose**: Adapter for pytest framework
- **Key Class**: `PytestRunner`
- **Features**:
  - Snapshot testing support
  - Parallel execution capability
  - Multiple output formats
  - Subprocess fallback if pytest not installed

### 3. Test Suites

#### test_all.py (Manual Tests)
```python
TestUtilityFunctions     # 7 tests - File I/O, utilities
TestTextFormatDetection  # 2 tests - Format detection
TestStreamProcessing     # 5 tests - stdin, clipboard
TestCoreProcessing       # 6 tests - Core functionality
TestAliasSystem2         # 6 tests - Alias management
TestAdvancedAliasFeatures # 2 tests - Complex aliases
TestIntegration          # 4 tests - External APIs
TestCLIFunctionality     # 5 tests - CLI interface
TestErrorHandling        # 4 tests - Error scenarios
TestPerformance         # 3 tests - Performance
TestMultipleInputProcessing # 3 tests - Multi-input
TestGitHubIssuesPullRequests # 5 tests - GitHub features
TestAdvancedWebCrawler   # 5 tests - Web crawling
```

#### test_recorded_*.py (Automated Tests)
- **Structure**: Each file contains one recorded scenario
- **Naming**: `test_recorded_{category}_{specific}.py`
- **Categories**:
  - alias: Command alias functionality
  - arxiv: Academic paper fetching
  - complex: Multi-source scenarios
  - crawl: Web crawling tests
  - dir: Directory processing
  - doi/pmid: Academic sources
  - error: Error handling
  - format: Output formats
  - github: Repository/issue/PR tests
  - help: Help system
  - local: File processing
  - stdin: Input stream handling
  - web: Web page fetching
  - youtube: Transcript extraction

### 4. Supporting Infrastructure

#### harness_claude1.py (Test Harness)
- **Purpose**: Subprocess execution for recorded tests
- **Functions**:
  - `run_program()`: Execute with captured output
  - `run_program_with_input()`: Execute with stdin
  - `run_program_expect_success()`: Assert success
  - `create_temp_file/directory()`: Test data creation
- **Features**:
  - Consistent subprocess handling
  - Output capture and formatting
  - Timeout protection
  - Path resolution

#### Snapshot System
- **Location**: `tests/snapshots/`
- **Format**: Text files with captured output
- **Naming**: `{test_name}_{hash}.txt`
- **Management**: pytest-snapshot plugin

## Data Flow Architecture

```
User Input
    │
    ▼
run_all_tests.py
    │
    ├─── Parse Arguments ──→ TestConfig
    │                           │
    ▼                           ▼
Framework Selection     Configuration Validation
    │                           │
    ├──── unittest ────┐        │
    │                  ▼        ▼
    │            UnittestRunner │
    │                  │        │
    │                  ▼        │
    │             test_all.py   │
    │                  │        │
    └──── pytest ──────┼────────┘
                       ▼
                  PytestRunner
                       │
                       ▼
              test_recorded_*.py
                       │
                       ▼
                TestResults Aggregation
                       │
                       ▼
                Output Formatting
                       │
                       ▼
                  Exit Code
```

## Test Execution Flow

### 1. Initialization Phase
```python
# Command line parsing
args = parse_arguments()

# Configuration creation
config = create_test_config(args)

# Environment setup
if args.integration:
    os.environ['RUN_INTEGRATION_TESTS'] = 'true'
```

### 2. Discovery Phase
```python
# Unittest discovery
unittest_runner = UnittestRunner()
unittest_tests = unittest_runner.discover_tests(config)

# Pytest discovery
pytest_runner = PytestRunner()
pytest_tests = pytest_runner.discover_tests(config)
```

### 3. Execution Phase
```python
# Run selected frameworks
results_list = []
if config.framework in ["unittest", "all"]:
    results_list.append(unittest_runner.run_tests(unittest_tests, config))

if config.framework in ["pytest", "all"]:
    results_list.append(pytest_runner.run_tests(pytest_tests, config))
```

### 4. Reporting Phase
```python
# Aggregate results
total_results = aggregate_results(results_list)

# Format output
if config.output_format == "rich":
    display_results_rich(total_results, results_list, console)
elif config.output_format == "json":
    display_results_json(total_results, results_list)
else:
    display_results_plain(total_results, results_list)

# Exit with appropriate code
sys.exit(0 if total_results.was_successful else 1)
```

## Design Principles

### 1. Separation of Concerns
- Clear boundaries between test frameworks
- Abstraction of common functionality
- Pluggable architecture for new frameworks

### 2. Unified Interface
- Consistent configuration across frameworks
- Common result format
- Single entry point for all tests

### 3. Extensibility
- Easy to add new test frameworks
- Configurable output formats
- Plugin-style architecture

### 4. CI/CD Optimization
- Proper exit codes
- Machine-readable output formats
- Parallel execution support
- Environment variable configuration

### 5. Developer Experience
- Rich terminal output by default
- Comprehensive error messages
- Easy debugging with verbose modes
- Clear documentation

## Extension Points

### Adding a New Test Framework

1. Create `new_framework_integration.py`:
```python
class NewFrameworkRunner(TestRunner):
    def discover_tests(self, config: TestConfig) -> List[str]:
        # Implementation
        pass
    
    def run_tests(self, tests: List[str], config: TestConfig) -> TestResults:
        # Implementation
        pass
```

2. Update `run_all_tests.py`:
```python
if args.framework in ["newframework", "all"]:
    runner = NewFrameworkRunner()
    tests = runner.discover_tests(config)
    results = runner.run_tests(tests, config)
```

### Adding Output Formats

1. Implement formatting method in runner
2. Add format option to TestConfig
3. Update display logic in run_all_tests.py

### Custom Test Discovery

Override `discover_tests()` in framework runner to implement custom test discovery logic.

## Performance Considerations

### Parallel Execution
- Pytest: Native support via pytest-xdist
- Unittest: Can be added via custom runner
- Configurable worker count

### Caching
- Test results not cached (ensures fresh runs)
- Dependencies cached in CI/CD
- Snapshot comparisons are fast

### Resource Management
- Subprocess timeout protection (120s default)
- Proper cleanup of temporary files
- Memory-efficient result aggregation

## Security Considerations

### Input Validation
- Command-line arguments validated
- File paths sanitized
- Environment variables filtered

### Subprocess Execution
- Controlled command construction
- Output capture with size limits
- Timeout protection

### Sensitive Data
- No credentials in test code
- Environment variables for tokens
- Secure cleanup of temp files

## Maintenance Guidelines

### Regular Tasks
1. Update snapshots when output changes
2. Review and update test coverage
3. Monitor test execution times
4. Update dependencies

### Best Practices
1. Keep test files focused and small
2. Use descriptive test names
3. Document complex test scenarios
4. Maintain backward compatibility

### Troubleshooting
See `TROUBLESHOOTING.md` for common issues and solutions.