"""Local file/folder processors compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import process_local_folder, process_ipynb_file, excel_to_markdown
from utils import safe_file_read, is_allowed_filetype, is_excluded_file, get_file_extension, is_binary_file

class LocalFileProcessor:
    """Processor for local files"""
    def process(self, file_path, context=None):
        return safe_file_read(file_path)

class LocalFolderProcessor:
    """Processor for local folders"""
    def process(self, folder_path, context=None):
        return process_local_folder(folder_path)

__all__ = [
    'LocalFileProcessor', 'LocalFolderProcessor',
    'safe_file_read', 'is_allowed_filetype', 'is_excluded_file',
    'excel_to_markdown', 'process_ipynb_file',
    'get_file_extension', 'is_binary_file'
]