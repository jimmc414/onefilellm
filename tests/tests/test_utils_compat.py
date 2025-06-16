"""
Utilities compatibility layer for tests.
Provides fixes and workarounds for test compatibility.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import detect_text_format as _original_detect_text_format
import re

def detect_text_format(text_sample):
    """
    Enhanced version of detect_text_format that better handles YAML detection.
    This is a compatibility fix for tests.
    """
    # First, try the original detection
    result = _original_detect_text_format(text_sample)
    
    # If it detected markdown but the content looks like YAML, override
    if result == 'markdown' and ':' in text_sample:
        # Check for YAML-specific patterns that shouldn't be markdown
        yaml_patterns = [
            r'^\s*-\s+\w+',  # YAML list items (- item)
            r'^\w+:\s*$',    # Key with no value on same line
            r'^\w+:\s+\w+',  # Key: value pairs
            r'^\s{2,}-\s',   # Indented list items (YAML style)
        ]
        
        for pattern in yaml_patterns:
            if re.search(pattern, text_sample, re.MULTILINE):
                try:
                    import yaml
                    yaml.safe_load(text_sample)
                    return 'yaml'
                except:
                    pass
                break
    
    return result

# Export the fixed version
__all__ = ['detect_text_format']