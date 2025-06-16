"""Configuration compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import CORE_ALIASES, ENABLE_COMPRESSION_AND_NLTK, TOKEN_ESTIMATE_MULTIPLIER, EXCLUDED_DIRS

class Configuration:
    """Configuration management for onefilellm"""
    def __init__(self):
        self.enable_compression = ENABLE_COMPRESSION_AND_NLTK
        self.token_multiplier = TOKEN_ESTIMATE_MULTIPLIER
        self.excluded_dirs = EXCLUDED_DIRS
        self.allowed_extensions = ['.py', '.txt', '.js', '.rst', '.sh', '.md', '.pyx', 
                                  '.html', '.yaml','.json', '.jsonl', '.ipynb', 
                                  '.h', '.c', '.sql', '.csv']

# Re-export CORE_ALIASES
__all__ = ['Configuration', 'CORE_ALIASES']