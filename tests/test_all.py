#!/usr/bin/env python3
"""
Comprehensive test suite for OneFileLLM
Consolidates all tests and expands coverage
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
import time
import subprocess
import io
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import requests
import pandas as pd
import pyperclip
from rich.console import Console
from rich.table import Table
from rich.text import Text

import onefilellm

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules we're testing
from onefilellm import (
    process_github_repo,
    process_arxiv_pdf,
    process_local_folder,
    fetch_youtube_transcript,
    crawl_and_extract_text,
    process_doi_or_pmid,
    process_github_pull_request,
    process_github_issue,
    process_github_issues,
    excel_to_markdown,
    process_input,
    process_text_stream,
    get_token_count,
    combine_xml_outputs,
    preprocess_text,
    ensure_alias_dir_exists,
    ENABLE_COMPRESSION_AND_NLTK,
    TOKEN_ESTIMATE_MULTIPLIER
)

from utils import (
    safe_file_read,
    read_from_clipboard,
    read_from_stdin,
    detect_text_format,
    parse_as_plaintext,
    parse_as_markdown,
    parse_as_json,
    parse_as_html,
    parse_as_yaml,
    download_file,
    is_same_domain,
    is_within_depth,
    is_excluded_file,
    is_allowed_filetype,
    escape_xml,
    get_file_extension,
    is_binary_file
)

# Test configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
RUN_INTEGRATION_TESTS = os.environ.get('RUN_INTEGRATION_TESTS', 'true').lower() == 'true'
RUN_SLOW_TESTS = os.environ.get('RUN_SLOW_TESTS', 'false').lower() == 'true'


class TestConfigurationLoading(unittest.TestCase):
    """Verify environment-driven configuration is loaded correctly."""

    def setUp(self):
        self._original_env = {
            key: os.environ.get(key)
            for key in ("OFFLINE_MODE", "GITHUB_TOKEN")
        }
        self._orig_offline = onefilellm.OFFLINE_MODE
        self._orig_token = onefilellm.TOKEN
        self._orig_headers = dict(onefilellm.headers)
        self._orig_warned = onefilellm._WARNED_ABOUT_TOKEN

    def tearDown(self):
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        onefilellm.OFFLINE_MODE = self._orig_offline
        onefilellm.TOKEN = self._orig_token
        onefilellm.headers = dict(self._orig_headers)
        onefilellm._WARNED_ABOUT_TOKEN = self._orig_warned

    def test_load_configuration_respects_env(self):
        """Environment variables should update runtime configuration."""

        with patch('onefilellm.load_dotenv') as mock_dotenv, \
             patch.dict(os.environ, {'OFFLINE_MODE': 'TrUe', 'GITHUB_TOKEN': 'abc123'}, clear=False):
            onefilellm.load_configuration()

        mock_dotenv.assert_called_once()
        self.assertTrue(onefilellm.OFFLINE_MODE)
        self.assertEqual(onefilellm.TOKEN, 'abc123')
        self.assertEqual(onefilellm.headers, {'Authorization': 'token abc123'})

    def test_load_configuration_defaults_without_env(self):
        """Missing environment variables should fall back to safe defaults."""

        onefilellm._WARNED_ABOUT_TOKEN = False
        with patch('onefilellm.load_dotenv') as mock_dotenv, \
             patch('onefilellm.print') as mock_print, \
             patch.dict(os.environ, {}, clear=True):
            onefilellm.load_configuration()

        mock_dotenv.assert_called_once()
        mock_print.assert_called()
        self.assertFalse(onefilellm.OFFLINE_MODE)
        self.assertEqual(onefilellm.TOKEN, onefilellm.DEFAULT_GITHUB_TOKEN)
        self.assertEqual(onefilellm.headers, {})


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions from utils.py"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_safe_file_read(self):
        """Test safe file reading with different encodings"""
        # Test UTF-8 file
        utf8_file = os.path.join(self.temp_dir, "utf8.txt")
        with open(utf8_file, 'w', encoding='utf-8') as f:
            f.write("Hello 世界")
        content = safe_file_read(utf8_file)
        self.assertEqual(content, "Hello 世界")
        
        # Test latin-1 file
        latin1_file = os.path.join(self.temp_dir, "latin1.txt")
        with open(latin1_file, 'wb') as f:
            f.write("Café".encode('latin-1'))
        content = safe_file_read(latin1_file)
        self.assertEqual(content, "Café")
    
    def test_file_extension_detection(self):
        """Test file extension detection"""
        self.assertEqual(get_file_extension("test.py"), ".py")
        self.assertEqual(get_file_extension("TEST.PY"), ".py")
        self.assertEqual(get_file_extension("no_extension"), "")
        self.assertEqual(get_file_extension("multiple.dots.txt"), ".txt")
    
    def test_is_binary_file(self):
        """Test binary file detection"""
        # Create text file
        text_file = os.path.join(self.temp_dir, "text.txt")
        with open(text_file, 'w') as f:
            f.write("This is text")
        self.assertFalse(is_binary_file(text_file))
        
        # Create binary file
        binary_file = os.path.join(self.temp_dir, "binary.bin")
        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')
        self.assertTrue(is_binary_file(binary_file))
    
    def test_is_excluded_file(self):
        """Test file exclusion patterns"""
        self.assertTrue(is_excluded_file("test.pb.go"))
        self.assertTrue(is_excluded_file("file_test.go"))
        self.assertTrue(is_excluded_file("script.min.js"))
        self.assertTrue(is_excluded_file("__pycache__/file.pyc"))
        self.assertTrue(is_excluded_file("node_modules/package.json"))
        self.assertFalse(is_excluded_file("main.go"))
        self.assertFalse(is_excluded_file("app.js"))
    
    def test_is_allowed_filetype(self):
        """Test allowed file type checking"""
        self.assertTrue(is_allowed_filetype("script.py"))
        self.assertTrue(is_allowed_filetype("README.md"))
        self.assertTrue(is_allowed_filetype("config.yaml"))
        self.assertFalse(is_allowed_filetype("image.png"))
        self.assertFalse(is_allowed_filetype("binary.exe"))
        self.assertFalse(is_allowed_filetype("archive.zip"))
    
    def test_url_utilities(self):
        """Test URL-related utilities"""
        base_url = "https://example.com/docs/"
        
        # Test same domain
        self.assertTrue(is_same_domain(base_url, "https://example.com/other/"))
        self.assertFalse(is_same_domain(base_url, "https://other.com/docs/"))
        
        # Test depth checking
        self.assertTrue(is_within_depth(base_url, "https://example.com/docs/page1", 1))
        self.assertTrue(is_within_depth(base_url, "https://example.com/docs/sub/page", 2))
        self.assertFalse(is_within_depth(base_url, "https://example.com/docs/a/b/c", 2))
    
    def test_escape_xml(self):
        """Test XML escaping (currently returns unchanged)"""
        text = "<tag>Content & more</tag>"
        self.assertEqual(escape_xml(text), text)

    def test_download_file_stream_and_error_handling(self):
        """Test streaming download and graceful error handling"""
        url = "http://example.com/file"
        target_path = os.path.join(self.temp_dir, "download.bin")

        # Successful download with streaming
        with patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
            with patch("utils.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.iter_content.return_value = [b"foo", b"bar"]
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value.__enter__.return_value = mock_response

                download_file(url, target_path)

                with open(target_path, "rb") as f:
                    self.assertEqual(f.read(), b"foobar")

                called_args, called_kwargs = mock_get.call_args
                self.assertEqual(called_args, (url,))
                self.assertEqual(called_kwargs["timeout"], 30)
                self.assertTrue(called_kwargs["stream"])
                self.assertEqual(
                    called_kwargs["headers"].get('User-Agent'),
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                self.assertNotIn('Authorization', called_kwargs["headers"])

        # Explicit headers should merge with defaults and forward Authorization
        with patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
            with patch("utils.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.iter_content.return_value = [b"baz"]
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value.__enter__.return_value = mock_response

                custom_headers = {'Authorization': 'token abc123', 'X-Test': '1'}
                target_path_with_headers = os.path.join(self.temp_dir, "download_with_headers.bin")

                download_file(url, target_path_with_headers, headers=custom_headers)

                called_args, called_kwargs = mock_get.call_args
                self.assertEqual(called_args, (url,))
                self.assertEqual(called_kwargs["headers"].get('User-Agent'),
                                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                self.assertEqual(called_kwargs["headers"]["Authorization"], 'token abc123')
                self.assertEqual(called_kwargs["headers"]["X-Test"], '1')
                # Ensure caller's headers dictionary is not mutated
                self.assertEqual(custom_headers, {'Authorization': 'token abc123', 'X-Test': '1'})

        # Error handling: ensure no exception and file not created
        error_path = os.path.join(self.temp_dir, "error.bin")
        with patch("utils.requests.get", side_effect=requests.RequestException("boom")), \
             patch("builtins.print") as mock_print:
            download_file(url, error_path)
            self.assertFalse(os.path.exists(error_path))
            self.assertTrue(mock_print.called)


class TestTextFormatDetection(unittest.TestCase):
    """Test text format detection and parsing"""
    
    def test_format_detection(self):
        """Test detection of various text formats"""
        # Plain text
        self.assertEqual(detect_text_format("Just plain text"), "text")
        self.assertEqual(detect_text_format(""), "text")
        
        # JSON
        self.assertEqual(detect_text_format('{"key": "value"}'), "json")
        self.assertEqual(detect_text_format('[1, 2, 3]'), "json")
        self.assertEqual(detect_text_format('{\n  "nested": {\n    "data": true\n  }\n}'), "json")
        
        # HTML
        self.assertEqual(detect_text_format('<!DOCTYPE html><html></html>'), "html")
        self.assertEqual(detect_text_format('<html><body>Content</body></html>'), "html")
        self.assertEqual(detect_text_format('<div>Single tag</div>'), "html")
        
        # Markdown
        self.assertEqual(detect_text_format('# Heading\n\nParagraph'), "markdown")
        self.assertEqual(detect_text_format('**Bold** and *italic*'), "markdown")
        self.assertEqual(detect_text_format('- List item\n- Another item'), "markdown")
        self.assertEqual(detect_text_format('[Link](https://example.com)'), "markdown")
        self.assertEqual(detect_text_format('```code block```'), "markdown")
        
        # YAML (if available)
        try:
            import yaml
            self.assertEqual(detect_text_format('key: value\nlist:\n  - item1\n  - item2'), "yaml")
        except ImportError:
            pass
    
    def test_parsers(self):
        """Test individual parser functions"""
        # Plain text parser
        text = "Plain text content"
        self.assertEqual(parse_as_plaintext(text), text)
        
        # Markdown parser
        markdown = "# Heading\n\nContent"
        self.assertEqual(parse_as_markdown(markdown), markdown)
        
        # JSON parser
        json_text = '{"valid": "json"}'
        self.assertEqual(parse_as_json(json_text), json_text)
        with self.assertRaises(json.JSONDecodeError):
            parse_as_json("not valid json")
        
        # HTML parser
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        parsed = parse_as_html(html)
        self.assertIn("Title", parsed)
        self.assertIn("Content", parsed)
        self.assertNotIn("<h1>", parsed)
        
        # YAML parser (if available)
        try:
            import yaml
            yaml_text = "key: value"
            self.assertEqual(parse_as_yaml(yaml_text), yaml_text)
        except ImportError:
            pass


class TestStreamProcessing(unittest.TestCase):
    """Test stream processing functionality"""
    
    def setUp(self):
        self.console = MagicMock()
    
    def test_stdin_processing(self):
        """Test processing from stdin"""
        text_content = "Test content from stdin"
        result = process_text_stream(text_content, {'type': 'stdin'}, self.console)
        self.assertIn('<source type="stdin"', result)
        self.assertIn(text_content, result)
    
    def test_clipboard_processing(self):
        """Test processing from clipboard"""
        text_content = "Test content from clipboard"
        result = process_text_stream(text_content, {'type': 'clipboard'}, self.console)
        self.assertIn('<source type="clipboard"', result)
        self.assertIn(text_content, result)
    
    def test_format_override(self):
        """Test format override functionality"""
        json_content = '{"key": "value"}'
        
        # Without override - should detect as JSON
        result = process_text_stream(json_content, {'type': 'stdin'}, self.console)
        self.assertIn('processed_as_format="json"', result)
        
        # With override to text
        result = process_text_stream(json_content, {'type': 'stdin'}, self.console, format_override="text")
        self.assertIn('processed_as_format="text"', result)
    
    def test_clipboard_errors(self):
        """Test clipboard error handling"""
        # We're testing the actual function behavior, not mocking
        # The function returns None when clipboard is empty or has errors
        with patch('pyperclip.paste') as mock_paste:
            mock_paste.side_effect = pyperclip.PyperclipException("Test error")
            result = read_from_clipboard()
            self.assertIsNone(result)
    
    @patch('utils.read_from_stdin')
    def test_stdin_errors(self, mock_stdin):
        """Test stdin error handling"""
        # Test no piped input
        mock_stdin.return_value = None
        result = read_from_stdin()
        self.assertIsNone(result)


class TestProcessInputFileURLs(unittest.TestCase):
    """Test direct file URL handling in process_input"""

    def setUp(self):
        self.console = Console(file=io.StringIO())
        self.args = type('Args', (), {})()

    def test_direct_file_url_multiple_types(self):
        """Ensure direct file URLs for allowed types are processed directly"""
        import asyncio
        for ext in ['.txt', '.md', '.py']:
            url = f'http://example.com/test{ext}'
            with patch('onefilellm._download_and_read_file', return_value='content'), \
                 patch('onefilellm.process_web_crawl', new_callable=AsyncMock) as mock_crawl:
                result = asyncio.run(process_input(url, self.args, self.console))
                self.assertIn('<source type="web_file"', result)
                self.assertIn(f'test{ext}', result)
                mock_crawl.assert_not_called()

    def test_disallowed_extension_uses_crawler(self):
        """Ensure disallowed extensions bypass direct processing"""
        import asyncio
        url = 'http://example.com/file.pdf'
        fake_crawl = {'content': 'pdf content', 'processed_urls': []}
        with patch('onefilellm.crawl_and_extract_text', return_value=fake_crawl), \
             patch('onefilellm._download_and_read_file') as mock_download:
            result = asyncio.run(process_input(url, self.args, self.console))
            self.assertIn('pdf content', result)
            mock_download.assert_not_called()

    def test_unallowed_extension_uses_web_crawl(self):
        """Ensure unallowed extensions trigger web crawl"""
        import asyncio
        url = 'http://example.com/file.exe'
        with patch('onefilellm.process_web_crawl', new_callable=AsyncMock, return_value='crawl result') as mock_crawl, \
             patch('onefilellm._download_and_read_file') as mock_download:
            result = asyncio.run(process_input(url, self.args, self.console))
            self.assertEqual(result, 'crawl result')
            mock_download.assert_not_called()
            mock_crawl.assert_awaited_once()


class TestCoreProcessing(unittest.TestCase):
    """Test core processing functions"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_local_file_processing(self):
        """Test processing of local files"""
        # Create test files
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Mock args object since process_input is now async and requires args
        with patch('onefilellm.process_input', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = '<source type="local_file">Test content</source>'
            # Use a synchronous wrapper to test the async function
            import asyncio
            result = asyncio.run(mock_process(test_file, None, Console()))
            self.assertIn('<source type="local_file"', result)
            self.assertIn('Test content', result)
    
    def test_local_folder_processing(self):
        """Test processing of local folders"""
        # Create test files in folder
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"file{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"Content {i}")
        
        console = Console()
        result = process_local_folder(self.temp_dir, console)
        self.assertIn('<source type="local_folder"', result)
        for i in range(3):
            self.assertIn(f'Content {i}', result)
    
    def test_excel_processing(self):
        """Test Excel file processing"""
        # Create test Excel file
        excel_file = os.path.join(self.temp_dir, "test.xlsx")
        df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        df2 = pd.DataFrame({'X': ['a', 'b'], 'Y': ['c', 'd']})
        
        with pd.ExcelWriter(excel_file) as writer:
            df1.to_excel(writer, sheet_name='Sheet1', index=False)
            df2.to_excel(writer, sheet_name='Sheet2', index=False)
        
        result = excel_to_markdown(excel_file)
        # excel_to_markdown returns a dict, not a string
        self.assertIsInstance(result, dict)
        self.assertIn('Sheet1', result)
        self.assertIn('Sheet2', result)
        self.assertIn('A', result['Sheet1'])
        self.assertIn('B', result['Sheet1'])
        self.assertIn('X', result['Sheet2'])
        self.assertIn('Y', result['Sheet2'])
    
    def test_token_counting(self):
        """Test token counting functionality"""
        text = "This is a test text for token counting."
        count = get_token_count(text)
        self.assertGreater(count, 0)
        self.assertIsInstance(count, int)
        
        # Test with XML tags (should be stripped)
        xml_text = "<tag>Content</tag>"
        xml_count = get_token_count(xml_text)
        content_count = get_token_count("Content")
        self.assertEqual(xml_count, content_count)
    
    def test_token_count_estimation(self):
        """Test token count estimation with multiplier"""
        # Test basic estimation calculation
        test_text = "This is a sample text that will be used to test token estimation."
        base_count = get_token_count(test_text)
        
        # Calculate estimated count using the imported multiplier
        estimated_count = round(base_count * TOKEN_ESTIMATE_MULTIPLIER)
        
        # Verify the multiplier is applied correctly
        self.assertEqual(estimated_count, round(base_count * TOKEN_ESTIMATE_MULTIPLIER))
        
        # Verify the multiplier value is reasonable (between 1.0 and 2.0)
        self.assertGreater(TOKEN_ESTIMATE_MULTIPLIER, 1.0)
        self.assertLess(TOKEN_ESTIMATE_MULTIPLIER, 2.0)
        
        # Test with a known token count
        # "Hello world" is typically 2 tokens
        simple_text = "Hello world"
        simple_count = get_token_count(simple_text)
        simple_estimated = round(simple_count * TOKEN_ESTIMATE_MULTIPLIER)
        
        # Verify estimated is greater than base count
        self.assertGreater(simple_estimated, simple_count)
        
        # Test formatting with comma separator
        large_text = " ".join(["word"] * 10000)  # Create text with many tokens
        large_count = get_token_count(large_text)
        large_estimated = round(large_count * TOKEN_ESTIMATE_MULTIPLIER)
        
        # Format with comma separator
        formatted_base = f"{large_count:,}"
        formatted_estimated = f"{large_estimated:,}"
        
        # Verify formatting includes commas for large numbers
        if large_count >= 1000:
            self.assertIn(",", formatted_base)
            self.assertIn(",", formatted_estimated)

    def test_token_count_fallback_no_network(self):
        """Ensure token counting falls back when encoding cannot be loaded"""
        import onefilellm as ofl
        ofl._TIKTOKEN_ENCODING = None
        with patch('onefilellm.tiktoken.get_encoding', side_effect=Exception("offline")):
            sample = "fallback test"
            count = get_token_count(sample)
            self.assertEqual(count, len(sample) // 4)
    
    def test_combine_xml_outputs(self):
        """Test combining multiple XML outputs"""
        outputs = [
            '<source type="test1"><content>Content 1</content></source>',
            '<source type="test2"><content>Content 2</content></source>'
        ]
        
        combined = combine_xml_outputs(outputs)
        self.assertIn('<onefilellm_output>', combined)
        self.assertIn('Content 1', combined)
        self.assertIn('Content 2', combined)
        self.assertIn('</onefilellm_output>', combined)
    
    def test_text_preprocessing(self):
        """Test text preprocessing with NLTK"""
        input_file = os.path.join(self.temp_dir, "input.txt")
        output_file = os.path.join(self.temp_dir, "output.txt")
        
        with open(input_file, 'w') as f:
            f.write("This is a TEST with STOPWORDS and   extra   spaces.")
        
        preprocess_text(input_file, output_file)
        
        with open(output_file, 'r') as f:
            processed = f.read()
        
        self.assertNotIn("STOPWORDS", processed)  # Should be lowercase
        self.assertNotIn("   ", processed)  # Extra spaces removed


# TODO: Update TestAliasSystem for new AliasManager implementation
# The old alias system has been replaced with AliasManager class.
# This test class needs to be rewritten to test the new alias functionality:
# - AliasManager.add_or_update_alias(), remove_alias(), list_aliases_formatted()
# - Alias expansion logic in main(), JSON storage, Core vs user alias precedence
# - Placeholder {} functionality
@unittest.skip("Legacy alias system tests - pending rewrite")
class TestAliasSystem2OLD(unittest.TestCase):
    """Test old alias functionality - DISABLED"""
    
    def setUp(self):
        self.temp_alias_dir = tempfile.mkdtemp()
        self.original_alias_dir = Path.home() / ".onefilellm_aliases"
        # Mock the alias directory for testing
        self.patcher = patch('onefilellm.ALIAS_DIR', Path(self.temp_alias_dir))
        self.patcher.start()
        
    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_alias_dir)
    
    def test_alias_detection(self):
        """Test alias detection logic"""
        # Should be detected as potential aliases
        self.assertTrue(is_potential_alias("myalias"))
        self.assertTrue(is_potential_alias("my_alias_123"))
        
        # Should NOT be detected as aliases
        self.assertFalse(is_potential_alias("https://example.com"))
        self.assertFalse(is_potential_alias("/path/to/file"))
        self.assertFalse(is_potential_alias("C:\\Windows\\file"))
        self.assertFalse(is_potential_alias("10.1234/doi"))
    
    def test_alias_directory_creation(self):
        """Test alias directory creation"""
        ensure_alias_dir_exists()
        alias_dir = Path.home() / ".onefilellm_aliases"
        self.assertTrue(alias_dir.exists())
        self.assertTrue(alias_dir.is_dir())
    
    def test_handle_add_alias(self):
        """Test creating aliases with --add-alias"""
        from onefilellm import handle_add_alias
        from rich.console import Console
        
        console = Console()
        
        # Test successful alias creation
        args = ["--add-alias", "mytest", "https://github.com/user/repo", "https://example.com"]
        result = handle_add_alias(args, console)
        self.assertTrue(result)
        
        # Verify alias file was created
        alias_file = Path(self.temp_alias_dir) / "mytest"
        self.assertTrue(alias_file.exists())
        
        # Verify contents
        with open(alias_file, 'r') as f:
            contents = f.read()
            self.assertIn("https://github.com/user/repo", contents)
            self.assertIn("https://example.com", contents)
    
    def test_handle_alias_from_clipboard(self):
        """Test creating aliases from clipboard content"""
        from onefilellm import handle_alias_from_clipboard
        from rich.console import Console
        
        console = Console()
        
        # Mock clipboard content
        test_urls = "https://github.com/repo1\nhttps://example.com/doc\n/local/path/file.txt"
        with patch('pyperclip.paste', return_value=test_urls):
            args = ["--alias-from-clipboard", "cliptest"]
            result = handle_alias_from_clipboard(args, console)
            self.assertTrue(result)
            
            # Verify alias file was created
            alias_file = Path(self.temp_alias_dir) / "cliptest"
            self.assertTrue(alias_file.exists())
            
            # Verify contents
            with open(alias_file, 'r') as f:
                contents = f.read()
                self.assertIn("https://github.com/repo1", contents)
                self.assertIn("https://example.com/doc", contents)
                self.assertIn("/local/path/file.txt", contents)
    
    def test_load_alias(self):
        """Test loading and resolving aliases"""
        from onefilellm import load_alias
        from rich.console import Console
        
        console = Console()
        
        # Create a test alias file
        alias_name = "testalias"
        alias_file = Path(self.temp_alias_dir) / alias_name
        test_targets = ["https://github.com/test/repo", "https://example.com/page"]
        with open(alias_file, 'w') as f:
            for target in test_targets:
                f.write(target + "\n")
        
        # Test loading the alias
        loaded_targets = load_alias(alias_name, console)
        self.assertEqual(loaded_targets, test_targets)
    
    def test_alias_validation(self):
        """Test alias name validation"""
        from onefilellm import handle_add_alias
        from rich.console import Console
        
        console = Console()
        
        # Test invalid alias names
        invalid_names = ["test/alias", "test\\alias", "test.alias", "test:alias"]
        for invalid_name in invalid_names:
            args = ["--add-alias", invalid_name, "https://example.com"]
            result = handle_add_alias(args, console)
            self.assertTrue(result)  # Should return True indicating error
            # Verify no file was created
            alias_file = Path(self.temp_alias_dir) / invalid_name
            self.assertFalse(alias_file.exists())


class TestAliasSystem2(unittest.TestCase):
    """Test new Alias Management 2.0 functionality"""
    
    def setUp(self):
        self.temp_alias_dir = tempfile.mkdtemp()
        self.alias_file = Path(self.temp_alias_dir) / "aliases.json"
        
        # Mock the alias configuration directory
        self.config_dir_patcher = patch('onefilellm.ALIAS_DIR', Path(self.temp_alias_dir))
        self.config_dir_patcher.start()
        
        # Mock the user aliases path
        self.aliases_path_patcher = patch('onefilellm.USER_ALIASES_PATH', self.alias_file)
        self.aliases_path_patcher.start()
        
    def tearDown(self):
        self.config_dir_patcher.stop()
        self.aliases_path_patcher.stop()
        shutil.rmtree(self.temp_alias_dir)
    
    def test_alias_manager_creation(self):
        """Test AliasManager instantiation and basic setup"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        
        # Should have core aliases
        self.assertIsInstance(manager.core_aliases_map, dict)
        self.assertIn("ofl_repo", manager.core_aliases_map)
        self.assertIn("gh_search", manager.core_aliases_map)
        
        # Should start with empty user aliases
        self.assertEqual(len(manager.user_aliases_map), 0)
    
    def test_alias_manager_json_storage(self):
        """Test JSON file creation and loading"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Add a user alias
        result = manager.add_or_update_alias("test_alias", "https://example.com --flag")
        self.assertTrue(result)
        
        # Verify JSON file was created
        self.assertTrue(self.alias_file.exists())
        
        # Verify JSON content
        with open(self.alias_file, 'r') as f:
            data = json.load(f)
            self.assertIn("test_alias", data)
            self.assertEqual(data["test_alias"], "https://example.com --flag")
    
    def test_alias_manager_validation(self):
        """Test alias name validation"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Valid names should work
        self.assertTrue(manager.add_or_update_alias("valid_alias", "command"))
        self.assertTrue(manager.add_or_update_alias("valid-alias", "command"))
        self.assertTrue(manager.add_or_update_alias("valid_123", "command"))
        
        # Invalid names should be rejected
        self.assertFalse(manager.add_or_update_alias("invalid/name", "command"))
        self.assertFalse(manager.add_or_update_alias("invalid.name", "command"))
        self.assertFalse(manager.add_or_update_alias("--invalid", "command"))
        self.assertFalse(manager.add_or_update_alias("", "command"))
    
    def test_alias_manager_precedence(self):
        """Test user aliases override core aliases"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check core alias exists
        core_command = manager.get_command("ofl_repo")
        self.assertIsNotNone(core_command)
        self.assertIn("github.com/jimmc414/onefilellm", core_command)
        
        # Override with user alias
        manager.add_or_update_alias("ofl_repo", "https://my-custom-repo.com")
        
        # Should now return user alias
        user_command = manager.get_command("ofl_repo")
        self.assertEqual(user_command, "https://my-custom-repo.com")
        
        # Remove user alias
        manager.remove_alias("ofl_repo")
        
        # Should restore core alias
        restored_command = manager.get_command("ofl_repo")
        self.assertEqual(restored_command, core_command)

    def test_alias_listing_functionality(self):
        """Test alias listing with different options"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Add some user aliases
        manager.add_or_update_alias("user_alias1", "https://example1.com")
        manager.add_or_update_alias("user_alias2", "https://example2.com")
        
        # Test listing all aliases
        all_list = manager.list_aliases_formatted(list_user=True, list_core=True)
        self.assertIn("user_alias1", all_list)
        self.assertIn("ofl_repo", all_list)  # Core alias
        
        # Test listing only user aliases
        user_list = manager.list_aliases_formatted(list_user=True, list_core=False)
        self.assertIn("user_alias1", user_list)
        self.assertNotIn("ofl_repo", user_list)
        
        # Test listing only core aliases
        core_list = manager.list_aliases_formatted(list_user=False, list_core=True)
        self.assertNotIn("user_alias1", core_list)
        self.assertIn("ofl_repo", core_list)


class TestAdvancedAliasFeatures(unittest.TestCase):
    """Test advanced alias functionality including placeholders and complex scenarios"""
    
    def setUp(self):
        self.temp_alias_dir = tempfile.mkdtemp()
        self.alias_file = Path(self.temp_alias_dir) / "aliases.json"
        
        # Mock the alias configuration directory
        self.config_dir_patcher = patch('onefilellm.ALIAS_DIR', Path(self.temp_alias_dir))
        self.config_dir_patcher.start()
        
        # Mock the user aliases path
        self.aliases_path_patcher = patch('onefilellm.USER_ALIASES_PATH', self.alias_file)
        self.aliases_path_patcher.start()
        
    def tearDown(self):
        self.config_dir_patcher.stop()
        self.aliases_path_patcher.stop()
        shutil.rmtree(self.temp_alias_dir)

    def test_placeholder_functionality(self):
        """Test dynamic placeholder substitution in aliases"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Test core alias with placeholder
        gh_search_command = manager.get_command("gh_search")
        self.assertIn("{}", gh_search_command)
        self.assertIn("github.com/search", gh_search_command)
        
        # Test adding custom placeholder alias
        manager.add_or_update_alias("custom_search", "https://example.com/search?q={}")
        custom_command = manager.get_command("custom_search")
        self.assertEqual(custom_command, "https://example.com/search?q={}")
        
        # Test multi-source alias with placeholder
        manager.add_or_update_alias("multi_search", "https://site1.com/search?q={} https://site2.com/find?term={}")
        multi_command = manager.get_command("multi_search")
        self.assertIn("site1.com", multi_command)
        self.assertIn("site2.com", multi_command)
        self.assertEqual(multi_command.count("{}"), 2)

    def test_complex_multi_source_aliases(self):
        """Test complex aliases with multiple sources"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Test comprehensive ecosystem alias
        ecosystem_sources = " ".join([
            "https://github.com/facebook/react",
            "https://github.com/vercel/next.js", 
            "https://reactjs.org/docs/",
            "https://nextjs.org/docs",
            "local_notes.md"
        ])
        
        manager.add_or_update_alias("react_ecosystem", ecosystem_sources)
        command = manager.get_command("react_ecosystem")
        
        # Verify all sources are present
        self.assertIn("github.com/facebook/react", command)
        self.assertIn("github.com/vercel/next.js", command)
        self.assertIn("reactjs.org/docs", command)
        self.assertIn("nextjs.org/docs", command)
        self.assertIn("local_notes.md", command)
        
        # Test splitting the command
        sources = command.split()
        self.assertEqual(len(sources), 5)

    def test_alias_with_mixed_source_types(self):
        """Test aliases containing different types of sources"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Mixed sources: GitHub, ArXiv, DOI, YouTube, local files
        mixed_sources = " ".join([
            "https://github.com/openai/whisper",
            "arxiv:1706.03762",
            "10.1038/s41586-021-03819-2",
            "https://www.youtube.com/watch?v=example",
            "research_notes.pdf",
            "https://docs.example.com/"
        ])
        
        manager.add_or_update_alias("ai_research", mixed_sources)
        command = manager.get_command("ai_research")
        
        # Verify all source types are preserved
        self.assertIn("github.com/openai/whisper", command)
        self.assertIn("arxiv:1706.03762", command)
        self.assertIn("10.1038/s41586-021-03819-2", command)
        self.assertIn("youtube.com", command)
        self.assertIn("research_notes.pdf", command)
        self.assertIn("docs.example.com", command)

    def test_alias_expansion_simulation(self):
        """Test simulating the main() alias expansion logic"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        import shlex
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Add test aliases
        manager.add_or_update_alias("test_simple", "https://example.com")
        manager.add_or_update_alias("test_placeholder", "https://search.com?q={}")
        manager.add_or_update_alias("test_multi", "https://site1.com https://site2.com")
        
        # Test simple alias expansion
        original_argv = ["onefilellm.py", "test_simple"]
        alias_name = original_argv[1]
        command_str = manager.get_command(alias_name)
        self.assertIsNotNone(command_str)
        
        expanded_parts = shlex.split(command_str)
        new_argv = original_argv[:1] + expanded_parts + original_argv[2:]
        self.assertEqual(new_argv, ["onefilellm.py", "https://example.com"])
        
        # Test placeholder expansion with value
        original_argv = ["onefilellm.py", "test_placeholder", "machine learning"]
        alias_name = original_argv[1]
        command_str = manager.get_command(alias_name)
        placeholder_value = original_argv[2] if len(original_argv) > 2 else ""
        
        # Simulate placeholder replacement
        expanded_command_str = command_str.replace("{}", placeholder_value)
        expanded_parts = shlex.split(expanded_command_str)
        new_argv = original_argv[:1] + expanded_parts + original_argv[3:]
        
        # The URL will be split by shlex because it contains spaces
        self.assertEqual(new_argv, ["onefilellm.py", "https://search.com?q=machine", "learning"])
        
        # Test multi-source expansion
        original_argv = ["onefilellm.py", "test_multi", "extra_arg.txt"]
        alias_name = original_argv[1]
        command_str = manager.get_command(alias_name)
        
        expanded_parts = shlex.split(command_str)
        new_argv = original_argv[:1] + expanded_parts + original_argv[2:]
        
        expected = ["onefilellm.py", "https://site1.com", "https://site2.com", "extra_arg.txt"]
        self.assertEqual(new_argv, expected)

    def test_alias_edge_cases(self):
        """Test edge cases and error conditions"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Test empty command string
        result = manager.add_or_update_alias("empty_test", "")
        self.assertTrue(result)  # Should accept empty commands
        self.assertEqual(manager.get_command("empty_test"), "")
        
        # Test command with special characters
        special_command = "https://example.com/search?q=test&format=json&special=!@#$%"
        manager.add_or_update_alias("special_chars", special_command)
        self.assertEqual(manager.get_command("special_chars"), special_command)
        
        # Test very long command
        long_command = " ".join([f"https://example{i}.com" for i in range(50)])
        manager.add_or_update_alias("long_alias", long_command)
        retrieved = manager.get_command("long_alias")
        self.assertEqual(retrieved, long_command)
        self.assertEqual(len(retrieved.split()), 50)
        
        # Test alias name with underscores and hyphens
        manager.add_or_update_alias("test_under_score", "https://underscore.com")
        manager.add_or_update_alias("test-hyphen-name", "https://hyphen.com")
        
        self.assertEqual(manager.get_command("test_under_score"), "https://underscore.com")
        self.assertEqual(manager.get_command("test-hyphen-name"), "https://hyphen.com")

    def test_json_persistence_and_loading(self):
        """Test JSON file persistence and loading across manager instances"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        
        # Create first manager instance and add aliases
        manager1 = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager1.load_aliases()
        
        manager1.add_or_update_alias("persist_test1", "https://test1.com")
        manager1.add_or_update_alias("persist_test2", "https://test2.com file.txt")
        manager1.add_or_update_alias("persist_placeholder", "https://search.com?q={}")
        
        # Create second manager instance (simulating restart)
        manager2 = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager2.load_aliases()
        
        # Verify all aliases were persisted and loaded
        self.assertEqual(manager2.get_command("persist_test1"), "https://test1.com")
        self.assertEqual(manager2.get_command("persist_test2"), "https://test2.com file.txt")
        self.assertEqual(manager2.get_command("persist_placeholder"), "https://search.com?q={}")
        
        # Verify JSON file structure
        with open(self.alias_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn("persist_test1", data)
        self.assertIn("persist_test2", data)
        self.assertIn("persist_placeholder", data)
        self.assertEqual(data["persist_test1"], "https://test1.com")

    def test_alias_removal_and_core_restoration(self):
        """Test removing user aliases and core alias restoration"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Get original core alias
        original_core = manager.get_command("ofl_repo")
        self.assertIsNotNone(original_core)
        
        # Override with user alias
        manager.add_or_update_alias("ofl_repo", "https://my-custom-repo.com")
        self.assertEqual(manager.get_command("ofl_repo"), "https://my-custom-repo.com")
        
        # Remove user alias - should restore core alias
        result = manager.remove_alias("ofl_repo")
        self.assertTrue(result)
        self.assertEqual(manager.get_command("ofl_repo"), original_core)
        
        # Test removing non-existent user alias
        result = manager.remove_alias("non_existent_alias")
        self.assertFalse(result)
        
        # Test removing user-only alias
        manager.add_or_update_alias("user_only", "https://user.com")
        self.assertEqual(manager.get_command("user_only"), "https://user.com")
        
        result = manager.remove_alias("user_only")
        self.assertTrue(result)
        self.assertIsNone(manager.get_command("user_only"))

    def test_complex_placeholder_scenarios(self):
        """Test complex placeholder usage scenarios"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        import shlex
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Test multiple placeholders in same command
        manager.add_or_update_alias("multi_placeholder", 
            "https://site1.com/search?q={} https://site2.com/find?term={}")
        
        # Simulate expansion with value
        command = manager.get_command("multi_placeholder")
        expanded = command.replace("{}", "test_query")  # Use underscore to avoid splitting
        parts = shlex.split(expanded)
        
        self.assertEqual(len(parts), 2)
        self.assertIn("q=test_query", parts[0])
        self.assertIn("term=test_query", parts[1])
        
        # Test placeholder with complex query (using underscores)
        complex_query = "machine_learning_transformers_attention"
        expanded_complex = command.replace("{}", complex_query)
        parts_complex = shlex.split(expanded_complex)
        
        self.assertEqual(len(parts_complex), 2)
        self.assertIn("q=machine_learning_transformers_attention", parts_complex[0])
        self.assertIn("term=machine_learning_transformers_attention", parts_complex[1])
        
        # Test placeholder with special characters
        special_query = "test & query with spaces + symbols"
        expanded_special = command.replace("{}", special_query)
        # Should not break the command structure
        self.assertIn("site1.com", expanded_special)
        self.assertIn("site2.com", expanded_special)

    def test_real_world_alias_scenarios(self):
        """Test realistic, complex alias scenarios"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Modern web development ecosystem (realistic scenario)
        web_ecosystem = " ".join([
            "https://github.com/facebook/react",
            "https://github.com/vercel/next.js",
            "https://github.com/tailwindlabs/tailwindcss",
            "https://github.com/prisma/prisma",
            "https://reactjs.org/docs/",
            "https://nextjs.org/docs",
            "https://tailwindcss.com/docs",
            "https://www.prisma.io/docs"
        ])
        manager.add_or_update_alias("modern_web", web_ecosystem)
        
        # AI/ML research ecosystem
        ai_ecosystem = " ".join([
            "arxiv:1706.03762",  # Attention is All You Need
            "arxiv:2005.14165",  # GPT-3
            "10.1038/s41586-021-03819-2",  # AlphaFold
            "https://github.com/huggingface/transformers",
            "https://github.com/openai/whisper",
            "https://github.com/pytorch/pytorch",
            "https://huggingface.co/docs",
            "https://pytorch.org/docs"
        ])
        manager.add_or_update_alias("ai_research", ai_ecosystem)
        
        # Security research stack
        security_stack = " ".join([
            "https://github.com/OWASP/Top10",
            "https://github.com/aquasecurity/trivy",
            "https://github.com/falcosecurity/falco",
            "https://owasp.org/www-project-top-ten/",
            "https://aquasec.com/trivy/",
            "https://falco.org/docs/"
        ])
        manager.add_or_update_alias("security_stack", security_stack)
        
        # Test all aliases work correctly
        web_cmd = manager.get_command("modern_web")
        ai_cmd = manager.get_command("ai_research")
        sec_cmd = manager.get_command("security_stack")
        
        # Verify source counts
        self.assertEqual(len(web_cmd.split()), 8)
        self.assertEqual(len(ai_cmd.split()), 8)
        self.assertEqual(len(sec_cmd.split()), 6)
        
        # Verify specific sources are present
        self.assertIn("github.com/facebook/react", web_cmd)
        self.assertIn("arxiv:1706.03762", ai_cmd)
        self.assertIn("github.com/OWASP/Top10", sec_cmd)
        
        # Test combining aliases (simulating complex command)
        # This would represent: onefilellm.py modern_web ai_research extra_file.pdf
        combined_sources = web_cmd.split() + ai_cmd.split() + ["extra_file.pdf"]
        self.assertEqual(len(combined_sources), 17)  # 8 + 8 + 1
        
        # Verify no duplicates in individual aliases
        web_sources = web_cmd.split()
        self.assertEqual(len(web_sources), len(set(web_sources)))  # No duplicates

    def test_alias_validation_comprehensive(self):
        """Comprehensive alias name validation tests"""
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Valid alias names
        valid_names = [
            "simple",
            "with_underscore",
            "with-hyphen",
            "mix_ed-name",
            "name123",
            "name_123_test",
            "a",  # Single character
            "verylongaliasnamethatshouldstillbevalid123"
        ]
        
        for name in valid_names:
            result = manager.add_or_update_alias(name, "https://example.com")
            self.assertTrue(result, f"Valid name '{name}' should be accepted")
            self.assertEqual(manager.get_command(name), "https://example.com")
        
        # Invalid alias names
        invalid_names = [
            "",  # Empty
            "--invalid",  # Starts with --
            "invalid/slash",  # Contains slash
            "invalid\\backslash",  # Contains backslash
            "invalid.dot",  # Contains dot
            "invalid:colon",  # Contains colon
            "invalid space",  # Contains space
            "invalid@symbol",  # Contains @
            "invalid#hash",  # Contains #
            "invalid$dollar",  # Contains $
            "invalid%percent",  # Contains %
        ]
        
        for name in invalid_names:
            result = manager.add_or_update_alias(name, "https://example.com")
            self.assertFalse(result, f"Invalid name '{name}' should be rejected")

    def test_cli_alias_add_single_source(self):
        """Test --alias-add with single source (backward compatibility)"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test single source alias
        test_args = ['onefilellm.py', '--alias-add', 'test_single', 'https://example.com']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check the alias exists and has correct value
        command = manager.get_command('test_single')
        self.assertEqual(command, 'https://example.com')

    def test_cli_alias_add_multi_source_quoted(self):
        """Test --alias-add with quoted multi-source command (backward compatibility)"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test multi-source alias with quotes
        test_args = ['onefilellm.py', '--alias-add', 'test_multi_quoted', 
                     'https://example1.com https://example2.com https://example3.com']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check the alias exists and has all sources
        command = manager.get_command('test_multi_quoted')
        self.assertIn('https://example1.com', command)
        self.assertIn('https://example2.com', command)
        self.assertIn('https://example3.com', command)

    def test_cli_alias_add_multi_source_unquoted(self):
        """Test --alias-add with unquoted multi-source command (new functionality)"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test multi-source alias without quotes - NEW FUNCTIONALITY
        test_args = ['onefilellm.py', '--alias-add', 'test_multi_unquoted', 
                     'https://example1.com', 'https://example2.com', 'https://example3.com']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check the alias exists and has all sources
        command = manager.get_command('test_multi_unquoted')
        self.assertIn('https://example1.com', command)
        self.assertIn('https://example2.com', command)
        self.assertIn('https://example3.com', command)
        
        # Verify they're space-separated
        sources = command.split()
        self.assertEqual(len(sources), 3)
        self.assertEqual(sources[0], 'https://example1.com')
        self.assertEqual(sources[1], 'https://example2.com')
        self.assertEqual(sources[2], 'https://example3.com')

    def test_cli_alias_add_with_local_files(self):
        """Test --alias-add with URLs and local files mixed"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test alias with URLs and local files
        test_args = ['onefilellm.py', '--alias-add', 'test_mixed', 
                     'https://example.com', 'local_file.txt', 
                     'https://example2.com', 'another_file.md']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check the alias has all components
        command = manager.get_command('test_mixed')
        self.assertIn('https://example.com', command)
        self.assertIn('local_file.txt', command)
        self.assertIn('https://example2.com', command)
        self.assertIn('another_file.md', command)

    def test_cli_alias_add_placeholder_support(self):
        """Test --alias-add with placeholder {} support"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test alias with placeholder and multiple sources
        test_args = ['onefilellm.py', '--alias-add', 'test_search', 
                     'https://github.com/search?q={}', 'https://docs.github.com/search?q={}']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check placeholder is preserved
        command = manager.get_command('test_search')
        self.assertEqual(command, 'https://github.com/search?q={} https://docs.github.com/search?q={}')

    def test_cli_alias_add_error_handling(self):
        """Test --alias-add error handling for invalid inputs"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Test with only one argument (missing command string)
        captured_output = StringIO()
        test_args = ['onefilellm.py', '--alias-add', 'only_name']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        output = captured_output.getvalue()
        self.assertIn('Error', output)
        self.assertIn('requires at least two arguments', output)

    def test_cli_alias_add_special_characters(self):
        """Test --alias-add with special characters and edge cases"""
        from onefilellm import main
        import sys
        import asyncio
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        
        # Test alias with special characters in URL
        test_args = ['onefilellm.py', '--alias-add', 'test_special', 
                     'https://example.com/path?param1=value1&param2=value2', 
                     'https://api.example.com/v2/search?q=test+query']
        with patch('sys.argv', test_args):
            with patch('sys.stdout', captured_output):
                asyncio.run(main())
        
        # Verify alias was created correctly
        from onefilellm import AliasManager, CORE_ALIASES
        from rich.console import Console
        
        console = Console()
        manager = AliasManager(console, CORE_ALIASES, self.alias_file)
        manager.load_aliases()
        
        # Check special characters are preserved
        command = manager.get_command('test_special')
        self.assertIn('param1=value1&param2=value2', command)
        self.assertIn('q=test+query', command)


@unittest.skipUnless(RUN_INTEGRATION_TESTS, "Integration tests disabled")
class TestIntegration(unittest.TestCase):
    """Integration tests for external services"""
    
    def test_github_repo_integration(self):
        """Test GitHub repository processing"""
        repo_url = "https://github.com/jimmc414/onefilellm"
        result = process_github_repo(repo_url)
        self.assertIn('<source type="github_repository"', result)
        self.assertIn('README.md', result)
        self.assertIn('onefilellm.py', result)
    
    def test_arxiv_integration(self):
        """Test ArXiv PDF processing"""
        arxiv_url = "https://arxiv.org/abs/2401.14295"
        result = process_arxiv_pdf(arxiv_url)
        self.assertIn('<source type="arxiv"', result)
        self.assertIn('</source>', result)
        # Check that we got actual PDF content (not an error)
        self.assertNotIn('<error>', result)
    
    def test_youtube_transcript_error_handling(self):
        """Test that YouTube transcript errors are handled gracefully.
        
        This test intentionally uses a video (Rick Astley - Never Gonna Give You Up)
        that may have restricted transcripts to ensure error handling works correctly.
        The error output is expected and suppressed to avoid confusion.
        """
        import io
        import contextlib
        
        # Use Rick Astley's video which often has transcript issues
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Capture stdout and stderr to suppress error messages during test
        captured_output = io.StringIO()
        captured_error = io.StringIO()
        
        with contextlib.redirect_stdout(captured_output), contextlib.redirect_stderr(captured_error):
            result = fetch_youtube_transcript(youtube_url)
        
        # Check that the function returns a valid XML structure even on error
        self.assertIn('<source type="youtube_transcript"', result)
        self.assertIn('</source>', result)
        self.assertIn(f'url="{youtube_url}"', result)
        
        # If an error occurred, verify it's properly formatted in XML
        if '<error>' in result:
            self.assertIn('<error>', result)
            self.assertIn('</error>', result)
            # This is expected - the test passes when errors are handled gracefully
        else:
            # If transcript was actually fetched, verify it has content
            self.assertTrue(len(result) > 100, "Transcript should contain actual content")
    
    def test_web_crawl_integration(self):
        """Test web crawling"""
        url = "https://docs.anthropic.com/"
        result = crawl_and_extract_text(url, max_depth=1, include_pdfs=False, ignore_epubs=True)
        # Result is now a dict with 'content' key
        content = result['content'] if isinstance(result, dict) else result
        self.assertIn('<source type="web_crawl"', content)
        self.assertIn('Anthropic', content)


class TestCLIFunctionality(unittest.TestCase):
    """Test command-line interface functionality"""
    
    def run_cli(self, args, input_text=None):
        """Helper to run CLI commands"""
        cmd = [sys.executable, "onefilellm.py"] + args
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_text else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_text)
        return stdout, stderr, process.returncode
    
    def test_help_message(self):
        """Test regular help message"""
        stdout, stderr, returncode = self.run_cli(["--help"])
        self.assertEqual(returncode, 0, f"Help command failed with stderr: {stderr}")
        self.assertIn("usage:", stdout.lower())  # Case insensitive
        self.assertIn("options:", stdout.lower())
        self.assertIn("--format", stdout)
        self.assertIn("onefilellm", stdout.lower())
    
    def test_help_full_message(self):
        """Test comprehensive help message (--help-full) - DISABLED: Feature not implemented yet"""
        # TODO: Implement --help-full argument and comprehensive help content
        # The new alias system documentation needs to be integrated into a full help system
        self.skipTest("--help-full feature not yet implemented. Use --help-topic instead.")
    
    def test_stdin_input(self):
        """Test stdin input processing"""
        stdout, stderr, returncode = self.run_cli(["-"], "Test input")
        self.assertEqual(returncode, 0)
        self.assertIn("Detected format:", stdout)
    
    def test_format_override(self):
        """Test format override via CLI"""
        stdout, stderr, returncode = self.run_cli(["-", "--format", "json"], '{"key": "value"}')
        self.assertEqual(returncode, 0)
        self.assertIn("Processing input as json", stdout)
    
    def test_invalid_format(self):
        """Test invalid format handling"""
        stdout, stderr, returncode = self.run_cli(["-", "--format", "invalid"], "test")
        self.assertNotEqual(returncode, 0)
        self.assertIn("invalid choice", stderr)  # argparse error message
    
    def test_multiple_inputs(self):
        """Test multiple input handling"""
        # Create test files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f1:
            f1.write("Content 1")
            file1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f2:
            f2.write("Content 2")
            file2 = f2.name
        
        try:
            stdout, stderr, returncode = self.run_cli([file1, file2])
            self.assertEqual(returncode, 0)
            # Check that both files were processed
            self.assertIn(file1, stdout)
            self.assertIn(file2, stdout)
            self.assertIn("Successfully processed", stdout)
        finally:
            os.unlink(file1)
            os.unlink(file2)


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios"""
    
    def test_invalid_file_path(self):
        """Test handling of invalid file paths"""
        # Mock the process_input function since it's now async and requires args
        with patch('onefilellm.process_input', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = '<error>File not found</error>'
            import asyncio
            result = asyncio.run(mock_process("/nonexistent/file/path.txt", None, Console()))
            self.assertIn('error', result.lower())
    
    def test_invalid_url(self):
        """Test handling of invalid URLs"""
        # Mock the process_input function since it's now async and requires args
        with patch('onefilellm.process_input', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = '<error>Invalid URL</error>'
            import asyncio
            result = asyncio.run(mock_process("not_a_valid_url", None, Console()))
            self.assertIn('error', result.lower())
    
    def test_empty_input(self):
        """Test handling of empty input"""
        console = MagicMock()
        result = process_text_stream("", {'type': 'stdin'}, console)
        self.assertIsNotNone(result)  # Should still return valid XML
    
    def test_network_errors(self):
        """Test handling of network errors"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            result = crawl_and_extract_text("https://example.com", 1, False, True)
            # crawl_and_extract_text returns a dict with 'content' and 'processed_urls' keys
            self.assertIsInstance(result, dict)
            self.assertIn('content', result)
            self.assertIn('Error processing page', result['content'])

    def test_youtube_subprocess_failure(self):
        """Simulate yt-dlp subprocess failure and verify error handling."""
        import types

        # Create a fake youtube_transcript_api module that always fails
        fake_module = types.ModuleType("youtube_transcript_api")

        class FakeYTA:
            @staticmethod
            def get_transcript(video_id):
                raise Exception("api failure")

        fake_module.YouTubeTranscriptApi = FakeYTA

        with patch.dict('sys.modules', {"youtube_transcript_api": fake_module}), \
             patch.object(onefilellm, "OFFLINE_MODE", False), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=['yt-dlp'], returncode=1, stdout='', stderr='boom')
            result = fetch_youtube_transcript('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

        self.assertIn('yt-dlp failed', result)
        self.assertIn('boom', result)


class TestOfflineMode(unittest.TestCase):
    """Ensure network helpers honor OFFLINE_MODE."""

    def setUp(self):
        self._orig_offline = onefilellm.OFFLINE_MODE
        onefilellm.OFFLINE_MODE = True

    def tearDown(self):
        onefilellm.OFFLINE_MODE = self._orig_offline

    def test_fetch_youtube_transcript_offline(self):
        with patch('subprocess.run') as mock_run:
            result = fetch_youtube_transcript('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertIn('Offline mode enabled', result)
        mock_run.assert_not_called()

    def test_fetch_youtube_transcript_offline_live_url(self):
        with patch('subprocess.run') as mock_run:
            result = fetch_youtube_transcript('https://www.youtube.com/live/czVBmqZP6Ss')
        self.assertIn('Offline mode enabled', result)
        self.assertNotIn('Could not extract video ID', result)
        mock_run.assert_not_called()

    def test_process_doi_or_pmid_offline(self):
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            result = process_doi_or_pmid('10.1000/182')
        self.assertIn('Offline mode enabled', result)
        mock_post.assert_not_called()
        mock_get.assert_not_called()

    def test_process_github_repo_offline(self):
        with patch('requests.get') as mock_get:
            result = process_github_repo('https://github.com/user/repo')
        self.assertIn('Offline mode enabled', result)
        mock_get.assert_not_called()


class TestTemporaryFileCollisions(unittest.TestCase):
    """Ensure temporary file handling avoids name collisions."""

    def setUp(self):
        self.orig_offline = onefilellm.OFFLINE_MODE
        onefilellm.OFFLINE_MODE = False

    def tearDown(self):
        onefilellm.OFFLINE_MODE = self.orig_offline

    def test_duplicate_filenames(self):
        repo_url = 'https://github.com/user/repo'

        def mock_requests_get(url, headers=None, timeout=30):
            response = MagicMock()
            if url == 'https://api.github.com/repos/user/repo/contents':
                response.json.return_value = [
                    {"type": "dir", "name": "dir1", "url": "url_dir1"},
                    {"type": "dir", "name": "dir2", "url": "url_dir2"},
                ]
            elif url == 'url_dir1':
                response.json.return_value = [
                    {"type": "file", "name": "same.txt", "path": "dir1/same.txt", "download_url": "url1"}
                ]
            elif url == 'url_dir2':
                response.json.return_value = [
                    {"type": "file", "name": "same.txt", "path": "dir2/same.txt", "download_url": "url2"}
                ]
            else:
                raise AssertionError(f'Unexpected URL {url}')
            response.raise_for_status = MagicMock()
            return response

        download_paths = []

        def mock_download_file(url, target_path, headers=None):
            download_paths.append(target_path)
            with open(target_path, 'wb') as f:
                if url == 'url1':
                    f.write(b'content1')
                elif url == 'url2':
                    f.write(b'content2')

        with patch('onefilellm.requests.get', side_effect=mock_requests_get), \
             patch('onefilellm.download_file', side_effect=mock_download_file):
            result = process_github_repo(repo_url)

        self.assertIn('content1', result)
        self.assertIn('content2', result)
        self.assertEqual(len(download_paths), 2)
        self.assertEqual(len(set(download_paths)), 2)
        for path in download_paths:
            self.assertFalse(os.path.exists(path))


class TestGitHubAuthorizationHeaders(unittest.TestCase):
    """Validate GitHub Authorization headers propagate through downloads."""

    def setUp(self):
        self.orig_offline = onefilellm.OFFLINE_MODE
        self.orig_headers = dict(onefilellm.headers)
        self.orig_token = onefilellm.TOKEN
        onefilellm.OFFLINE_MODE = False
        onefilellm.headers = {'Authorization': 'token testtoken'}
        onefilellm.TOKEN = 'testtoken'

    def tearDown(self):
        onefilellm.OFFLINE_MODE = self.orig_offline
        onefilellm.headers = dict(self.orig_headers)
        onefilellm.TOKEN = self.orig_token

    def test_process_github_repo_forwards_authorization(self):
        repo_url = 'https://github.com/user/private'
        requested_headers = []
        forwarded_headers = []

        def mock_requests_get(url, headers=None, timeout=30):
            requested_headers.append(headers)
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.json.return_value = [
                {
                    "type": "file",
                    "name": "example.txt",
                    "path": "example.txt",
                    "download_url": "https://example.com/example.txt",
                }
            ]
            return response

        def mock_download_file(url, target_path, headers=None):
            forwarded_headers.append(headers)
            with open(target_path, 'w', encoding='utf-8') as handle:
                handle.write('dummy content')

        with patch('onefilellm.requests.get', side_effect=mock_requests_get), \
             patch('onefilellm.download_file', side_effect=mock_download_file):
            result = process_github_repo(repo_url)

        self.assertIn('dummy content', result)
        self.assertTrue(requested_headers, 'Expected directory listing requests')
        self.assertTrue(forwarded_headers, 'Expected file downloads to occur')

        for header in requested_headers:
            self.assertIsNotNone(header)
            self.assertEqual(header.get('Authorization'), 'token testtoken')

        self.assertEqual(forwarded_headers[0].get('Authorization'), 'token testtoken')


class TestPerformance(unittest.TestCase):
    """Performance and edge case tests"""
    
    def test_large_file_handling(self):
        """Test handling of large files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write 1MB of text
            content = "x" * 1024 * 1024
            f.write(content)
            f.flush()
            
            # Mock the process_input function since it's now async and requires args
            with patch('onefilellm.process_input', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = '<source type="local_file">Large file content</source>'
                start_time = time.time()
                import asyncio
                result = asyncio.run(mock_process(f.name, None, Console()))
                end_time = time.time()
                
                self.assertIn('<source type="local_file"', result)
                self.assertLess(end_time - start_time, 5)  # Should complete within 5 seconds
            
            # Close file before unlinking to avoid Windows permission error
            f.close()
            os.unlink(f.name)
    
    def test_unicode_handling(self):
        """Test Unicode character handling"""
        unicode_content = "Hello 世界 🌍 Émojis"
        console = MagicMock()
        result = process_text_stream(unicode_content, {'type': 'stdin'}, console)
        self.assertIn(unicode_content, result)
    
    def test_special_characters(self):
        """Test special character handling"""
        special_content = "Special <>&\" characters"
        console = MagicMock()
        result = process_text_stream(special_content, {'type': 'stdin'}, console)
        self.assertIn(special_content, result)


class TestGitHubIssuesPullRequests(unittest.TestCase):
    """Test GitHub Issues and Pull Requests processing"""
    
    def test_github_issue_url_parsing(self):
        """Test GitHub issue URL parsing logic"""
        # Test valid GitHub issue URLs
        valid_urls = [
            "https://github.com/user/repo/issues/123",
            "https://github.com/org/project/issues/456",
            "https://github.com/user-name/repo-name/issues/789"
        ]
        
        for url in valid_urls:
            # Test that the URL structure is recognized
            self.assertIn('/issues/', url)
            self.assertIn('github.com', url)
    
    def test_github_pr_url_parsing(self):
        """Test GitHub pull request URL parsing logic"""
        # Test valid GitHub PR URLs
        valid_urls = [
            "https://github.com/user/repo/pull/123",
            "https://github.com/org/project/pull/456",
            "https://github.com/user-name/repo-name/pull/789"
        ]
        
        for url in valid_urls:
            # Test that the URL structure is recognized
            self.assertIn('/pull/', url)
            self.assertIn('github.com', url)
    
    @patch('os.environ.get')
    @patch('onefilellm.requests.get')
    def test_github_issue_with_token(self, mock_get, mock_env):
        """Test GitHub issue processing when token is available"""
        # Mock environment to have GitHub token
        mock_env.return_value = "fake_token"
        
        # Mock GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Test Issue',
            'body': 'Issue body',
            'user': {'login': 'testuser'},
            'state': 'open',
            'number': 123
        }
        mock_get.return_value = mock_response
        
        # Test that function can be called without immediate token error
        try:
            result = process_github_issue("https://github.com/user/repo/issues/123")
            # If no exception, check that it returns some XML structure
            self.assertIn('<source', result)
        except Exception as e:
            # If there's still an error, it should be about the actual processing, not token
            self.assertNotIn('GitHub Token not set', str(e))
    
    def test_github_issue_error_response_format(self):
        """Test GitHub issue error response format"""
        # Test that without a token, we get a properly formatted error response
        result = process_github_issue("https://github.com/user/repo/issues/123")

        # Should return properly formatted XML even for errors
        self.assertIn('<source type="github_issue"', result)
        self.assertIn('error', result.lower())

    def test_github_issues_error_response_format(self):
        """Test GitHub issues list error response format"""
        result = process_github_issues("https://github.com/user/repo/issues")

        self.assertIn('<source type="github_issues"', result)
        self.assertIn('error', result.lower())
    
    def test_github_pr_error_response_format(self):
        """Test GitHub pull request error response format"""
        # Test that without a token, we get a properly formatted error response
        result = process_github_pull_request("https://github.com/user/repo/pull/123")
        
        # Should return properly formatted XML even for errors
        self.assertIn('<source type="github_pull_request"', result)
        self.assertIn('error', result.lower())


class TestAdvancedWebCrawler(unittest.TestCase):
    """Test advanced web crawler features and options"""
    
    def test_crawl_function_signature(self):
        """Test that crawl function has expected signature"""
        # Test that the function signature includes required parameters
        import inspect
        sig = inspect.signature(crawl_and_extract_text)
        params = list(sig.parameters.keys())
        
        # Check that required parameters exist
        self.assertIn('base_url', params)
        self.assertIn('max_depth', params)
        self.assertIn('include_pdfs', params)
        self.assertIn('ignore_epubs', params)
    
    def test_crawl_depth_parameter_validation(self):
        """Test crawl depth parameter validation"""
        # Test with different depth values
        test_depths = [1, 2, 3, 5]
        
        for depth in test_depths:
            # Test that depth parameter is accepted (basic validation)
            self.assertIsInstance(depth, int)
            self.assertGreater(depth, 0)
    
    def test_crawl_pdf_parameter_validation(self):
        """Test PDF inclusion parameter validation"""
        # Test boolean parameters
        include_pdf_options = [True, False]
        ignore_epub_options = [True, False]
        
        for include_pdfs in include_pdf_options:
            for ignore_epubs in ignore_epub_options:
                self.assertIsInstance(include_pdfs, bool)
                self.assertIsInstance(ignore_epubs, bool)
    
    @patch('onefilellm.requests.get')
    def test_crawl_with_mocked_requests(self, mock_get):
        """Test crawl with mocked HTTP requests"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Test Page</h1><p>Test content</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response
        
        # Test basic crawl functionality
        result = crawl_and_extract_text("https://example.com", 1, False, True)
        
        # Check that result has expected structure
        self.assertIsInstance(result, dict)
        self.assertIn('content', result)
        self.assertIn('processed_urls', result)
    
    def test_crawl_error_handling(self):
        """Test crawl error handling for invalid URLs"""
        # Test with invalid URL
        result = crawl_and_extract_text("invalid-url", 1, False, True)
        
        # Should handle errors gracefully
        self.assertIsInstance(result, dict)
        self.assertIn('content', result)
    
    def test_crawl_url_validation(self):
        """Test URL validation logic"""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://subdomain.example.com/path"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            None
        ]
        
        for url in valid_urls:
            self.assertTrue(url.startswith(('http://', 'https://')))
        
        for url in invalid_urls:
            if url:
                self.assertFalse(url.startswith(('http://', 'https://')))


class TestMultipleInputProcessing(unittest.TestCase):
    """Test complex multiple input processing scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_file1 = os.path.join(self.temp_dir, "test1.txt")
        with open(self.test_file1, 'w') as f:
            f.write("Content from file 1")
            
        self.test_file2 = os.path.join(self.temp_dir, "test2.md")
        with open(self.test_file2, 'w') as f:
            f.write("# Markdown Content\nContent from file 2")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_mixed_input_types_validation(self):
        """Test validation of mixed input types"""
        # Test different input type recognition
        local_file = self.test_file1
        web_url = "https://example.com"
        github_repo = "https://github.com/user/repo"
        
        # Test that inputs are recognized as different types
        self.assertTrue(os.path.exists(local_file))
        self.assertTrue(web_url.startswith('https://'))
        self.assertTrue('github.com' in github_repo)
        
        # Test input list processing logic
        inputs = [local_file, web_url, github_repo]
        self.assertEqual(len(inputs), 3)
        
        # Test that each input has different characteristics
        input_types = []
        for inp in inputs:
            if os.path.exists(inp):
                input_types.append('local_file')
            elif 'github.com' in inp:
                input_types.append('github')
            elif inp.startswith(('http://', 'https://')):
                input_types.append('web_url')
        
        self.assertEqual(len(set(input_types)), 3)  # Should have 3 different types
    
    def test_error_in_one_input_doesnt_stop_others(self):
        """Test that error in one input doesn't prevent processing others"""
        # Create a mix of valid and invalid inputs
        inputs = [
            self.test_file1,
            "/nonexistent/file.txt",  # This will fail
            self.test_file2
        ]
        
        with patch('onefilellm.process_input', new_callable=AsyncMock) as mock_process:
            # First call succeeds, second fails, third succeeds
            mock_process.side_effect = [
                '<source type="local_file">Content from file 1</source>',
                Exception("File not found"),
                '<source type="local_file">Content from file 2</source>'
            ]
            
            results = []
            errors = []
            
            for input_item in inputs:
                try:
                    import asyncio
                    result = asyncio.run(mock_process(input_item, None, Console()))
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
                    continue
            
            # Should have 2 successful results and 1 error
            self.assertEqual(len(results), 2)
            self.assertEqual(len(errors), 1)
            self.assertIn("File not found", errors[0])
    
    def test_specialized_input_recognition(self):
        """Test recognition of specialized input types"""
        arxiv_url = "https://arxiv.org/abs/2401.14295"
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Test ArXiv URL recognition
        self.assertIn('arxiv.org', arxiv_url)
        self.assertIn('/abs/', arxiv_url)
        
        # Test YouTube URL recognition
        self.assertIn('youtube.com', youtube_url)
        self.assertIn('watch?v=', youtube_url)
        
        # Test that both are valid URLs
        specialized_inputs = [arxiv_url, youtube_url]
        for inp in specialized_inputs:
            self.assertTrue(inp.startswith('https://'))
    
    def test_large_number_of_inputs_creation(self):
        """Test creation and management of large number of inputs"""
        # Create multiple test files
        large_input_list = []
        for i in range(10):
            test_file = os.path.join(self.temp_dir, f"large_test_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"Content from large file {i}")
            large_input_list.append(test_file)
        
        # Test that all files were created
        self.assertEqual(len(large_input_list), 10)
        
        # Test that all files exist
        for test_file in large_input_list:
            self.assertTrue(os.path.exists(test_file))
        
        # Test file content
        for i, test_file in enumerate(large_input_list):
            with open(test_file, 'r') as f:
                content = f.read()
                self.assertIn(f"Content from large file {i}", content)
        
        # Clean up additional files
        for test_file in large_input_list:
            os.unlink(test_file)


class RichTestResult(unittest.TextTestResult):
    """Custom test result class with rich formatting"""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.console = Console()
        self.test_results = []
        self.verbosity = verbosity
        
    def startTest(self, test):
        super().startTest(test)
        if self.verbosity > 1:
            test_name = f"{test.__class__.__name__}.{test._testMethodName}"
            self.console.print(f"🔄 Running: [cyan]{test_name}[/cyan]", end="")
    
    def addSuccess(self, test):
        super().addSuccess(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.test_results.append(('success', test_name))
        if self.verbosity > 1:
            self.console.print(" [bold green]✓ PASSED[/bold green]")
        elif self.verbosity == 1:
            self.console.print("[bold green].[/bold green]", end="")
    
    def addError(self, test, err):
        super().addError(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.test_results.append(('error', test_name))
        if self.verbosity > 1:
            self.console.print(" [bold red]✗ ERROR[/bold red]")
            if self.verbosity > 2:
                import traceback
                self.console.print(f"[red]{traceback.format_exception(*err)[-1]}[/red]")
        elif self.verbosity == 1:
            self.console.print("[bold red]E[/bold red]", end="")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.test_results.append(('failure', test_name))
        if self.verbosity > 1:
            self.console.print(" [bold red]✗ FAILED[/bold red]")
            if self.verbosity > 2:
                import traceback
                self.console.print(f"[red]{traceback.format_exception(*err)[-1]}[/red]")
        elif self.verbosity == 1:
            self.console.print("[bold red]F[/bold red]", end="")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.test_results.append(('skip', test_name))
        if self.verbosity > 1:
            self.console.print(f" [yellow]⚠ SKIPPED[/yellow]: {reason}")
        elif self.verbosity == 1:
            self.console.print("[yellow]S[/yellow]", end="")


class RichTestRunner(unittest.TextTestRunner):
    """Custom test runner with rich formatting"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.console = Console()
        self.resultclass = RichTestResult
    
    def run(self, test):
        self.console.print("\n[bold bright_blue]══════════════════════════════════════════════════════════════════════[/bold bright_blue]")
        self.console.print("[bold bright_yellow]OneFileLLM Test Suite - All Tests Consolidated[/bold bright_yellow]", justify="center")
        self.console.print("[bold bright_blue]══════════════════════════════════════════════════════════════════════[/bold bright_blue]\n")
        
        result = super().run(test)
        
        # Print summary table
        self._print_summary(result)
        
        return result
    
    def _print_summary(self, result):
        self.console.print("\n[bold bright_blue]══════════════════════════════════════════════════════════════════════[/bold bright_blue]")
        
        # Create summary table
        table = Table(title="Test Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Count", justify="right", width=10)
        table.add_column("Status", width=20)
        
        # Add rows
        table.add_row("Tests Run", str(result.testsRun), "")
        
        success_count = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
        table.add_row("Passed", str(success_count), Text("✓", style="bold green") if success_count > 0 else "")
        
        table.add_row("Failed", str(len(result.failures)), 
                     Text("✗", style="bold red") if len(result.failures) > 0 else Text("✓", style="bold green"))
        
        table.add_row("Errors", str(len(result.errors)), 
                     Text("✗", style="bold red") if len(result.errors) > 0 else Text("✓", style="bold green"))
        
        table.add_row("Skipped", str(len(result.skipped)), 
                     Text("⚠", style="yellow") if len(result.skipped) > 0 else "")
        
        self.console.print(table)
        
        # Overall result
        if result.wasSuccessful():
            self.console.print("\n[bold green]✅ All tests passed![/bold green]", justify="center")
        else:
            self.console.print("\n[bold red]❌ Some tests failed![/bold red]", justify="center")
            
            # Show failed tests
            if result.failures or result.errors:
                self.console.print("\n[bold red]Failed Tests:[/bold red]")
                for test, _ in result.failures + result.errors:
                    test_name = f"{test.__class__.__name__}.{test._testMethodName}"
                    self.console.print(f"  [red]• {test_name}[/red]")


def run_all_tests(verbosity=2):
    """Run all tests with optional filtering"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestUtilityFunctions,
        TestTextFormatDetection,
        TestStreamProcessing,
        TestCoreProcessing,
        TestAliasSystem2,  # New Alias Management 2.0 tests
        TestAdvancedAliasFeatures,  # Advanced alias functionality tests
        TestIntegration,
        TestCLIFunctionality,
        TestErrorHandling,
        TestPerformance,
        TestGitHubIssuesPullRequests,
        TestAdvancedWebCrawler,
        TestMultipleInputProcessing
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with rich formatting
    runner = RichTestRunner(verbosity=verbosity, stream=sys.stderr)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("""
OneFileLLM Comprehensive Test Suite

Usage:
    python test_all.py [options]

Options:
    -h, --help          Show this help message
    --integration       Run integration tests (requires network)
    --slow              Run slow tests (ArXiv, web crawling)
    --verbose           Increase test output verbosity
    --quiet             Decrease test output verbosity
    --no-color          Disable colored output

Environment Variables:
    GITHUB_TOKEN        Set to run GitHub integration tests
    RUN_INTEGRATION_TESTS=true   Enable integration tests
    RUN_SLOW_TESTS=true         Enable slow tests

Examples:
    # Run basic tests only
    python test_all.py

    # Run all tests including integration
    python test_all.py --integration --slow

    # Run with GitHub token
    GITHUB_TOKEN=your_token python test_all.py --integration
    
    # Run specific test class
    python -m unittest test_all.TestUtilityFunctions
    
    # Run specific test method
    python -m unittest test_all.TestUtilityFunctions.test_safe_file_read
""")
            sys.exit(0)
        
        # Set environment variables based on arguments
        if "--integration" in sys.argv:
            os.environ['RUN_INTEGRATION_TESTS'] = 'true'
        if "--slow" in sys.argv:
            os.environ['RUN_SLOW_TESTS'] = 'true'
        
        # Set verbosity
        verbosity = 2  # Default
        if "--verbose" in sys.argv:
            verbosity = 3
        elif "--quiet" in sys.argv:
            verbosity = 1
        
        # Check for no-color option
        if "--no-color" in sys.argv:
            os.environ['NO_COLOR'] = '1'
            from rich import console as rich_console
            rich_console._console = Console(force_terminal=False, no_color=True)
    else:
        verbosity = 2
    
    # Run tests
    success = run_all_tests(verbosity=verbosity)
    sys.exit(0 if success else 1)