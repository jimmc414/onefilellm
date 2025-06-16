#!/usr/bin/env python3
"""
Script to add pytest markers to test files based on their type.
This helps categorize tests for selective execution.
"""

import os
import re
from pathlib import Path


def add_markers_to_test_file(filepath, markers):
    """Add pytest markers to a test class."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if markers already exist
    if any(f"@pytest.mark.{marker}" in content for marker in markers):
        return False
    
    # Find the class definition
    class_match = re.search(r'^class\s+Test\w+.*?:\s*$', content, re.MULTILINE)
    if not class_match:
        return False
    
    # Prepare marker decorators
    marker_lines = '\n'.join(f"@pytest.mark.{marker}" for marker in markers)
    
    # Insert markers before the class definition
    class_start = class_match.start()
    line_start = content.rfind('\n', 0, class_start) + 1
    
    new_content = (
        content[:line_start] +
        marker_lines + '\n' +
        content[line_start:]
    )
    
    with open(filepath, 'w') as f:
        f.write(new_content)
    
    return True


def categorize_and_mark_tests():
    """Categorize test files and add appropriate markers."""
    tests_dir = Path(__file__).parent
    
    # Define test categories and their markers
    test_categories = {
        'crawl': {
            'pattern': r'test_recorded_crawl_.*\.py',
            'markers': ['slow', 'network', 'crawl', 'integration']
        },
        'web': {
            'pattern': r'test_recorded_web_.*\.py',
            'markers': ['network', 'integration']
        },
        'github': {
            'pattern': r'test_recorded_github_.*\.py',
            'markers': ['network', 'github', 'integration']
        },
        'alias': {
            'pattern': r'test_recorded_alias_.*\.py',
            'markers': ['unit', 'alias']
        },
        'local': {
            'pattern': r'test_recorded_(local|dir|file)_.*\.py',
            'markers': ['unit']
        },
        'stdin': {
            'pattern': r'test_recorded_stdin_.*\.py',
            'markers': ['unit', 'cli']
        },
        'format': {
            'pattern': r'test_recorded_format_.*\.py',
            'markers': ['unit']
        },
        'help': {
            'pattern': r'test_recorded_help_.*\.py',
            'markers': ['unit', 'cli']
        }
    }
    
    updated_files = []
    
    for test_file in tests_dir.glob('test_recorded_*.py'):
        filename = test_file.name
        
        # Determine which category this test belongs to
        for category, info in test_categories.items():
            if re.match(info['pattern'], filename):
                if add_markers_to_test_file(test_file, info['markers']):
                    updated_files.append((filename, info['markers']))
                break
    
    return updated_files


if __name__ == '__main__':
    print("Adding pytest markers to test files...")
    updated = categorize_and_mark_tests()
    
    if updated:
        print(f"\nUpdated {len(updated)} test files:")
        for filename, markers in updated:
            print(f"  {filename}: {', '.join(markers)}")
    else:
        print("No test files needed updating (markers may already be present)")
    
    print("\nDone! You can now run tests by category:")
    print("  pytest -m unit          # Fast unit tests only")
    print("  pytest -m 'not slow'    # Skip slow tests")
    print("  pytest -m crawl         # Only crawl tests")
    print("  pytest -m 'not network' # Skip network tests")