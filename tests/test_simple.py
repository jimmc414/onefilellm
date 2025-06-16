#!/usr/bin/env python3
"""
Simple test to check basic imports and functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing basic imports...")

try:
    # Test direct imports
    import onefilellm
    print("✓ onefilellm module imported")
    
    import utils
    print("✓ utils module imported")
    
    # Test specific imports
    from onefilellm import AliasManager, CORE_ALIASES
    print("✓ AliasManager and CORE_ALIASES imported")
    
    # Test compatibility package
    import onefilellm_compat
    print("✓ onefilellm_compat imported")
    
    # Test modular imports through compatibility
    from onefilellm_compat.core.processor_claude2 import CoreProcessor
    print("✓ CoreProcessor imported through compatibility")
    
    from onefilellm_compat.aliases.manager import AliasManager as AliasManager2
    print("✓ AliasManager imported through modular path")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"\n✗ Import failed: {e}")
    import traceback
    traceback.print_exc()