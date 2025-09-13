"""
Utility functions for OneFileLLM.

This module contains common utilities used across the application including:
- File I/O operations
- Text format detection and parsing
- Network operations
- Path and file type validation
"""

import os
import sys
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import Union, Optional
import pyperclip
from bs4 import BeautifulSoup

# Try to import yaml, but don't fail if not available
try:
    import yaml
except ImportError:
    yaml = None


# ===== File I/O Utilities =====

def safe_file_read(filepath: str, fallback_encoding: str = 'latin1') -> str:
    """
    Safely read a file with UTF-8 encoding, falling back to another encoding if needed.
    
    Args:
        filepath: Path to the file to read
        fallback_encoding: Encoding to use if UTF-8 fails
        
    Returns:
        Contents of the file as a string
    """
    try:
        with open(filepath, "r", encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding=fallback_encoding) as file:
            return file.read()


def read_from_clipboard() -> Optional[str]:
    """
    Retrieves text content from the system clipboard.
    
    Returns:
        The text content from the clipboard, or None if empty or error.
    """
    try:
        clipboard_content = pyperclip.paste()
        if clipboard_content and clipboard_content.strip():
            return clipboard_content
        else:
            return None
    except pyperclip.PyperclipException as e:
        print(f"[DEBUG] PyperclipException in read_from_clipboard: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[DEBUG] Unexpected error in read_from_clipboard: {e}", file=sys.stderr)
        return None


def read_from_stdin() -> Optional[str]:
    """
    Reads all available text from standard input (sys.stdin).
    
    Returns:
        The text content read from stdin, or None if no data is piped.
    """
    if sys.stdin.isatty():
        # stdin is connected to a terminal, not a pipe
        return None
    
    try:
        # Read all stdin content
        stdin_content = sys.stdin.read()
        if stdin_content:
            return stdin_content
        else:
            return None
    except Exception as e:
        print(f"[DEBUG] Error reading from stdin: {e}", file=sys.stderr)
        return None


# ===== Text Format Detection and Parsing =====

def detect_text_format(text_sample: str) -> str:
    """
    Attempts to detect the format of the input text.
    
    Args:
        text_sample: A sample of the text (first 1000 chars recommended)
        
    Returns:
        Detected format: 'json', 'yaml', 'html', 'markdown', or 'text'
    """
    # Check for empty input
    if not text_sample or not text_sample.strip():
        return 'text'
    
    text_sample = text_sample.strip()
    
    # JSON detection
    if (text_sample.startswith('{') and text_sample.endswith('}')) or \
       (text_sample.startswith('[') and text_sample.endswith(']')):
        try:
            import json
            json.loads(text_sample)
            return 'json'
        except:
            pass
    
    # YAML detection
    if yaml and ':' in text_sample:
        try:
            yaml.safe_load(text_sample)
            if '\n' in text_sample and not text_sample.startswith('<'):
                return 'yaml'
        except:
            pass
    
    # HTML detection
    if text_sample.startswith('<!DOCTYPE') or text_sample.startswith('<html'):
        return 'html'
    
    # More lenient HTML detection
    if '<' in text_sample and '>' in text_sample:
        tag_pattern = r'<[^>]+>'
        # Even a single well-formed tag should be detected as HTML
        if len(re.findall(tag_pattern, text_sample)) >= 1:
            return 'html'
    
    # Markdown detection
    markdown_patterns = [
        r'^#{1,6}\s',          # Headers
        r'\*\*[^*]+\*\*',      # Bold
        r'\*[^*]+\*',          # Italic
        r'\[([^\]]+)\]\([^)]+\)',  # Links
        r'^\s*[-*+]\s',        # Lists
        r'^\s*\d+\.\s',        # Numbered lists
        r'^```',               # Code blocks
        r'`[^`]+`',            # Inline code
    ]
    
    for pattern in markdown_patterns:
        if re.search(pattern, text_sample, re.MULTILINE):
            return 'markdown'
    
    # Default to plain text
    return 'text'


def parse_as_plaintext(text_content: str) -> str:
    """Parse content as plain text (basically unchanged)."""
    return text_content


def parse_as_markdown(text_content: str) -> str:
    """Parse content as markdown (currently unchanged, could be enhanced)."""
    return text_content


def parse_as_json(text_content: str) -> str:
    """Validate JSON content and return it unchanged if valid."""
    import json
    # This will raise JSONDecodeError if invalid
    json.loads(text_content)
    # Return the original content unchanged
    return text_content


def parse_as_html(text_content: str) -> str:
    """Parse HTML content and extract text."""
    soup = BeautifulSoup(text_content, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    # Get text
    text = soup.get_text()
    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    # Drop blank lines
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Join with newlines
    return '\n'.join(chunk for chunk in chunks if chunk)


def parse_as_yaml(text_content: str) -> str:
    """Validate YAML content and return it unchanged if valid."""
    if yaml:
        # This will raise YAMLError if invalid
        yaml.safe_load(text_content)
        # Return the original content unchanged
        return text_content
    else:
        # If yaml not available, return as-is
        return text_content


# ===== Network Utilities =====

def download_file(url: str, target_path: str) -> None:
    """
    Download a file from a URL to a local path.
    
    Args:
        url: URL to download from
        target_path: Local path to save the file
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        with requests.get(url, headers=headers, timeout=30, stream=True) as response:
            response.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    except requests.RequestException as e:
        print(f"Error downloading file from {url}: {e}")


def is_same_domain(base_url: str, new_url: str) -> bool:
    """Check if two URLs are from the same domain."""
    return urlparse(base_url).netloc == urlparse(new_url).netloc


def is_within_depth(base_url: str, current_url: str, max_depth: int) -> bool:
    """Check if a URL is within the allowed crawl depth from base URL."""
    base_path = urlparse(base_url).path.rstrip('/')
    current_path = urlparse(current_url).path.rstrip('/')
    
    # Ensure current path starts with base path
    if not current_path.startswith(base_path):
        return False
        
    base_depth = len(base_path.split('/')) if base_path else 0
    current_depth = len(current_path.split('/')) if current_path else 0
    
    return (current_depth - base_depth) <= max_depth


# ===== Path and File Type Utilities =====

def is_excluded_file(filename: str) -> bool:
    """
    Check if a file should be excluded based on common patterns.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file should be excluded, False otherwise
    """
    excluded_patterns = [
        r'\.pb\.go$',          # Protocol buffer generated files
        r'\.pb\.gw\.go$',      # Protocol buffer gateway files
        r'_test\.go$',         # Go test files
        r'\.min\.js$',         # Minified JavaScript
        r'\.min\.css$',        # Minified CSS
        r'__pycache__',        # Python cache
        r'\.pyc$',             # Python compiled files
        r'node_modules',       # Node.js modules
        r'vendor/',            # Vendor directories
        r'\.git/',             # Git directory
        r'dist/',              # Distribution directories
        r'build/',             # Build directories
    ]
    
    for pattern in excluded_patterns:
        if re.search(pattern, filename):
            return True
    return False


def is_allowed_filetype(filename: str) -> bool:
    """
    Check if a file type is allowed for processing.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file type is allowed, False otherwise
    """
    allowed_extensions = [
        '.py', '.txt', '.js', '.rst', '.sh', '.md', '.pyx', '.html', '.yaml',
        '.json', '.jsonl', '.ipynb', '.h', '.c', '.sql', '.csv', '.go', '.java',
        '.cpp', '.hpp', '.cs', '.php', '.rb', '.swift', '.kt', '.ts', '.tsx',
        '.jsx', '.vue', '.r', '.m', '.scala', '.rs', '.dart', '.lua', '.pl',
        '.jl', '.mat', '.asm', '.s', '.pas', '.fs', '.ml', '.ex', '.clj',
        '.hs', '.lsp', '.scm', '.nim', '.zig', '.d', '.ada', '.f90', '.cob',
        '.vb', '.pro', '.v', '.sv', '.vhdl', '.tcl', '.elm', '.erl', '.hrl',
        '.idr', '.agda', '.lean', '.coq', '.thy', '.sml', '.rkt', '.el', '.vim',
        '.tex', '.bib', '.org', '.adoc', '.pod', '.rdoc', '.textile', '.wiki',
        '.mediawiki', '.creole', '.mw', '.twiki', '.pmwiki', '.trac', '.doku',
        '.cfg', '.conf', '.config', '.ini', '.toml', '.properties', '.env',
        '.example', '.sample', '.default', '.dist', '.in', '.tpl', '.template'
    ]
    
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)


def escape_xml(text: str) -> str:
    """
    Escape text for XML. Currently returns text unchanged as per design decision.
    
    The output format preserves code readability by not escaping XML special characters
    within content tags. This is intentional for better LLM interpretation.
    """
    return text


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename."""
    return Path(filename).suffix.lower()


def is_binary_file(filepath: str) -> bool:
    """
    Check if a file is likely to be binary.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(8192)  # Read first 8KB
            # Check for null bytes which indicate binary
            return b'\x00' in chunk
    except:
        return True  # If we can't read it, assume binary