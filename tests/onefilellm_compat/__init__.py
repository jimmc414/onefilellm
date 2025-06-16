"""
Compatibility package that provides the expected modular structure for tests
while mapping to the actual monolithic onefilellm.py implementation.
"""

import sys
import os

# Add parent directories to path
test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_dir = os.path.dirname(test_dir)
sys.path.insert(0, project_dir)

# Now import the actual implementation
import onefilellm as _onefilellm_module
import utils as _utils_module

# Re-export everything from the original modules
from onefilellm import *
from utils import *

# Set up the module structure that tests expect
__all__ = ['core', 'aliases', 'sources', 'crawlers']