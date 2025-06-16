"""Stream source processors compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from utils import read_from_stdin, read_from_clipboard

class StdinProcessor:
    """Processor for stdin input"""
    def process(self, input_data=None, context=None):
        return read_from_stdin()

class ClipboardProcessor:
    """Processor for clipboard input"""
    def process(self, input_data=None, context=None):
        return read_from_clipboard()

class StringProcessor:
    """Processor for string input"""
    def process(self, input_string, context=None):
        return input_string

__all__ = ['StdinProcessor', 'ClipboardProcessor', 'StringProcessor']