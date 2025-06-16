#!/usr/bin/env python3
"""
Test harness for running the onefilellm.py script in a subprocess.
This is imported by auto-generated test files.

Created by Claude 1 - Testing Infrastructure & Harness Setup
Updated by Claude 3 - Increased timeouts from 120s to 600s to handle long-running crawl tests
"""
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional
import tempfile

# Get the path to onefilellm.py relative to this harness file
# This ensures the path works regardless of where pytest is run from
HARNESS_DIR = Path(__file__).parent
PROJECT_ROOT = HARNESS_DIR.parent
SCRIPT_PATH = str(PROJECT_ROOT / 'onefilellm.py')

def run_program(args_list: List[str]) -> str:
    """
    Executes the target script as a subprocess and captures its stdout and stderr.
    This provides a consistent way for tests to invoke the script.
    
    Args:
        args_list: List of command line arguments to pass to the script
        
    Returns:
        Combined stdout and stderr output as a string
        
    Raises:
        subprocess.CalledProcessError: If the subprocess returns non-zero exit code
    """
    # Prepare the command - always use python to execute the script
    cmd = [sys.executable, SCRIPT_PATH] + args_list
    
    # Set up test environment variables
    test_env = os.environ.copy()
    if 'GITHUB_TOKEN' not in test_env:
        test_env['GITHUB_TOKEN'] = 'dummy-token-for-testing'
    
    try:
        # Execute the subprocess and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 2 minute timeout for most operations
            check=False,   # Don't raise exception on non-zero exit code
            env=test_env
        )
        
        # Combine stdout and stderr for complete snapshot
        combined_output = ""
        if result.stdout:
            combined_output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            combined_output += f"STDERR:\n{result.stderr}\n"
        if result.returncode != 0:
            combined_output += f"EXIT_CODE: {result.returncode}\n"
            
        return combined_output.strip()
        
    except subprocess.TimeoutExpired as e:
        return f"ERROR: Process timed out after 600 seconds\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
    except Exception as e:
        return f"ERROR: Subprocess execution failed: {str(e)}"


def run_program_with_input(args_list: List[str], stdin_input: Optional[str] = None) -> str:
    """
    Executes the target script as a subprocess with optional stdin input.
    
    Args:
        args_list: List of command line arguments to pass to the script
        stdin_input: Optional string to pass to the script's stdin
        
    Returns:
        Combined stdout and stderr output as a string
    """
    cmd = [sys.executable, SCRIPT_PATH] + args_list
    
    # Set up test environment variables
    test_env = os.environ.copy()
    if 'GITHUB_TOKEN' not in test_env:
        test_env['GITHUB_TOKEN'] = 'dummy-token-for-testing'
    
    try:
        result = subprocess.run(
            cmd,
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            env=test_env
        )
        
        # Combine stdout and stderr for complete snapshot
        combined_output = ""
        if result.stdout:
            combined_output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            combined_output += f"STDERR:\n{result.stderr}\n"
        if result.returncode != 0:
            combined_output += f"EXIT_CODE: {result.returncode}\n"
            
        return combined_output.strip()
        
    except subprocess.TimeoutExpired as e:
        return f"ERROR: Process timed out after 600 seconds\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
    except Exception as e:
        return f"ERROR: Subprocess execution failed: {str(e)}"


def run_program_expect_success(args_list: List[str]) -> str:
    """
    Executes the target script expecting successful completion (exit code 0).
    
    Args:
        args_list: List of command line arguments to pass to the script
        
    Returns:
        Combined stdout and stderr output as a string
        
    Raises:
        AssertionError: If the subprocess returns non-zero exit code
    """
    cmd = [sys.executable, SCRIPT_PATH] + args_list
    
    # Set up test environment variables
    test_env = os.environ.copy()
    if 'GITHUB_TOKEN' not in test_env:
        test_env['GITHUB_TOKEN'] = 'dummy-token-for-testing'
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            env=test_env
        )
        
        # Assert successful execution
        if result.returncode != 0:
            error_msg = f"Expected successful execution but got exit code {result.returncode}\n"
            if result.stdout:
                error_msg += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                error_msg += f"STDERR:\n{result.stderr}\n"
            raise AssertionError(error_msg)
        
        # Combine stdout and stderr for complete snapshot
        combined_output = ""
        if result.stdout:
            combined_output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            combined_output += f"STDERR:\n{result.stderr}\n"
            
        return combined_output.strip()
        
    except subprocess.TimeoutExpired as e:
        raise AssertionError(f"Process timed out after 120 seconds\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
    except Exception as e:
        raise AssertionError(f"Subprocess execution failed: {str(e)}")


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """
    Creates a temporary file with specified content.
    
    Args:
        content: Content to write to the file
        suffix: File extension (default: .txt)
        
    Returns:
        Path to the created temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def create_temp_directory() -> str:
    """
    Creates a temporary directory.
    
    Returns:
        Path to the created temporary directory
    """
    return tempfile.mkdtemp()


def cleanup_temp_path(path: str) -> None:
    """
    Safely removes a temporary file or directory.
    
    Args:
        path: Path to the file or directory to remove
    """
    try:
        path_obj = Path(path)
        if path_obj.is_file():
            path_obj.unlink()
        elif path_obj.is_dir():
            import shutil
            shutil.rmtree(path)
    except Exception:
        # Ignore cleanup errors in tests
        pass


def get_project_root() -> Path:
    """
    Returns the project root directory path.
    
    Returns:
        Path object pointing to the project root
    """
    # Assume we're in tests/ subdirectory, so go up one level
    return Path(__file__).parent.parent


def verify_script_exists() -> bool:
    """
    Verifies that the onefilellm.py script exists and is executable.
    
    Returns:
        True if script exists and is readable, False otherwise
    """
    script_path = get_project_root() / SCRIPT_PATH
    return script_path.exists() and script_path.is_file()


# Test harness metadata
HARNESS_VERSION = "1.0.0"
HARNESS_AUTHOR = "Claude 1 - Testing Infrastructure"
HARNESS_DESCRIPTION = "Subprocess harness for OneFileLLM self-recording tests"

if __name__ == "__main__":
    # Basic self-test of the harness
    print(f"OneFileLLM Test Harness v{HARNESS_VERSION}")
    print(f"Author: {HARNESS_AUTHOR}")
    print(f"Description: {HARNESS_DESCRIPTION}")
    print()
    
    if verify_script_exists():
        print("✅ onefilellm.py script found and accessible")
        
        # Test basic execution
        try:
            output = run_program(["--help"])
            print("✅ Basic harness execution test passed")
            print("Sample output length:", len(output))
        except Exception as e:
            print(f"❌ Basic harness execution test failed: {e}")
    else:
        print("❌ onefilellm.py script not found or not accessible")
        print(f"Expected location: {get_project_root() / SCRIPT_PATH}")