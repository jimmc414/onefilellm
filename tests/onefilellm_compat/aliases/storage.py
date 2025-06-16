"""Alias storage compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import ensure_alias_dir_exists, ALIAS_CONFIG_DIR, USER_ALIASES_PATH

__all__ = ['ensure_alias_dir_exists', 'ALIAS_CONFIG_DIR', 'USER_ALIASES_PATH']