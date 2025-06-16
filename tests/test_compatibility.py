"""
Compatibility layer for test suite to work with monolithic onefilellm.py structure.
This module provides the expected modular interface while mapping to the actual implementation.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the actual monolithic onefilellm module
import onefilellm
from onefilellm import (
    AliasManager, CORE_ALIASES, ALIAS_CONFIG_DIR, USER_ALIASES_PATH,
    ensure_alias_dir_exists, process_github_repo, process_local_folder,
    process_ipynb_file, excel_to_markdown,
    escape_xml, fetch_youtube_transcript, process_doi_or_pmid,
    process_github_pull_request, process_github_issue,
    crawl_and_extract_text, process_web_crawl,
    ENABLE_COMPRESSION_AND_NLTK, TOKEN_ESTIMATE_MULTIPLIER
)

from utils import (
    detect_text_format, parse_as_plaintext, parse_as_markdown,
    parse_as_json, parse_as_html, parse_as_yaml,
    download_file, is_same_domain, is_within_depth,
    read_from_clipboard, read_from_stdin,
    get_file_extension, is_binary_file,
    safe_file_read, is_allowed_filetype, is_excluded_file
)

# Create mock processor classes that wrap the existing functions
class CoreProcessor:
    """Mock processor for core functionality"""
    def process(self, input_data, context=None):
        # Implement core processing logic
        return input_data

class GitHubRepoProcessor:
    """Processor for GitHub repositories"""
    def process(self, repo_url, context=None):
        github_token = context.get('github_token') if context else None
        # The original function uses the global TOKEN, so we need to temporarily set it
        import os
        old_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            os.environ['GITHUB_TOKEN'] = github_token
        try:
            result = process_github_repo(repo_url)
            return result
        finally:
            if old_token:
                os.environ['GITHUB_TOKEN'] = old_token
            elif github_token:
                del os.environ['GITHUB_TOKEN']

class GitHubPRProcessor:
    """Processor for GitHub pull requests"""
    def process(self, pr_url, context=None):
        github_token = context.get('github_token') if context else None
        return process_github_pull_request(pr_url, github_token)

class GitHubIssueProcessor:
    """Processor for GitHub issues"""
    def process(self, issue_url, context=None):
        github_token = context.get('github_token') if context else None
        return process_github_issue(issue_url, github_token)

class LocalFileProcessor:
    """Processor for local files"""
    def process(self, file_path, context=None):
        return safe_file_read(file_path)

class LocalFolderProcessor:
    """Processor for local folders"""
    def process(self, folder_path, context=None):
        return process_local_folder(folder_path)

class ArXivProcessor:
    """Processor for ArXiv papers"""
    def process(self, arxiv_id, context=None):
        # ArXiv processing through DOI
        return process_doi_or_pmid(arxiv_id)

class DOIProcessor:
    """Processor for DOI papers"""
    def process(self, doi, context=None):
        return process_doi_or_pmid(doi)

class PMIDProcessor:
    """Processor for PubMed papers"""
    def process(self, pmid, context=None):
        return process_doi_or_pmid(pmid)

class YouTubeProcessor:
    """Processor for YouTube videos"""
    def process(self, video_url, context=None):
        return fetch_youtube_transcript(video_url)

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

class WebContentProcessor:
    """Processor for web content"""
    async def process_async(self, url, context=None):
        # Extract crawler arguments from context
        cli_args = type('obj', (object,), context or {})()
        console = context.get('console') if context else None
        progress_bar = context.get('progress_bar') if context else None
        
        return await crawl_and_extract_text(url, **context) if context else await crawl_and_extract_text(url)

class AsyncWebCrawler:
    """Async web crawler"""
    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs
    
    async def crawl(self, progress_bar=None):
        return await crawl_and_extract_text(self.base_url, **self.kwargs)

# XML builder functions
def combine_xml_outputs(outputs):
    """Combine multiple XML outputs into one"""
    if not outputs:
        return "<onefilellm_output></onefilellm_output>"
    
    combined = ["<onefilellm_output>"]
    for output in outputs:
        # Strip the outer onefilellm_output tags if present
        content = output
        if content.startswith("<onefilellm_output>"):
            content = content.replace("<onefilellm_output>", "").replace("</onefilellm_output>", "")
        combined.append(content)
    combined.append("</onefilellm_output>")
    return "\n".join(combined)

def create_source_element(source_type, **attributes):
    """Create a source XML element"""
    attrs = " ".join([f'{k}="{escape_xml(v)}"' for k, v in attributes.items()])
    return f'<source type="{escape_xml(source_type)}" {attrs}>'

def create_file_element(path, content):
    """Create a file XML element"""
    return f'<file path="{escape_xml(path)}">\n{content}\n</file>'

def create_error_element(error_msg):
    """Create an error XML element"""
    return f'<error>{escape_xml(error_msg)}</error>'

# Configuration class
class Configuration:
    """Configuration management for onefilellm"""
    def __init__(self):
        self.enable_compression = ENABLE_COMPRESSION_AND_NLTK
        self.token_multiplier = TOKEN_ESTIMATE_MULTIPLIER
        self.excluded_dirs = onefilellm.EXCLUDED_DIRS
        self.allowed_extensions = getattr(onefilellm, 'allowed_extensions', [])

# Additional function mappings needed for tests
def process_arxiv_pdf(pdf_path):
    """Process ArXiv PDF from local path"""
    return onefilellm._process_pdf_content_from_path(pdf_path)

# Import process_text_stream from onefilellm
from onefilellm import process_text_stream as _original_process_text_stream

def process_text_stream(raw_text_content, source_info, console, format_override=None):
    """Wrapper for process_text_stream to handle parameter compatibility"""
    return _original_process_text_stream(raw_text_content, source_info, console, format_override)

# Create namespace modules for imports
class CoreModule:
    processor_claude2 = type('module', (), {
        'CoreProcessor': CoreProcessor
    })
    xml_builder_claude2 = type('module', (), {
        'combine_xml_outputs': combine_xml_outputs,
        'create_source_element': create_source_element,
        'create_file_element': create_file_element,
        'create_error_element': create_error_element
    })
    config = type('module', (), {
        'Configuration': Configuration,
        'CORE_ALIASES': CORE_ALIASES
    })

class AliasesModule:
    manager = type('module', (), {
        'AliasManager': AliasManager
    })
    storage = type('module', (), {
        'ensure_alias_dir_exists': ensure_alias_dir_exists,
        'ALIAS_CONFIG_DIR': ALIAS_CONFIG_DIR,
        'USER_ALIASES_PATH': USER_ALIASES_PATH
    })

class SourcesModule:
    github_claude2 = type('module', (), {
        'GitHubRepoProcessor': GitHubRepoProcessor,
        'GitHubPRProcessor': GitHubPRProcessor,
        'GitHubIssueProcessor': GitHubIssueProcessor
    })
    academic_claude1 = type('module', (), {
        'ArXivProcessor': ArXivProcessor,
        'DOIProcessor': DOIProcessor,
        'PMIDProcessor': PMIDProcessor,
        'process_pdf_content_from_path': process_arxiv_pdf
    })
    local_claude2 = type('module', (), {
        'LocalFileProcessor': LocalFileProcessor,
        'LocalFolderProcessor': LocalFolderProcessor,
        'safe_file_read': safe_file_read,
        'is_allowed_filetype': is_allowed_filetype,
        'is_excluded_file': is_excluded_file,
        'excel_to_markdown': excel_to_markdown,
        'process_ipynb_file': process_ipynb_file,
        'get_file_extension': get_file_extension,
        'is_binary_file': is_binary_file
    })
    youtube_claude1 = type('module', (), {
        'YouTubeProcessor': YouTubeProcessor
    })
    stream_claude1 = type('module', (), {
        'StdinProcessor': StdinProcessor,
        'ClipboardProcessor': ClipboardProcessor,
        'StringProcessor': StringProcessor
    })

class CrawlersModule:
    web_processor_claude3 = type('module', (), {
        'WebContentProcessor': WebContentProcessor
    })
    async_crawler_claude3 = type('module', (), {
        'AsyncWebCrawler': AsyncWebCrawler
    })

# Create the module structure
onefilellm.core = CoreModule()
onefilellm.aliases = AliasesModule()
onefilellm.sources = SourcesModule()
onefilellm.crawlers = CrawlersModule()