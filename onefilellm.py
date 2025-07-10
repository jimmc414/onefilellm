import asyncio
import time
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
import os
import sys
import json
import tiktoken
import re
import shlex
import pyperclip
from pathlib import Path
import wget
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
import xml.etree.ElementTree as ET # Keep for preprocess_text if needed
from typing import Union, List, Dict, Optional, Set, Tuple
from dotenv import load_dotenv
from urllib.robotparser import RobotFileParser
from readability import Document
import io
import argparse

# Import utility functions
from utils import (
    safe_file_read, read_from_clipboard, read_from_stdin,
    detect_text_format, parse_as_plaintext, parse_as_markdown,
    parse_as_json, parse_as_html, parse_as_yaml,
    download_file, is_same_domain, is_within_depth,
    is_excluded_file, is_allowed_filetype, escape_xml
)

# Try to import yaml, but don't fail if not available
try:
    import yaml
except ImportError:
    yaml = None
    print("[Warning] PyYAML module not found. YAML format detection/parsing will be limited.", file=sys.stderr)

# --- Configuration Flags ---
ENABLE_COMPRESSION_AND_NLTK = False # Set to True to enable NLTK download, stopword removal, and compressed output
TOKEN_ESTIMATE_MULTIPLIER = 1.37 # Multiplier to estimate model token usage from tiktoken count
# --- End Configuration Flags ---

# --- Output Format Notes ---
# This script produces output wrapped in XML-like tags for structure (e.g., <source>, <file>).
# However, the *content* within these tags (especially code) is NOT XML-escaped.
# This means characters like < > & within code blocks are preserved as-is for readability
# and correct interpretation by LLMs. The escape_xml function currently returns text unchanged.
# --- End Output Format Notes ---

# --- Configuration Directories ---
EXCLUDED_DIRS = ["dist", "node_modules", ".git", "__pycache__"]

# --- Alias Configuration ---
ALIAS_DIR_NAME = ".onefilellm_aliases"  # Re-use existing constant
ALIAS_CONFIG_DIR = Path.home() / ALIAS_DIR_NAME
USER_ALIASES_PATH = ALIAS_CONFIG_DIR / "aliases.json"

CORE_ALIASES = {
    "ofl_readme": "https://github.com/jimmc414/onefilellm/blob/main/readme.md",
    "ofl_repo": "https://github.com/jimmc414/onefilellm",
    "gh_search": "https://github.com/search?q={}", # Example alias expecting a placeholder
    "arxiv_search": "https://arxiv.org/search/?query={}&searchtype=all&source=header",
    # Consider adding more common aliases
}
# --- End Alias Configuration ---

def ensure_alias_dir_exists():
    """Ensures the alias directory exists, creating it if necessary."""
    ALIAS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class AliasManager:
    def __init__(self, console, core_aliases_dict, user_aliases_file_path):
        self.console = console
        self.core_aliases_map = core_aliases_dict.copy() # Store the original core aliases
        self.user_aliases_file_path = user_aliases_file_path
        self.user_aliases_map = {}
        self.effective_aliases_map = {} # Merged view: user takes precedence
        self._ensure_alias_dir()

    def _ensure_alias_dir(self):
        """Ensures the alias directory exists."""
        try:
            self.user_aliases_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.console.print(f"[bold red]Error:[/bold red] Could not create alias directory {self.user_aliases_file_path.parent}: {e}")


    def load_aliases(self):
        """Loads user aliases from file and merges with core aliases."""
        self._load_user_aliases()
        self.effective_aliases_map = self.core_aliases_map.copy()
        self.effective_aliases_map.update(self.user_aliases_map) # User aliases override core

    def _load_user_aliases(self):
        """Loads user aliases from the JSON file."""
        self.user_aliases_map = {}
        if self.user_aliases_file_path.exists():
            try:
                with open(self.user_aliases_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.user_aliases_map = data
                    else:
                        self.console.print(f"[bold yellow]Warning:[/bold yellow] Alias file {self.user_aliases_file_path} is not a valid JSON object. Ignoring.")
            except json.JSONDecodeError:
                self.console.print(f"[bold yellow]Warning:[/bold yellow] Could not parse alias file {self.user_aliases_file_path}. It may be corrupt. Please check or remove it.")
            except IOError as e:
                self.console.print(f"[bold red]Error:[/bold red] Could not read alias file {self.user_aliases_file_path}: {e}")
        # If file doesn't exist, user_aliases_map remains empty, which is fine.

    def _save_user_aliases(self):
        """Saves the current user aliases to the JSON file."""
        self._ensure_alias_dir() # Ensure directory exists before writing
        try:
            with open(self.user_aliases_file_path, "w", encoding="utf-8") as f:
                json.dump(self.user_aliases_map, f, indent=2)
        except IOError as e:
            self.console.print(f"[bold red]Error:[/bold red] Could not write to alias file {self.user_aliases_file_path}: {e}")
            return False
        return True

    def get_command(self, alias_name: str) -> Optional[str]:
        """Gets the command string for a given alias name from the effective list."""
        return self.effective_aliases_map.get(alias_name)

    def _is_valid_alias_name(self, name: str) -> bool:
        if not name or name.startswith("--"):
            return False
        # Basic check for path-like characters or other problematic chars.
        # Allows alphanumeric, underscore, hyphen.
        if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", name):
            return False
        return True

    def add_or_update_alias(self, name: str, command_string: str) -> bool:
        """Adds or updates a user-defined alias."""
        if not self._is_valid_alias_name(name):
            self.console.print(f"[bold red]Error:[/bold red] Invalid alias name '{name}'. Names must be alphanumeric and can include '-' or '_'. They cannot start with '--'.")
            return False
            
        self.user_aliases_map[name] = command_string
        if self._save_user_aliases():
            self.effective_aliases_map[name] = command_string # Update effective map
            self.console.print(f"Alias '{name}' set to: \"{command_string}\"")
            return True
        return False

    def remove_alias(self, name: str) -> bool:
        """Removes a user-defined alias."""
        if name in self.user_aliases_map:
            del self.user_aliases_map[name]
            if self._save_user_aliases():
                # Update effective map: if core alias was shadowed, it's now active
                if name in self.core_aliases_map:
                    self.effective_aliases_map[name] = self.core_aliases_map[name]
                else: # No core alias with this name, so it's gone from effective too
                    if name in self.effective_aliases_map:
                         del self.effective_aliases_map[name]
                self.console.print(f"User alias '{name}' removed.")
                return True
            return False # Save failed
        else:
            self.console.print(f"User alias '{name}' not found.")
            return False

    def list_aliases_formatted(self, list_user=True, list_core=True) -> str:
        """Returns a formatted string of aliases for display."""
        output_lines = []
        
        # Determine combined keys for proper ordering and precedence display
        all_names = sorted(list(set(self.core_aliases_map.keys()) | set(self.user_aliases_map.keys())))

        if not all_names and (list_user or list_core):
             return "No aliases defined."

        for name in all_names:
            command_str = ""
            source_type = ""

            is_user = name in self.user_aliases_map
            is_core = name in self.core_aliases_map

            if is_user and list_user:
                command_str = self.user_aliases_map[name]
                source_type = "(user)"
            elif is_core and list_core and not is_user : # Show core only if not overridden by user or if user listing is off
                command_str = self.core_aliases_map[name]
                source_type = "(core)"
            
            if command_str: # If we have something to show based on filters
                 output_lines.append(f"- [cyan]{name}[/cyan] {source_type}: \"{command_str}\"")
        
        if not output_lines:
            if list_user and not list_core: return "No user aliases defined."
            if list_core and not list_user: return "No core aliases defined."
            return "No aliases to display with current filters."
            
        return "\n".join(output_lines)


# --- Placeholders for custom formats ---
def parse_as_doculing(text_content: str) -> str:
    """Placeholder for Doculing parsing. Returns text as is for V1."""
    # TODO: Implement actual Doculing parsing logic when specifications are available.
    return text_content

def parse_as_markitdown(text_content: str) -> str:
    """Placeholder for Markitdown parsing. Returns text as is for V1."""
    # TODO: Implement actual Markitdown parsing logic when specifications are available.
    return text_content

def get_parser_for_format(format_name: str) -> callable:
    """
    Returns the appropriate parser function based on the format name.
    Defaults to parse_as_plaintext if format is unknown.
    """
    parsers = {
        "text": parse_as_plaintext,
        "markdown": parse_as_markdown,
        "json": parse_as_json,
        "html": parse_as_html,
        "yaml": parse_as_yaml,
        "doculing": parse_as_doculing,       # Placeholder
        "markitdown": parse_as_markitdown,   # Placeholder
    }
    return parsers.get(format_name, parse_as_plaintext) # Default to plaintext parser

def process_text_stream(raw_text_content: str, source_info: dict, console: Console, format_override: str | None = None) -> str | None:
    """
    Processes text from a stream (stdin or clipboard).
    Detects format, parses, and builds the XML structure.

    Args:
        raw_text_content (str): The raw text from the input stream.
        source_info (dict): Information about the source, e.g., {'type': 'stdin'}.
        console (Console): The Rich console object for printing messages.
        format_override (str | None): User-specified format, if any.

    Returns:
        str | None: The XML structured output string, or None if processing fails.
    """
    actual_format = ""
    parsed_content = ""

    if format_override:
        actual_format = format_override.lower()
        console.print(f"[green]Processing input as [bold]{actual_format}[/bold] (user override).[/green]")
    else:
        actual_format = detect_text_format(raw_text_content)
        console.print(f"[green]Detected format: [bold]{actual_format}[/bold][/green]")

    parser_function = get_parser_for_format(actual_format)

    try:
        parsed_content = parser_function(raw_text_content)
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Input specified or detected as JSON, but it's not valid JSON. Details: {e}")
        return None
    except yaml.YAMLError as e: # Assuming PyYAML is used
        console.print(f"[bold red]Error:[/bold red] Input specified or detected as YAML, but it's not valid YAML. Details: {e}")
        return None
    except Exception as e: # Catch-all for other parsing errors
        console.print(f"[bold red]Error:[/bold red] Failed to parse content as {actual_format}. Details: {e}")
        return None

    # XML Generation for the stream
    # This XML structure should be consistent with how single files/sources are wrapped.
    # The escape_xml function currently does nothing, which is correct for content.
    # Attributes of XML tags *should* be escaped if they could contain special chars,
    # but 'stdin', 'clipboard', and format names are safe.
    
    source_type_attr = escape_xml(source_info.get('type', 'unknown_stream'))
    format_attr = escape_xml(actual_format)

    # Build the XML for this specific stream source
    # This part creates the XML for THIS stream.
    # It will be wrapped by <onefilellm_output> in main() if it's the only input,
    # or combined with other sources by combine_xml_outputs() if multiple inputs are supported later.
    
    # For now, let's assume process_text_stream provides the content for a single <source> tag
    # and main() will handle the <onefilellm_output> wrapper.
    
    # XML structure should mirror existing <source> tags for files/URLs where possible
    # but with type="stdin" or type="clipboard".
    # Instead of <file path="...">, we might have a <content_block> or similar.

    # Let's create a simple XML structure for the stream content.
    # The content itself (parsed_content) is NOT XML-escaped, preserving its raw form.
    xml_parts = [
        f'<source type="{source_type_attr}" processed_as_format="{format_attr}">',
        f'<content>{escape_xml(parsed_content)}</content>', # escape_xml does nothing to parsed_content
        f'</source>'
    ]
    final_xml_for_stream = "\n".join(xml_parts)
    
    return final_xml_for_stream

TOKEN = os.getenv('GITHUB_TOKEN', 'default_token_here')
if TOKEN == 'default_token_here':
    # Consider making this a non-fatal warning or prompt if interactive use is common
    print("[bold red]Warning:[/bold red] GITHUB_TOKEN environment variable not set. GitHub API requests may fail or be rate-limited.")
    # raise EnvironmentError("GITHUB_TOKEN environment variable not set.") # Keep commented out if you want it to proceed

headers = {"Authorization": f"token {TOKEN}"} if TOKEN != 'default_token_here' else {}

def process_ipynb_file(temp_file):
    try:
        import nbformat
        from nbconvert import PythonExporter
        with open(temp_file, "r", encoding='utf-8', errors='ignore') as f:
            notebook_content = f.read()
        exporter = PythonExporter()
        python_code, _ = exporter.from_notebook_node(nbformat.reads(notebook_content, as_version=4))
        return python_code
    except Exception as e:
        print(f"[bold red]Error processing notebook {temp_file}: {e}[/bold red]")
        # Return error message instead of raising, wrapped in comments
        return f"# ERROR PROCESSING NOTEBOOK: {e}\n"


# --- XML Handling ---
# --- End XML Handling ---


def process_github_repo(repo_url):
    """
    Processes a GitHub repository, extracting file contents and wrapping them in XML structure.
    """
    api_base_url = "https://api.github.com/repos/"
    repo_url_parts = repo_url.split("https://github.com/")[-1].split("/")
    repo_name = "/".join(repo_url_parts[:2])
    branch_or_tag = ""
    subdirectory = ""

    if len(repo_url_parts) > 2 and repo_url_parts[2] == "tree":
        if len(repo_url_parts) > 3:
            branch_or_tag = repo_url_parts[3]
        if len(repo_url_parts) > 4:
            subdirectory = "/".join(repo_url_parts[4:])
    
    contents_url = f"{api_base_url}{repo_name}/contents"
    if subdirectory:
        contents_url = f"{contents_url}/{subdirectory}"
    if branch_or_tag:
        contents_url = f"{contents_url}?ref={branch_or_tag}"

    # Start XML structure
    repo_content = [f'<source type="github_repository" url="{escape_xml(repo_url)}">']

    def process_directory_recursive(url, repo_content_list):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            files = response.json()

            for file_info in files:
                if file_info["type"] == "dir" and file_info["name"] in EXCLUDED_DIRS:
                    continue

                if file_info["type"] == "file" and is_allowed_filetype(file_info["name"]):
                    print(f"Processing {file_info['path']}...")
                    temp_file = f"temp_{file_info['name']}"
                    try:
                        download_file(file_info["download_url"], temp_file)
                        repo_content_list.append(f'\n<file path="{escape_xml(file_info["path"])}">')
                        if file_info["name"].endswith(".ipynb"):
                            # Append raw code - escape_xml not needed as it does nothing
                            repo_content_list.append(process_ipynb_file(temp_file))
                        else:
                            # Append raw code - escape_xml not needed here
                            repo_content_list.append(safe_file_read(temp_file))
                        repo_content_list.append('</file>')
                    except Exception as e:
                        print(f"[bold red]Error processing file {file_info['path']}: {e}[/bold red]")
                        repo_content_list.append(f'\n<file path="{escape_xml(file_info["path"])}">')
                        repo_content_list.append(f'<error>Failed to download or process: {escape_xml(str(e))}</error>')
                        repo_content_list.append('</file>')
                    finally:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

                elif file_info["type"] == "dir":
                    process_directory_recursive(file_info["url"], repo_content_list)
        except requests.exceptions.RequestException as e:
            print(f"[bold red]Error fetching directory {url}: {e}[/bold red]")
            repo_content_list.append(f'<error>Failed to fetch directory {escape_xml(url)}: {escape_xml(str(e))}</error>')
        except Exception as e: # Catch other potential errors like JSON parsing
             print(f"[bold red]Error processing directory {url}: {e}[/bold red]")
             repo_content_list.append(f'<error>Failed processing directory {escape_xml(url)}: {escape_xml(str(e))}</error>')


    process_directory_recursive(contents_url, repo_content)
    repo_content.append('\n</source>') # Close source tag
    print("GitHub repository processing finished.")
    return "\n".join(repo_content)

def process_local_folder(local_path):
    """
    Processes a local directory, extracting file contents and wrapping them in XML structure.
    """
    def process_local_directory_recursive(current_path, content_list):
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                relative_path = os.path.relpath(item_path, local_path)

                if os.path.isdir(item_path):
                    if item not in EXCLUDED_DIRS:
                        process_local_directory_recursive(item_path, content_list)
                elif os.path.isfile(item_path):
                    if is_allowed_filetype(item):
                        print(f"Processing {item_path}...")
                        content_list.append(f'\n<file path="{escape_xml(relative_path)}">')
                        try:
                            if item.lower().endswith(".ipynb"): # Case-insensitive check
                                content_list.append(process_ipynb_file(item_path))
                            elif item.lower().endswith(".pdf"): # Case-insensitive check
                                content_list.append(_process_pdf_content_from_path(item_path))
                            elif item.lower().endswith(('.xls', '.xlsx')): # Case-insensitive check for Excel files
                                # Need to pop the opening file tag we already added
                                content_list.pop()  # Remove the <file> tag
                                
                                # Generate Markdown for each sheet
                                try:
                                    for sheet, md in excel_to_markdown(item_path).items():
                                        virtual_name = f"{os.path.splitext(relative_path)[0]}_{sheet}.md"
                                        content_list.append(f'\n<file path="{escape_xml(virtual_name)}">')
                                        content_list.append(md)      # raw Markdown table
                                        content_list.append('</file>')
                                except Exception as e:
                                    print(f"[bold red]Error processing Excel file {item_path}: {e}[/bold red]")
                                    # Re-add the original file tag for the error message
                                    content_list.append(f'\n<file path="{escape_xml(relative_path)}">')
                                    content_list.append(f'<e>Failed to process Excel file: {escape_xml(str(e))}</e>')
                                    content_list.append('</file>')
                                continue  # Skip the final </file> for Excel files
                            else:
                                content_list.append(safe_file_read(item_path))
                        except Exception as e:
                            print(f"[bold red]Error reading file {item_path}: {e}[/bold red]")
                            content_list.append(f'<error>Failed to read file: {escape_xml(str(e))}</error>')
                        content_list.append('</file>')
        except Exception as e:
             print(f"[bold red]Error reading directory {current_path}: {e}[/bold red]")
             content_list.append(f'<error>Failed reading directory {escape_xml(current_path)}: {escape_xml(str(e))}</error>')


    # Start XML structure
    content = [f'<source type="local_folder" path="{escape_xml(local_path)}">']
    process_local_directory_recursive(local_path, content)
    content.append('\n</source>') # Close source tag

    print("Local folder processing finished.")
    return '\n'.join(content)


def _process_pdf_content_from_path(file_path):
    """
    Extracts text content from a local PDF file.
    Returns the extracted text or an error message string.
    """
    print(f"  Extracting text from local PDF: {file_path}")
    text_list = []
    try:
        from PyPDF2 import PdfReader
        with open(file_path, 'rb') as pdf_file_obj:
            pdf_reader = PdfReader(pdf_file_obj)
            if not pdf_reader.pages:
                print(f"  [bold yellow]Warning:[/bold yellow] PDF file has no pages or is encrypted: {file_path}")
                return "<e>PDF file has no pages or could not be read (possibly encrypted).</e>"
            
            for i, page_obj in enumerate(pdf_reader.pages):
                try:
                    page_text = page_obj.extract_text()
                    if page_text:
                        text_list.append(page_text)
                except Exception as page_e: # Catch error extracting from a specific page
                     print(f"  [bold yellow]Warning:[/bold yellow] Could not extract text from page {i+1} of {file_path}: {page_e}")
                     text_list.append(f"\n<e>Could not extract text from page {i+1}.</e>\n")
        
        if not text_list:
             print(f"  [bold yellow]Warning:[/bold yellow] No text could be extracted from PDF: {file_path}")
             return "<e>No text could be extracted from PDF.</e>"

        return ' '.join(text_list)
    except Exception as e:
        print(f"[bold red]Error reading PDF file {file_path}: {e}[/bold red]")
        return f"<e>Failed to read or process PDF file: {escape_xml(str(e))}</e>"

def _download_and_read_file(url):
    """
    Downloads and reads the content of a file from a URL.
    Returns the content as text or an error message string.
    """
    print(f"  Downloading and reading content from: {url}")
    try:
        # Add headers conditionally
        response = requests.get(url, headers=headers if TOKEN != 'default_token_here' else None)
        response.raise_for_status()
        
        # Try to determine encoding
        encoding = response.encoding or 'utf-8'
        
        try:
            # Try to decode as text
            content = response.content.decode(encoding)
            return content
        except UnicodeDecodeError:
            # If that fails, try a fallback encoding
            try:
                content = response.content.decode('latin-1')
                return content
            except Exception as decode_err:
                print(f"  [bold yellow]Warning:[/bold yellow] Could not decode content: {decode_err}")
                return f"<e>Failed to decode content: {escape_xml(str(decode_err))}</e>"
                
    except requests.RequestException as e:
        print(f"[bold red]Error downloading file from {url}: {e}[/bold red]")
        return f"<e>Failed to download file: {escape_xml(str(e))}</e>"
    except Exception as e:
        print(f"[bold red]Unexpected error processing file from {url}: {e}[/bold red]")
        return f"<e>Unexpected error: {escape_xml(str(e))}</e>"


def excel_to_markdown(
    file_path: Union[str, Path],
    *,
    skip_rows: int = 0,  # Changed from 3 to 0 to not skip potential headers
    min_header_cells: int = 2,
    sheet_filter: List[str] | None = None,
) -> Dict[str, str]:
    """
    Convert an Excel workbook (.xls / .xlsx) to Markdown.

    Parameters
    ----------
    file_path :
        Path to the workbook.
    skip_rows :
        How many leading rows to ignore before we start hunting for a header row.
        Default is 0 to ensure we don't miss any potential headers.
    min_header_cells :
        Minimum number of non-NA cells that makes a row "look like" a header.
    sheet_filter :
        Optional list of sheet names to include (exact match, case-sensitive).

    Returns
    -------
    Dict[str, str]
        Mapping of ``sheet_name → markdown_table``.
        Empty dict means the workbook had no usable sheets by the above rules.

    Raises
    ------
    ValueError
        If the file extension is not .xls or .xlsx.
    RuntimeError
        If *none* of the sheets meet the header-detection criteria.
    """
    import pandas as pd
    
    file_path = Path(file_path).expanduser().resolve()
    if file_path.suffix.lower() not in {".xls", ".xlsx"}:
        raise ValueError("Only .xls/.xlsx files are supported")

    print(f"Processing Excel file: {file_path}")
    
    # For simple Excel files, it's often better to use header=0 directly
    # Try both approaches: first with automatic header detection, then fallback to header=0
    try:
        # Let pandas pick the right engine (openpyxl for xlsx, xlrd/pyxlsb if installed for xls)
        wb = pd.read_excel(file_path, sheet_name=None, header=None)

        md_tables: Dict[str, str] = {}

        for name, df in wb.items():
            if sheet_filter and name not in sheet_filter:
                continue

            df = df.iloc[skip_rows:].reset_index(drop=True)
            try:
                # Try to find a header row
                header_idx = next(i for i, row in df.iterrows() if row.count() >= min_header_cells)
                
                # Use ffill instead of deprecated method parameter
                header = df.loc[header_idx].copy()
                header = header.ffill()  # Forward-fill NaN values
                
                body = df.loc[header_idx + 1:].copy()
                body.columns = header
                body.dropna(how="all", inplace=True)
                
                # Convert to markdown
                md_tables[name] = body.to_markdown(index=False)
                print(f"  Processed sheet '{name}' with detected header")
                
            except StopIteration:
                # No row looked like a header - skip for now, we'll try again with header=0
                print(f"  No header detected in sheet '{name}', will try fallback")
                continue

        # If no headers were found with our heuristic, try again with header=0
        if not md_tables:
            print("  No headers detected with heuristic, trying with fixed header row")
            wb = pd.read_excel(file_path, sheet_name=None, header=0)
            
            for name, df in wb.items():
                if sheet_filter and name not in sheet_filter:
                    continue
                    
                # Drop rows that are all NaN
                df = df.dropna(how="all")
                
                # Convert to markdown
                md_tables[name] = df.to_markdown(index=False)
                print(f"  Processed sheet '{name}' with fixed header")

        if not md_tables:
            raise RuntimeError("Workbook contained no sheets with usable data")

        return md_tables
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        # Last resort: try with the most basic approach
        wb = pd.read_excel(file_path, sheet_name=None)
        md_tables = {name: df.to_markdown(index=False) for name, df in wb.items() 
                    if not (sheet_filter and name not in sheet_filter)}
                    
        if not md_tables:
            raise RuntimeError(f"Failed to extract any usable data from Excel file: {e}")
            
        return md_tables


def excel_to_markdown_from_url(
    url: str,
    *,
    skip_rows: int = 0,  # Changed from 3 to 0 to not skip potential headers
    min_header_cells: int = 2,
    sheet_filter: List[str] | None = None,
) -> Dict[str, str]:
    """
    Download an Excel workbook from a URL and convert it to Markdown.
    
    This function downloads the Excel file from the URL to a BytesIO buffer
    and then processes it using excel_to_markdown.
    
    Parameters are the same as excel_to_markdown.
    
    Returns
    -------
    Dict[str, str]
        Mapping of ``sheet_name → markdown_table``.
    
    Raises
    ------
    ValueError, RuntimeError, RequestException
        Various errors that might occur during downloading or processing.
    """
    import pandas as pd
    import io
    print(f"  Downloading Excel file from URL: {url}")
    
    try:
        # Add headers conditionally
        response = requests.get(url, headers=headers if TOKEN != 'default_token_here' else None)
        response.raise_for_status()
        
        # Create a BytesIO buffer from the downloaded content
        excel_buffer = io.BytesIO(response.content)
        
        # For simple Excel files, it's often better to use header=0 directly
        # Try both approaches: first with automatic header detection, then fallback to header=0
        try:
            # Let pandas read from the buffer
            wb = pd.read_excel(excel_buffer, sheet_name=None, header=None)
            
            md_tables: Dict[str, str] = {}
            
            for name, df in wb.items():
                if sheet_filter and name not in sheet_filter:
                    continue
                    
                df = df.iloc[skip_rows:].reset_index(drop=True)
                try:
                    # Try to find a header row
                    header_idx = next(i for i, row in df.iterrows() if row.count() >= min_header_cells)
                    
                    # Use ffill instead of deprecated method parameter
                    header = df.loc[header_idx].copy()
                    header = header.ffill()  # Forward-fill NaN values
                    
                    body = df.loc[header_idx + 1:].copy()
                    body.columns = header
                    body.dropna(how="all", inplace=True)
                    
                    # Convert to markdown
                    md_tables[name] = body.to_markdown(index=False)
                    print(f"  Processed sheet '{name}' with detected header")
                    
                except StopIteration:
                    # No row looked like a header - skip for now, we'll try again with header=0
                    print(f"  No header detected in sheet '{name}', will try fallback")
                    continue

            # If no headers were found with our heuristic, try again with header=0
            if not md_tables:
                print("  No headers detected with heuristic, trying with fixed header row")
                excel_buffer.seek(0)  # Reset the buffer position
                wb = pd.read_excel(excel_buffer, sheet_name=None, header=0)
                
                for name, df in wb.items():
                    if sheet_filter and name not in sheet_filter:
                        continue
                        
                    # Drop rows that are all NaN
                    df = df.dropna(how="all")
                    
                    # Convert to markdown
                    md_tables[name] = df.to_markdown(index=False)
                    print(f"  Processed sheet '{name}' with fixed header")

            if not md_tables:
                raise RuntimeError("Workbook contained no sheets with usable data")

            return md_tables
            
        except Exception as e:
            print(f"Error processing Excel file: {e}")
            # Last resort: try with the most basic approach
            excel_buffer.seek(0)  # Reset the buffer position
            wb = pd.read_excel(excel_buffer, sheet_name=None)
            md_tables = {name: df.to_markdown(index=False) for name, df in wb.items() 
                        if not (sheet_filter and name not in sheet_filter)}
                        
            if not md_tables:
                raise RuntimeError(f"Failed to extract any usable data from Excel file: {e}")
                
            return md_tables
        
    except requests.RequestException as e:
        print(f"[bold red]Error downloading Excel file from {url}: {e}[/bold red]")
        raise
    except Exception as e:
        print(f"[bold red]Error processing Excel file from {url}: {e}[/bold red]")
        raise

def process_arxiv_pdf(arxiv_abs_url):
    """
    Downloads and extracts text from an ArXiv PDF, wrapped in XML.
    """
    pdf_url = arxiv_abs_url.replace("/abs/", "/pdf/") + ".pdf"
    temp_pdf_path = 'temp_arxiv.pdf'
    try:
        print(f"Downloading ArXiv PDF from {pdf_url}...")
        response = requests.get(pdf_url)
        response.raise_for_status()

        with open(temp_pdf_path, 'wb') as pdf_file:
            pdf_file.write(response.content)

        print("Extracting text from PDF...")
        text_list = []
        from PyPDF2 import PdfReader
        with open(temp_pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            for i, page in enumerate(range(len(pdf_reader.pages))):
                print(f"  Processing page {i+1}/{len(pdf_reader.pages)}")
                page_text = pdf_reader.pages[page].extract_text()
                if page_text: # Add text only if extraction was successful
                    text_list.append(page_text)

        # Use XML structure
        formatted_text = f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}">\n'
        formatted_text += ' '.join(text_list) # Append raw extracted text
        formatted_text += '\n</source>' # Close source tag
        print("ArXiv paper processed successfully.")
        return formatted_text

    except requests.RequestException as e:
        print(f"[bold red]Error downloading ArXiv PDF {pdf_url}: {e}[/bold red]")
        return f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}"><error>Failed to download PDF: {escape_xml(str(e))}</error></source>'
    except Exception as e: # Catch PdfReader errors or others
        print(f"[bold red]Error processing ArXiv PDF {arxiv_abs_url}: {e}[/bold red]")
        return f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}"><error>Failed to process PDF: {escape_xml(str(e))}</error></source>'
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def fetch_youtube_transcript(url):
    """
    Fetches YouTube transcript using yt-dlp with fallback to youtube_transcript_api, wrapped in XML.
    """
    import tempfile
    import subprocess
    
    def extract_video_id(url):
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    video_id = extract_video_id(url)
    if not video_id:
        print(f"[bold red]Could not extract YouTube video ID from URL: {url}[/bold red]")
        return f'<source type="youtube_transcript" url="{escape_xml(url)}">\n<error>Could not extract video ID from URL.</error>\n</source>'

    transcript_text = None
    error_msg = None
    
    # Try Method 1: Use yt-dlp (most reliable)
    try:
        print(f"Fetching transcript for YouTube video ID: {video_id} using yt-dlp...")
        
        # Create a temporary directory for subtitle files
        with tempfile.TemporaryDirectory() as temp_dir:
            output_template = os.path.join(temp_dir, '%(id)s.%(ext)s')
            
            # yt-dlp command to download subtitles only
            cmd = [
                'yt-dlp',
                '--write-auto-sub',  # Get automatic subtitles if available
                '--write-sub',       # Get manual subtitles if available
                '--sub-lang', 'en',  # Prefer English, but will get others if not available
                '--skip-download',   # Don't download the video
                '--quiet',           # Reduce output
                '--no-warnings',
                '-o', output_template,
                url
            ]
            
            # Run yt-dlp
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Look for subtitle files
            subtitle_files = []
            for ext in ['.en.vtt', '.en.srt', '.vtt', '.srt']:
                subtitle_path = os.path.join(temp_dir, f"{video_id}{ext}")
                if os.path.exists(subtitle_path):
                    subtitle_files.append(subtitle_path)
            
            if subtitle_files:
                # Read the first available subtitle file
                with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse VTT or SRT format to extract just the text
                lines = content.split('\n')
                transcript_lines = []
                
                for line in lines:
                    # Skip timestamp lines and empty lines
                    if '-->' not in line and line.strip() and not line.strip().isdigit() and not line.startswith('WEBVTT'):
                        # Remove HTML tags if present
                        clean_line = re.sub(r'<[^>]+>', '', line)
                        if clean_line.strip():
                            transcript_lines.append(clean_line.strip())
                
                transcript_text = ' '.join(transcript_lines)
                print(f"Transcript fetched successfully using yt-dlp. Got {len(transcript_lines)} lines.")
            else:
                error_msg = "No subtitle files found"
                
    except FileNotFoundError:
        error_msg = "yt-dlp not found. Please install it with: pip install yt-dlp"
    except Exception as e:
        error_msg = f"yt-dlp failed: {str(e)}"
        print(f"yt-dlp method failed: {error_msg}")
    
    # Try Method 2: Fallback to youtube_transcript_api
    if not transcript_text:
        try:
            print("Falling back to youtube_transcript_api...")
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            if isinstance(transcript_list, list) and transcript_list:
                # Format transcript entries
                transcript_lines = []
                for entry in transcript_list:
                    if 'text' in entry:
                        transcript_lines.append(entry['text'])
                
                transcript_text = ' '.join(transcript_lines)
                print(f"Transcript fetched successfully using youtube_transcript_api. Got {len(transcript_list)} entries.")
        except Exception as e:
            if not error_msg:
                error_msg = f"youtube_transcript_api also failed: {str(e)}"
    
    # Format the successful transcript or return error
    if transcript_text:
        # Use XML structure for success
        formatted_text = f'<source type="youtube_transcript" url="{escape_xml(url)}">\n'
        formatted_text += transcript_text
        formatted_text += '\n</source>'
        return formatted_text
    
    # Handle errors
    if not error_msg:
        error_msg = "Unable to fetch transcript with either yt-dlp or youtube_transcript_api"
        
    # Check for common error types and provide better messages
    if "no element found" in error_msg or "ParseError" in error_msg:
        error_msg = "No captions/transcript available for this video"
    elif "NoTranscriptFound" in error_msg:
        error_msg = "No transcript found for this video"
        
    print(f"[bold red]Error fetching YouTube transcript for {url}: {error_msg}[/bold red]")
    return f'<source type="youtube_transcript" url="{escape_xml(url)}">\n<error>{escape_xml(error_msg)}</error>\n</source>'

def preprocess_text(input_file, output_file):
    """
    Preprocesses text, optionally removing stopwords if NLTK is enabled.
    Handles potential XML structure if present (intended for compressed output).
    """
    print("Preprocessing text for compression (if enabled)...")
    with open(input_file, "r", encoding="utf-8") as infile:
        input_text = infile.read()

    # Lazy load NLTK stopwords only when needed
    stop_words = set()
    if ENABLE_COMPRESSION_AND_NLTK:
        try:
            import nltk
            from nltk.corpus import stopwords
            nltk.download("stopwords", quiet=True)
            stop_words = set(stopwords.words("english"))
        except Exception as e:
            print(f"[bold yellow]Warning:[/bold yellow] Failed to download or load NLTK stopwords. Compression will proceed without stopword removal. Error: {e}")

    def process_content(text):
        text = re.sub(r"[\n\r]+", "\n", text)
        text = re.sub(r"[^a-zA-Z0-9\s_.,!?:;@#$%^&*()+\-=[\]{}|\\<>`~'\"/]+", "", text)
        text = re.sub(r"\s+", " ", text)
        text = text.lower()
        if ENABLE_COMPRESSION_AND_NLTK and stop_words:
            words = text.split()
            words = [word for word in words if word not in stop_words]
            text = " ".join(words)
        return text

    try:
        # Attempt to parse as XML - this is mainly relevant if the INPUT
        # already had some structure we wanted to preserve during compression
        root = ET.fromstring(input_text)
        for elem in root.iter():
            if elem.text:
                elem.text = process_content(elem.text)
            if elem.tail:
                elem.tail = process_content(elem.tail)
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        print("Text preprocessing with XML structure preservation completed.")
    except ET.ParseError:
        # If input is not valid XML (likely our case with raw content), process as plain text
        processed_text = process_content(input_text)
        with open(output_file, "w", encoding="utf-8") as out_file:
            out_file.write(processed_text)
        print("Input was not XML. Text preprocessing completed as plain text.")
    except Exception as e:
        print(f"[bold red]Error during text preprocessing: {e}[/bold red]")
        # Fallback: write the original text if preprocessing fails
        with open(output_file, "w", encoding="utf-8") as out_file:
             out_file.write(input_text)
        print("[bold yellow]Warning:[/bold yellow] Preprocessing failed, writing original content to compressed file.")



def get_token_count(text, disallowed_special=[], chunk_size=1000):
    """
    Counts tokens using tiktoken, stripping XML tags first.
    """
    enc = tiktoken.get_encoding("cl100k_base")

    # Restore XML tag removal before counting tokens
    # This gives a count of the actual content, not the structural tags
    text_without_tags = re.sub(r'<[^>]+>', '', text)

    # Split the text without tags into smaller chunks for more robust encoding
    chunks = [text_without_tags[i:i+chunk_size] for i in range(0, len(text_without_tags), chunk_size)]
    total_tokens = 0

    for chunk in chunks:
        try:
            tokens = enc.encode(chunk, disallowed_special=disallowed_special)
            total_tokens += len(tokens)
        except Exception as e:
            print(f"[bold yellow]Warning:[/bold yellow] Error encoding chunk for token count: {e}")
            # Estimate token count for problematic chunk (e.g., len/4)
            total_tokens += len(chunk) // 4

    return total_tokens


def process_web_pdf(url):
    """Downloads and extracts text from a PDF found during web crawl."""
    temp_pdf_path = 'temp_web.pdf'
    try:
        print(f"  Downloading PDF: {url}")
        response = requests.get(url, timeout=30) # Add timeout
        response.raise_for_status()

        # Basic check for PDF content type
        if 'application/pdf' not in response.headers.get('Content-Type', '').lower():
             print(f"  [bold yellow]Warning:[/bold yellow] URL doesn't report as PDF, skipping: {url}")
             return None # Or return an error string

        with open(temp_pdf_path, 'wb') as pdf_file:
            pdf_file.write(response.content)

        print(f"  Extracting text from PDF: {url}")
        text_list = []
        from PyPDF2 import PdfReader
        with open(temp_pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            for page in range(len(pdf_reader.pages)):
                page_text = pdf_reader.pages[page].extract_text()
                if page_text:
                    text_list.append(page_text)
        return ' '.join(text_list)
    except requests.RequestException as e:
        print(f"  [bold red]Error downloading PDF {url}: {e}[/bold red]")
        return f"<error>Failed to download PDF: {escape_xml(str(e))}</error>"
    except Exception as e:
        print(f"  [bold red]Error processing PDF {url}: {e}[/bold red]")
        return f"<error>Failed to process PDF: {escape_xml(str(e))}</error>"
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def crawl_and_extract_text(base_url, max_depth, include_pdfs, ignore_epubs):
    """
    Crawls a website starting from base_url, extracts text, and wraps in XML.
    """
    visited_urls = set()
    urls_to_visit = [(base_url, 0)]
    processed_urls_content = {} # Store URL -> content/error
    # Start XML structure
    all_text = [f'<source type="web_crawl" base_url="{escape_xml(base_url)}">']

    print(f"Starting crawl from: {base_url} (Max Depth: {max_depth}, Include PDFs: {include_pdfs})")

    while urls_to_visit:
        current_url, current_depth = urls_to_visit.pop(0)
        # Normalize URL: remove fragment and ensure scheme
        parsed_url = urlparse(current_url)
        clean_url = urlparse(current_url)._replace(fragment="").geturl()
        if not parsed_url.scheme:
             clean_url = "http://" + clean_url # Default to http if missing

        if clean_url in visited_urls:
            continue

        # Check domain and depth *after* cleaning URL
        if not is_same_domain(base_url, clean_url) or not is_within_depth(base_url, clean_url, max_depth):
             # print(f"Skipping (domain/depth): {clean_url}") # Optional debug
             continue

        if ignore_epubs and clean_url.lower().endswith('.epub'):
            print(f"Skipping (EPUB): {clean_url}")
            visited_urls.add(clean_url)
            continue

        print(f"Processing (Depth {current_depth}): {clean_url}")
        visited_urls.add(clean_url)
        page_content = f'\n<page url="{escape_xml(clean_url)}">' # Start page tag

        try:
            # Handle PDFs separately
            if clean_url.lower().endswith('.pdf'):
                if include_pdfs:
                    pdf_text = process_web_pdf(clean_url)
                    if pdf_text: # Append text or error message from process_web_pdf
                        page_content += f'\n{pdf_text}\n'
                    else: # process_web_pdf returned None (e.g., wrong content type)
                        page_content += '\n<error>Skipped non-PDF content reported at PDF URL.</error>\n'
                else:
                    print(f"  Skipping PDF (include_pdfs=False): {clean_url}")
                    page_content += '\n<skipped>PDF ignored by configuration</skipped>\n'

            # Handle HTML pages
            else:
                 # Add timeout to requests
                response = requests.get(clean_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                response.raise_for_status()

                # Basic check for HTML content type
                if 'text/html' not in response.headers.get('Content-Type', '').lower():
                    print(f"  [bold yellow]Warning:[/bold yellow] Skipping non-HTML page: {clean_url} (Content-Type: {response.headers.get('Content-Type')})")
                    page_content += f'\n<skipped>Non-HTML content type: {escape_xml(response.headers.get("Content-Type", "N/A"))}</skipped>\n'
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Remove scripts, styles, etc.
                    for element in soup(['script', 'style', 'head', 'title', 'meta', '[document]', 'nav', 'footer', 'aside']): # Added common noise tags
                        element.decompose()
                    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
                    for comment in comments:
                        comment.extract()
                    # Get text, try to preserve some structure with newlines
                    text = soup.get_text(separator='\n', strip=True)
                    page_content += f'\n{text}\n' # Append raw extracted text

                    # Find links for the next level if depth allows
                    if current_depth < max_depth:
                        for link in soup.find_all('a', href=True):
                            try:
                                new_url_raw = link['href']
                                if new_url_raw and not new_url_raw.startswith(('mailto:', 'javascript:', '#')):
                                    new_url = urljoin(clean_url, new_url_raw)
                                    parsed_new = urlparse(new_url)
                                    # Add scheme if missing for domain/depth checks
                                    if not parsed_new.scheme:
                                         new_url = parsed_new._replace(scheme=urlparse(clean_url).scheme).geturl()

                                    new_clean_url = urlparse(new_url)._replace(fragment="").geturl()

                                    if new_clean_url not in visited_urls:
                                        # Check domain/depth *before* adding to queue
                                        if is_same_domain(base_url, new_clean_url) and is_within_depth(base_url, new_clean_url, max_depth):
                                             if not (ignore_epubs and new_clean_url.lower().endswith('.epub')):
                                                # Add only if valid and not already visited
                                                if (new_clean_url, current_depth + 1) not in urls_to_visit:
                                                     urls_to_visit.append((new_clean_url, current_depth + 1))
                            except Exception as link_err: # Catch errors parsing individual links
                                print(f"  [bold yellow]Warning:[/bold yellow] Error parsing link '{link.get('href')}': {link_err}")


        except requests.exceptions.Timeout:
             print(f"[bold red]Timeout retrieving {clean_url}[/bold red]")
             page_content += f'\n<error>Timeout during request</error>\n'
        except requests.RequestException as e:
            print(f"[bold red]Failed to retrieve {clean_url}: {e}[/bold red]")
            page_content += f'\n<error>Failed to retrieve URL: {escape_xml(str(e))}</error>\n'
        except Exception as e: # Catch other errors like BeautifulSoup issues
             print(f"[bold red]Error processing page {clean_url}: {e}[/bold red]")
             page_content += f'\n<error>Error processing page: {escape_xml(str(e))}</error>\n'

        page_content += '</page>' # Close page tag
        all_text.append(page_content)
        processed_urls_content[clean_url] = page_content # Store for processed list


    all_text.append('\n</source>') # Close source tag
    print("Web crawl finished.")
    formatted_content = '\n'.join(all_text)

    return {
        'content': formatted_content,
        'processed_urls': list(processed_urls_content.keys()) # Return URLs we attempted to process
    }


# --- Helper functions for DocCrawler ---
def _detect_code_language_heuristic(code: str) -> str:
    """Attempt to detect programming language of code block with naive heuristics."""
    if re.search(r'^\s*(import|from)\s+\w+\s+import|def\s+\w+\s*\(|class\s+\w+[:\(]', code, re.MULTILINE):
        return "python"
    elif re.search(r'^\s*(function|const|let|var|import)\s+|=\>|{\s*\n|export\s+', code, re.MULTILINE):
        return "javascript"
    elif re.search(r'^\s*(#include|int\s+main|using\s+namespace)', code, re.MULTILINE):
        return "cpp"
    elif re.search(r'^\s*(public\s+class|import\s+java|@Override)', code, re.MULTILINE):
        return "java"
    elif re.search(r'<\?php|\$\w+\s*=', code, re.MULTILINE):
        return "php"
    elif re.search(r'^\s*(use\s+|fn\s+\w+|let\s+mut|impl)', code, re.MULTILINE):
        return "rust"
    elif re.search(r'^\s*(package\s+main|import\s+\(|func\s+\w+\s*\()', code, re.MULTILINE):
        return "go"
    elif re.search(r'<html|<body|<div|<script|<style', code, re.IGNORECASE | re.MULTILINE):
        return "html"
    elif re.search(r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)', code, re.IGNORECASE | re.MULTILINE):
        return "sql"
    return "code"  # Default if no strong signal


def _clean_text_content(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]', ' ', text)  # Various space chars
    text = re.sub(r'[\u2018\u2019]', "'", text)  # Smart quotes to standard
    text = re.sub(r'[\u201C\u201D]', '"', text)  # Smart quotes to standard
    return text


class DocCrawler:
    """Advanced web crawler for extracting structured content from websites."""
    
    def __init__(self, start_url: str, cli_args: object, console_obj):
        self.start_url = start_url
        self.config = cli_args  # This will be the argparse namespace or similar
        self.console = console_obj
        
        self.output_xml_parts: List[str] = []
        self.visited_urls: Set[str] = set()
        self.pages_crawled = 0
        self.failed_urls: List[Tuple[str, str]] = []
        
        parsed_start = urlparse(self.start_url)
        self.domain = parsed_start.netloc
        self.start_url_path_prefix = parsed_start.path.rstrip('/') or "/"  # For --crawl-restrict-path
        
        self.robots_parsers: Dict[str, RobotFileParser] = {}
        self.session = None  # Will be aiohttp.ClientSession when initialized
        self.rich_progress = None  # For Rich progress bar
        self.progress_task_id = None
        
        # Map CLI args to attributes for convenience
        # Using defaults from change.md since CLI args aren't implemented yet
        self.max_depth = getattr(self.config, 'crawl_max_depth', 3)
        self.max_pages = getattr(self.config, 'crawl_max_pages', 1000)  # Increased default from 100 to 1000
        self.user_agent = getattr(self.config, 'crawl_user_agent', "OneFileLLMCrawler/1.1")
        self.delay = getattr(self.config, 'crawl_delay', 0.25)
        self.include_pattern = re.compile(self.config.crawl_include_pattern) if getattr(self.config, 'crawl_include_pattern', None) else None
        self.exclude_pattern = re.compile(self.config.crawl_exclude_pattern) if getattr(self.config, 'crawl_exclude_pattern', None) else None
        self.timeout = getattr(self.config, 'crawl_timeout', 20)
        self.include_images = getattr(self.config, 'crawl_include_images', False)
        self.include_code = getattr(self.config, 'crawl_include_code', True)
        self.extract_headings = getattr(self.config, 'crawl_extract_headings', True)
        self.follow_links = getattr(self.config, 'crawl_follow_links', False)
        self.clean_html = getattr(self.config, 'crawl_clean_html', True)
        self.strip_js = getattr(self.config, 'crawl_strip_js', True)
        self.strip_css = getattr(self.config, 'crawl_strip_css', True)
        self.strip_comments = getattr(self.config, 'crawl_strip_comments', True)
        self.respect_robots = getattr(self.config, 'crawl_respect_robots', False)  # Changed to False for backward compatibility
        self.concurrency = getattr(self.config, 'crawl_concurrency', 3)
        self.restrict_path = getattr(self.config, 'crawl_restrict_path', False)
        self.include_pdfs = getattr(self.config, 'crawl_include_pdfs', True)
        self.ignore_epubs = getattr(self.config, 'crawl_ignore_epubs', True)

    async def _init_session(self):
        import aiohttp
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def _close_session(self):
        if self.session:
            await self.session.close()

    async def _can_fetch_robots(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if domain not in self.robots_parsers:
            robots_url = f"{parsed_url.scheme}://{domain}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                # RobotFileParser.read() is synchronous. Run in executor.
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, parser.read)
                self.robots_parsers[domain] = parser
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not fetch/parse robots.txt for {domain}: {e}[/yellow]")
                return True  # Default to allow if robots.txt is inaccessible
        
        return self.robots_parsers[domain].can_fetch(self.user_agent, url)

    def _should_crawl_url(self, url: str) -> bool:
        parsed_url = urlparse(url)
        
        if parsed_url.scheme not in ('http', 'https'):
            return False
        
        # Handle external links based on --crawl-follow-links
        if not self.follow_links and parsed_url.netloc != self.domain:
            return False

        if self.restrict_path:
            # Ensure current URL's path starts with the initial URL's path prefix
            current_path_normalized = parsed_url.path.rstrip('/') or "/"
            if not current_path_normalized.startswith(self.start_url_path_prefix):
                return False

        if url in self.visited_urls:
            return False
        
        if self.pages_crawled >= self.max_pages:
            return False
        
        if self.include_pattern and not self.include_pattern.search(url):
            return False
        
        if self.exclude_pattern and self.exclude_pattern.search(url):
            return False

        if self.ignore_epubs and url.lower().endswith('.epub'):
            # Only print skip message if not using progress bar
            if not self.rich_progress:
                self.console.print(f"  [dim]Skipping EPUB: {url}[/dim]")
            return False
            
        # Note: robots.txt check is async, so it's done in the worker.
        return True

    async def _fetch_url_content(self, url: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        if not self.session:
            await self._init_session()
        
        try:
            async with self.session.get(url, timeout=self.timeout) as response:
                content_type_header = response.headers.get('Content-Type', '')
                if response.status != 200:
                    return None, f"HTTP Error {response.status}: {response.reason}", content_type_header
                
                # Read content as bytes first to handle different types
                content_bytes = await response.read()
                return content_bytes, None, content_type_header
                
        except asyncio.TimeoutError:
            return None, "Request timed out", None
        except Exception as e:
            # Check if it's an aiohttp ClientError
            if e.__class__.__name__ == 'ClientError':
                return None, f"Client error: {e}", None
            return None, f"Client error: {e}", None
        except Exception as e:
            return None, f"Unexpected fetch error: {e}", None

    def _extract_page_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href'].strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            
            full_url = urljoin(base_url, href)
            # Normalize: remove fragment, ensure scheme for external links
            parsed_new_url = urlparse(full_url)
            normalized_url = parsed_new_url._replace(fragment="").geturl()
            
            links.append(normalized_url)
        return links

    def _process_html_to_structured_data(self, html_content: str, url: str) -> Dict:
        try:
            doc = Document(html_content)
            title = _clean_text_content(doc.title())
            
            if self.clean_html:
                # Use readability's cleaned HTML body
                main_content_html = doc.summary()
                soup = BeautifulSoup(main_content_html, 'lxml') 
            else:
                soup = BeautifulSoup(html_content, 'lxml')

            if self.strip_js:
                for script_tag in soup.find_all('script'):
                    script_tag.decompose()
            if self.strip_css:
                for style_tag in soup.find_all('style'):
                    style_tag.decompose()
            if self.strip_comments:
                for comment_tag in soup.find_all(string=lambda text_node: isinstance(text_node, Comment)):
                    comment_tag.extract()
            
            meta_tags = {}
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    meta_tags[_clean_text_content(name)] = _clean_text_content(content)
            
            structured_content_blocks = self._extract_structured_content_from_soup(soup, url)
            
            return {
                'url': url,
                'title': title,
                'meta': meta_tags,
                'content_blocks': structured_content_blocks
            }
        except Exception as e:
            self.console.print(f"[bold red]Error processing HTML for {url}: {e}[/bold red]")
            return {
                'url': url,
                'title': f"Error processing page: {url}",
                'meta': {},
                'content_blocks': [{'type': 'error', 'text': f"Failed to process HTML: {e}"}]
            }

    def _extract_structured_content_from_soup(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        content_blocks = []
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'table']):
            if element.name.startswith('h'):
                level = int(element.name[1])
                text = _clean_text_content(element.get_text())
                if text:
                    content_blocks.append({'type': 'heading', 'level': level, 'text': text})
            elif element.name == 'p':
                text = _clean_text_content(element.get_text())
                if text:
                    content_blocks.append({'type': 'paragraph', 'text': text})
            elif element.name in ('ul', 'ol'):
                items = [_clean_text_content(li.get_text()) for li in element.find_all('li', recursive=False) if _clean_text_content(li.get_text())]
                if items:
                    content_blocks.append({'type': 'list', 'list_type': element.name, 'items': items})
            elif element.name == 'pre':  # Often contains code
                code_text = element.get_text()  # Keep original spacing
                if self.include_code and code_text.strip():
                    # Attempt to find language from class attribute if present
                    lang_class = element.get('class', [])
                    lang = "code"  # default
                    for cls in lang_class:
                        if cls.startswith('language-'):
                            lang = cls.replace('language-', '')
                            break
                    if lang == "code":  # if not found in class, use heuristic
                        lang = _detect_code_language_heuristic(code_text)
                    content_blocks.append({'type': 'code', 'language': lang, 'code': code_text})
            elif element.name == 'table':
                headers = []
                rows_data = []
                # Extract headers (th)
                for th in element.select('thead tr th, table > tr:first-child > th'):
                    headers.append(_clean_text_content(th.get_text()))
                # Extract rows (tr) and cells (td)
                for row_element in element.select('tbody tr, table > tr'):
                    # Avoid re-processing header row if it was caught by th selector
                    if row_element.find('th') and headers:
                        if all(_clean_text_content(th.get_text()) in headers for th in row_element.find_all('th')):
                            continue 
                    
                    cells = [_clean_text_content(td.get_text()) for td in row_element.find_all(['td', 'th'])]
                    if cells:
                        rows_data.append(cells)
                if not headers and rows_data:  # If no <th>, use first row as header
                    headers = rows_data.pop(0)

                if rows_data:  # Only add table if it has data rows
                    content_blocks.append({'type': 'table', 'headers': headers, 'rows': rows_data})

        if self.include_images:
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src')
                alt = _clean_text_content(img_tag.get('alt', ''))
                if src:
                    img_url = urljoin(base_url, src)
                    content_blocks.append({'type': 'image', 'url': img_url, 'alt_text': alt})
        return content_blocks

    def _initialize_xml_output(self):
        self.output_xml_parts = [f'<source type="web_crawl" base_url="{escape_xml(self.start_url)}">']

    def _add_page_to_xml_output(self, page_data: Dict):
        page_xml_parts = [f'<page url="{escape_xml(page_data["url"])}">']
        page_xml_parts.append(f'<title>{escape_xml(page_data.get("title", "N/A"))}</title>')

        if page_data.get('meta'):
            meta_xml_parts = ['<meta>']
            for key, value in page_data['meta'].items():
                meta_xml_parts.append(f'<meta_item name="{escape_xml(key)}">{escape_xml(str(value))}</meta_item>')
            meta_xml_parts.append('</meta>')
            page_xml_parts.append("".join(meta_xml_parts))

        content_xml_parts = ['<content>']
        for block in page_data.get('content_blocks', []):
            block_type = block.get('type')
            if block_type == 'paragraph':
                content_xml_parts.append(f'<paragraph>{escape_xml(block.get("text", ""))}</paragraph>')
            elif block_type == 'heading':
                content_xml_parts.append(f'<heading level="{block.get("level", 0)}">{escape_xml(block.get("text", ""))}</heading>')
            elif block_type == 'list':
                list_items_xml = "".join([f'<item>{escape_xml(item)}</item>' for item in block.get("items", [])])
                content_xml_parts.append(f'<list type="{block.get("list_type", "ul")}">{list_items_xml}</list>')
            elif block_type == 'code':
                # For code, do not escape_xml the content to preserve syntax
                content_xml_parts.append(f'<code language="{escape_xml(block.get("language", "unknown"))}">{block.get("code", "")}</code>')
            elif block_type == 'image':
                content_xml_parts.append(f'<image src="{escape_xml(block.get("url", ""))}" alt_text="{escape_xml(block.get("alt_text", ""))}" />')
            elif block_type == 'table':
                table_parts = ['<table>']
                if block.get('headers'):
                    header_row = "".join([f'<th>{escape_xml(h)}</th>' for h in block['headers']])
                    table_parts.append(f'<thead><tr>{header_row}</tr></thead>')
                
                body_rows = []
                for row_data in block.get('rows', []):
                    cell_row = "".join([f'<td>{escape_xml(cell)}</td>' for cell in row_data])
                    body_rows.append(f'<tr>{cell_row}</tr>')
                if body_rows:
                    table_parts.append(f'<tbody>{"".join(body_rows)}</tbody>')
                table_parts.append('</table>')
                content_xml_parts.append("".join(table_parts))
            elif block_type == 'error':
                content_xml_parts.append(f'<error_in_page>{escape_xml(block.get("text", "Unknown page error"))}</error_in_page>')

        content_xml_parts.append('</content>')
        page_xml_parts.append("".join(content_xml_parts))
        page_xml_parts.append('</page>')
        self.output_xml_parts.append("\n".join(page_xml_parts))
    
    async def _process_pdf_content_from_bytes(self, pdf_bytes: bytes, url: str) -> Optional[Dict]:
        self.console.print(f"  [cyan]Extracting text from PDF:[/cyan] {url}")
        try:
            from PyPDF2 import PdfReader
            pdf_file_obj = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file_obj)
            if not pdf_reader.pages:
                self.console.print(f"  [yellow]Warning: PDF has no pages or is encrypted: {url}[/yellow]")
                return None
            
            text_list = []
            for i, page_obj in enumerate(pdf_reader.pages):
                try:
                    page_text = page_obj.extract_text()
                    if page_text:
                        text_list.append(page_text)
                except Exception as page_e:
                    self.console.print(f"  [yellow]Warning: Could not extract text from page {i+1} of {url}: {page_e}[/yellow]")
            
            if not text_list:
                self.console.print(f"  [yellow]Warning: No text extracted from PDF: {url}[/yellow]")
                return None
            
            full_text = "\n\n--- Page Break ---\n\n".join(text_list)
            return {
                'url': url,
                'title': f"PDF: {os.path.basename(urlparse(url).path)}",
                'meta': {},
                'content_blocks': [{'type': 'paragraph', 'text': full_text}]
            }
        except Exception as e:
            self.console.print(f"[bold red]Error reading PDF content for {url}: {e}[/bold red]")
            return {
                'url': url,
                'title': f"Error processing PDF: {url}",
                'meta': {},
                'content_blocks': [{'type': 'error', 'text': f"Failed to process PDF content: {e}"}]
            }

    async def _worker(self, queue: asyncio.Queue):
        while True:
            try:
                url, depth = await queue.get()

                if self.pages_crawled >= self.max_pages:
                    queue.task_done()
                    continue
                
                # Perform async robots.txt check here
                if not await self._can_fetch_robots(url):
                    self.console.print(f"  [dim]Skipping (robots.txt): {url}[/dim]")
                    self.visited_urls.add(url)
                    queue.task_done()
                    continue

                # _should_crawl_url is synchronous and checks other conditions
                if not self._should_crawl_url(url):
                    self.visited_urls.add(url)
                    queue.task_done()
                    continue

                self.visited_urls.add(url)
                await asyncio.sleep(self.delay)

                # Only print crawling message if not using progress bar
                if not self.rich_progress:
                    self.console.print(f"[cyan]Crawling (Depth {depth}):[/cyan] {url}")
                
                content_bytes, error_msg, content_type_header = await self._fetch_url_content(url)

                page_data_dict = None
                if error_msg:
                    self.console.print(f"  [yellow]Failed to fetch {url}: {error_msg}[/yellow]")
                    self.failed_urls.append((url, error_msg))
                elif content_bytes and content_type_header:
                    if 'application/pdf' in content_type_header.lower() and self.include_pdfs:
                        page_data_dict = await self._process_pdf_content_from_bytes(content_bytes, url)
                    elif 'text/html' in content_type_header.lower():
                        try:
                            # Attempt to decode HTML content
                            html_text_content = content_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                html_text_content = content_bytes.decode('latin-1')
                            except UnicodeDecodeError as ude:
                                self.console.print(f"  [yellow]Failed to decode HTML for {url}: {ude}[/yellow]")
                                self.failed_urls.append((url, f"Unicode decode error: {ude}"))
                                html_text_content = None
                        if html_text_content:
                            page_data_dict = self._process_html_to_structured_data(html_text_content, url)
                    else:
                        self.console.print(f"  [dim]Skipping non-HTML/PDF content ({content_type_header}): {url}[/dim]")
                
                if page_data_dict:
                    self._add_page_to_xml_output(page_data_dict)
                    self.pages_crawled += 1
                    if self.rich_progress and self.progress_task_id is not None:
                        self.rich_progress.update(self.progress_task_id, advance=1, description=f"Crawled {self.pages_crawled}/{self.max_pages} pages")

                # Add new links to queue if depth and page count allow
                if page_data_dict and depth < self.max_depth and 'text/html' in (content_type_header or ""):
                    if 'html_text_content' in locals() and html_text_content:
                        soup_for_links = BeautifulSoup(html_text_content, 'lxml')
                        new_links = self._extract_page_links(soup_for_links, url)
                        for link_to_add in new_links:
                            if self._should_crawl_url(link_to_add) and self.pages_crawled < self.max_pages:
                                await queue.put((link_to_add, depth + 1))
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                current_url_in_worker = url if 'url' in locals() else "unknown"
                self.console.print(f"[bold red]Unexpected error in worker for URL {current_url_in_worker}: {type(e).__name__} - {e}[/bold red]")
                import traceback
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
                if 'queue' in locals() and hasattr(queue, 'task_done'):
                     queue.task_done()

    async def crawl(self, rich_progress_bar) -> str:
        self.rich_progress = rich_progress_bar
        self._initialize_xml_output()
        await self._init_session()

        queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
        await queue.put((self.start_url, 0))

        if self.rich_progress:
            self.progress_task_id = self.rich_progress.add_task(
                f"[cyan]Crawling {self.start_url}...", 
                total=self.max_pages, 
                completed=0
            )
        
        worker_tasks = []
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker(queue), name=f"Worker-{i+1}")
            worker_tasks.append(task)

        try:
            await queue.join()
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Crawl interrupted by user. Finalizing...[/bold yellow]")
        finally:
            # Cancel all worker tasks
            for task in worker_tasks:
                task.cancel()
            # Wait for all tasks to complete their cancellation
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            
            await self._close_session()

        self.output_xml_parts.append('</source>')
        
        if self.rich_progress and self.progress_task_id is not None:
            self.rich_progress.update(self.progress_task_id, completed=self.pages_crawled, description="Crawl finished")

        self.console.print(f"\n[green]Crawl complete.[/green] Pages crawled: {self.pages_crawled}. Failed URLs: {len(self.failed_urls)}")
        if self.failed_urls:
            self.console.print(f"[yellow]Failed URLs ({len(self.failed_urls)}):[/yellow]")
            for failed_url, reason in self.failed_urls[:5]:
                self.console.print(f"  - {failed_url} : {reason}")
            if len(self.failed_urls) > 5:
                self.console.print(f"  ... and {len(self.failed_urls) - 5} more (check verbose logs if enabled).")
        
        return "\n".join(self.output_xml_parts)


async def process_web_crawl(base_url: str, cli_args: object, console: Console, progress_bar) -> str:
    """
    Processes web crawling using the new DocCrawler.
    This function will replace crawl_and_extract_text once DocCrawler is ported.
    
    Args:
        base_url: The URL to start crawling from
        cli_args: Namespace object with CLI arguments for crawler configuration
        console: Rich Console object for output
        progress_bar: Rich Progress bar for tracking progress
        
    Returns:
        XML string with crawled content
    """
    console.print(f"\n[bold green]Initiating web crawl for:[/bold green] [bright_yellow]{base_url}[/bright_yellow]")
    
    # Create and run the DocCrawler
    crawler = DocCrawler(start_url=base_url, cli_args=cli_args, console_obj=console)
    
    try:
        xml_string_output = await crawler.crawl(rich_progress_bar=progress_bar)
        return xml_string_output
    except Exception as e:
        console.print(f"[bold red]Error during web crawl for {base_url}: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return f'<source type="web_crawl" base_url="{escape_xml(base_url)}"><error>Crawl failed: {escape_xml(str(e))}</error></source>'


def process_doi_or_pmid(identifier):
    """
    Attempts to fetch a paper PDF via Sci-Hub using DOI or PMID, wrapped in XML.
    Note: Sci-Hub access can be unreliable.
    """
    # Use a more reliable Sci-Hub domain if known, otherwise fallback
    sci_hub_domains = ['https://sci-hub.se/', 'https://sci-hub.st/', 'https://sci-hub.ru/'] # Add more mirrors if needed
    pdf_filename = f"temp_{identifier.replace('/', '-')}.pdf"
    pdf_text = None

    for base_url in sci_hub_domains:
        print(f"Attempting Sci-Hub domain: {base_url} for identifier: {identifier}")
        headers = { # Headers might help avoid blocks
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
        payload = {'request': identifier}

        try:
            # Initial request to Sci-Hub page
            response = requests.post(base_url, headers=headers, data=payload, timeout=60)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the PDF link/embed (Sci-Hub structure varies)
            pdf_url = None
            # Try common patterns: iframe#pdf, button onclick location.href, direct links
            pdf_frame = soup.find('iframe', id='pdf')
            if pdf_frame and pdf_frame.get('src'):
                pdf_url = urljoin(base_url, pdf_frame['src'])
            else:
                # Look for buttons or links directing to the PDF
                pdf_button = soup.find('button', onclick=lambda x: x and 'location.href=' in x)
                if pdf_button:
                    match = re.search(r"location\.href='(//.*?)'", pdf_button['onclick'])
                    if match:
                         # Need to add scheme if missing (often //...)
                        pdf_url_part = match.group(1)
                        if pdf_url_part.startswith("//"):
                            pdf_url = "https:" + pdf_url_part
                        else:
                             pdf_url = urljoin(base_url, pdf_url_part)

            if not pdf_url:
                 print(f"  Could not find PDF link on page from {base_url}")
                 continue # Try next domain

            print(f"  Found potential PDF URL: {pdf_url}")
            # Ensure URL has scheme for requests
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            elif not pdf_url.startswith("http"):
                 pdf_url = urljoin(base_url, pdf_url)


            print(f"  Downloading PDF from: {pdf_url}")
            # Download the PDF file
            pdf_response = requests.get(pdf_url, headers=headers, timeout=120) # Longer timeout for PDF download
            pdf_response.raise_for_status()

            # Check content type again
            if 'application/pdf' not in pdf_response.headers.get('Content-Type', '').lower():
                 print(f"  [bold yellow]Warning:[/bold yellow] Downloaded content is not PDF from {pdf_url}, trying next domain.")
                 continue


            with open(pdf_filename, 'wb') as f:
                f.write(pdf_response.content)

            print("  Extracting text from PDF...")
            from PyPDF2 import PdfReader
            with open(pdf_filename, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                text_list = []
                for page in range(len(pdf_reader.pages)):
                    page_text = pdf_reader.pages[page].extract_text()
                    if page_text:
                        text_list.append(page_text)
                pdf_text = " ".join(text_list)

            print(f"Identifier {identifier} processed successfully via {base_url}.")
            break # Success, exit the loop

        except requests.exceptions.Timeout:
             print(f"  Timeout connecting to {base_url} or downloading PDF.")
             continue # Try next domain
        except requests.RequestException as e:
            print(f"  Error with {base_url}: {e}")
            continue # Try next domain
        except Exception as e: # Catch other errors (PDF parsing, etc.)
             print(f"  Error processing identifier {identifier} with {base_url}: {e}")
             continue # Try next domain
        finally:
             # Clean up temp file even if loop continues
             if os.path.exists(pdf_filename):
                 os.remove(pdf_filename)

    # After trying all domains
    if pdf_text is not None:
        # Use XML structure for success
        formatted_text = f'<source type="sci-hub" identifier="{escape_xml(identifier)}">\n'
        formatted_text += pdf_text # Append raw extracted text
        formatted_text += '\n</source>'
        return formatted_text
    else:
        print(f"[bold red]Failed to process identifier {identifier} using all Sci-Hub domains tried.[/bold red]")
        # Use XML structure for error
        error_text = f'<source type="sci-hub" identifier="{escape_xml(identifier)}">\n'
        error_text += f'<error>Could not retrieve or process PDF via Sci-Hub.</error>\n'
        error_text += '</source>'
        return error_text


def process_github_pull_request(pull_request_url):
    """
    Processes a GitHub Pull Request, including details, diff, comments, and associated repo content, wrapped in XML.
    """
    if TOKEN == 'default_token_here':
         print("[bold red]Error:[/bold red] GitHub Token not set. Cannot process GitHub Pull Request.")
         return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>GitHub Token not configured.</error></source>'

    url_parts = pull_request_url.split("/")
    if len(url_parts) < 7 or url_parts[-2] != 'pull':
        print(f"[bold red]Invalid GitHub Pull Request URL: {pull_request_url}[/bold red]")
        return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Invalid URL format.</error></source>'

    repo_owner = url_parts[3]
    repo_name = url_parts[4]
    pull_request_number = url_parts[-1]

    api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pull_request_number}"
    repo_url_for_content = f"https://github.com/{repo_owner}/{repo_name}" # Base repo URL

    try:
        print(f"Fetching PR data for: {pull_request_url}")
        response = requests.get(api_base_url, headers=headers)
        response.raise_for_status()
        pull_request_data = response.json()

        # Start XML structure
        formatted_text_list = [f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}">']
        formatted_text_list.append(f'<title>{escape_xml(pull_request_data.get("title", "N/A"))}</title>') # Use .get for safety
        formatted_text_list.append('<description>')
        formatted_text_list.append(pull_request_data.get('body', "") or "") # Append raw body, handle None
        formatted_text_list.append('</description>')
        details = (
            f"User: {pull_request_data.get('user', {}).get('login', 'N/A')}, "
            f"State: {pull_request_data.get('state', 'N/A')}, "
            f"Commits: {pull_request_data.get('commits', 'N/A')}, "
            f"Base: {pull_request_data.get('base', {}).get('label', 'N/A')}, "
            f"Head: {pull_request_data.get('head', {}).get('label', 'N/A')}"
        )
        formatted_text_list.append(f'<details>{escape_xml(details)}</details>')

        # Fetch and add the diff
        diff_url = pull_request_data.get("diff_url")
        if diff_url:
            print("Fetching PR diff...")
            diff_response = requests.get(diff_url, headers=headers)
            diff_response.raise_for_status()
            pull_request_diff = diff_response.text
            formatted_text_list.append('\n<diff>')
            formatted_text_list.append(pull_request_diff) # Append raw diff
            formatted_text_list.append('</diff>')
        else:
             formatted_text_list.append('\n<diff><error>Could not retrieve diff URL.</error></diff>')


        # Fetch and add comments (PR comments + review comments)
        all_comments_data = []
        comments_url = pull_request_data.get("comments_url")
        review_comments_url = pull_request_data.get("review_comments_url")

        if comments_url:
            print("Fetching PR comments...")
            comments_response = requests.get(comments_url, headers=headers)
            if comments_response.ok:
                all_comments_data.extend(comments_response.json())
            else:
                 print(f"[bold yellow]Warning:[/bold yellow] Could not fetch PR comments: {comments_response.status_code}")

        if review_comments_url:
             print("Fetching PR review comments...")
             review_comments_response = requests.get(review_comments_url, headers=headers)
             if review_comments_response.ok:
                 all_comments_data.extend(review_comments_response.json())
             else:
                 print(f"[bold yellow]Warning:[/bold yellow] Could not fetch review comments: {review_comments_response.status_code}")


        if all_comments_data:
            formatted_text_list.append('\n<comments>')
             # Optional: Sort comments by creation date or position
            all_comments_data.sort(key=lambda c: c.get("created_at", ""))
            for comment in all_comments_data:
                 author = comment.get('user', {}).get('login', 'N/A')
                 body = comment.get('body', '') or "" # Handle None
                 # Add context if available (e.g., path, line for review comments)
                 path = comment.get('path')
                 line = comment.get('line') or comment.get('original_line')
                 context = f' path="{escape_xml(path)}"' if path else ''
                 context += f' line="{line}"' if line else ''
                 formatted_text_list.append(f'<comment author="{escape_xml(author)}"{context}>')
                 formatted_text_list.append(body) # Append raw comment body
                 formatted_text_list.append('</comment>')
            formatted_text_list.append('</comments>')

        # Add repository content (will include its own <source> tag)
        print(f"Fetching associated repository content from: {repo_url_for_content}")
        # Use the base branch if available, otherwise default branch content
        base_branch_ref = pull_request_data.get('base', {}).get('ref')
        repo_url_with_ref = f"{repo_url_for_content}/tree/{base_branch_ref}" if base_branch_ref else repo_url_for_content
        repo_content = process_github_repo(repo_url_with_ref) # process_github_repo returns XML string

        formatted_text_list.append('\n<!-- Associated Repository Content -->') # XML Comment
        formatted_text_list.append(repo_content) # Append the XML output directly

        formatted_text_list.append('\n</source>') # Close main PR source tag

        print(f"Pull request {pull_request_number} and repository content processed successfully.")
        return "\n".join(formatted_text_list)

    except requests.RequestException as e:
        print(f"[bold red]Error fetching GitHub PR data for {pull_request_url}: {e}[/bold red]")
        return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Failed to fetch PR data: {escape_xml(str(e))}</error></source>'
    except Exception as e: # Catch other potential errors
         print(f"[bold red]Unexpected error processing GitHub PR {pull_request_url}: {e}[/bold red]")
         return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Unexpected error: {escape_xml(str(e))}</error></source>'


def process_github_issue(issue_url):
    """
    Processes a GitHub Issue, including details, comments, and associated repo content, wrapped in XML.
    """
    if TOKEN == 'default_token_here':
         print("[bold red]Error:[/bold red] GitHub Token not set. Cannot process GitHub Issue.")
         return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>GitHub Token not configured.</error></source>'

    url_parts = issue_url.split("/")
    if len(url_parts) < 7 or url_parts[-2] != 'issues':
        print(f"[bold red]Invalid GitHub Issue URL: {issue_url}[/bold red]")
        return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Invalid URL format.</error></source>'

    repo_owner = url_parts[3]
    repo_name = url_parts[4]
    issue_number = url_parts[-1]

    api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
    repo_url_for_content = f"https://github.com/{repo_owner}/{repo_name}"

    try:
        print(f"Fetching issue data for: {issue_url}")
        response = requests.get(api_base_url, headers=headers)
        response.raise_for_status()
        issue_data = response.json()

        # Start XML structure
        formatted_text_list = [f'<source type="github_issue" url="{escape_xml(issue_url)}">']
        formatted_text_list.append(f'<title>{escape_xml(issue_data.get("title", "N/A"))}</title>')
        formatted_text_list.append('<description>')
        formatted_text_list.append(issue_data.get('body', "") or "") # Append raw body, handle None
        formatted_text_list.append('</description>')
        details = (
             f"User: {issue_data.get('user', {}).get('login', 'N/A')}, "
             f"State: {issue_data.get('state', 'N/A')}, "
             f"Number: {issue_data.get('number', 'N/A')}"
         )
        formatted_text_list.append(f'<details>{escape_xml(details)}</details>')


        # Fetch and add comments
        comments_data = []
        comments_url = issue_data.get("comments_url")
        if comments_url:
            print("Fetching issue comments...")
            comments_response = requests.get(comments_url, headers=headers)
            if comments_response.ok:
                 comments_data = comments_response.json()
            else:
                 print(f"[bold yellow]Warning:[/bold yellow] Could not fetch issue comments: {comments_response.status_code}")


        if comments_data:
            formatted_text_list.append('\n<comments>')
            # Optional: Sort comments by creation date
            comments_data.sort(key=lambda c: c.get("created_at", ""))
            for comment in comments_data:
                author = comment.get('user', {}).get('login', 'N/A')
                body = comment.get('body', '') or "" # Handle None
                formatted_text_list.append(f'<comment author="{escape_xml(author)}">')
                formatted_text_list.append(body) # Append raw comment body
                formatted_text_list.append('</comment>')
            formatted_text_list.append('</comments>')

        # Add repository content (will include its own <source> tag)
        print(f"Fetching associated repository content from: {repo_url_for_content}")
        # Fetch default branch content for issues
        repo_content = process_github_repo(repo_url_for_content) # process_github_repo returns XML string

        formatted_text_list.append('\n<!-- Associated Repository Content -->') # XML Comment
        formatted_text_list.append(repo_content) # Append the XML output directly

        formatted_text_list.append('\n</source>') # Close main issue source tag

        print(f"Issue {issue_number} and repository content processed successfully.")
        return "\n".join(formatted_text_list)

    except requests.RequestException as e:
        print(f"[bold red]Error fetching GitHub issue data for {issue_url}: {e}[/bold red]")
        return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Failed to fetch issue data: {escape_xml(str(e))}</error></source>'
    except Exception as e: # Catch other potential errors
         print(f"[bold red]Unexpected error processing GitHub issue {issue_url}: {e}[/bold red]")
         return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Unexpected error: {escape_xml(str(e))}</error></source>'


def combine_xml_outputs(outputs):
    """
    Combines multiple XML outputs into one cohesive XML document
    under a <onefilellm_output> root tag.
    """
    if not outputs:
        return None
    
    # If only one output, wrap it in onefilellm_output for consistency
    # instead of returning it as-is
    
    # Create a wrapper for multiple sources
    combined = ['<onefilellm_output>']
    
    # Add each source
    for output in outputs:
        # Remove any XML declaration if present (rare but possible)
        output = re.sub(r'<\?xml[^>]+\?>', '', output).strip()
        combined.append(output)
    
    # Close the wrapper
    combined.append('</onefilellm_output>')
    
    return '\n'.join(combined)

async def process_input(input_path, args, progress=None, task=None):
    """
    Process a single input path and return the XML output.
    Extracted from main() for reuse with multiple inputs.
    """
    console = Console()
    urls_list_file = "processed_urls.txt"
    
    try:
        console.print(f"\n[bold bright_green]Processing:[/bold bright_green] [bold bright_yellow]{input_path}[/bold bright_yellow]\n")
        
        # Input type detection logic
        if "github.com" in input_path:
            if "/pull/" in input_path:
                result = process_github_pull_request(input_path)
            elif "/issues/" in input_path:
                result = process_github_issue(input_path)
            else: # Assume repository URL
                result = process_github_repo(input_path)
        elif urlparse(input_path).scheme in ["http", "https"]:
            if "youtube.com" in input_path or "youtu.be" in input_path:
                result = fetch_youtube_transcript(input_path)
            elif "arxiv.org/abs/" in input_path:
                result = process_arxiv_pdf(input_path)
            elif input_path.lower().endswith(('.pdf')): # Direct PDF link
                # Simplified: wrap direct PDF processing if needed, or treat as web crawl
                print("[bold yellow]Direct PDF URL detected - treating as single-page crawl.[/bold yellow]")
                crawl_result = crawl_and_extract_text(input_path, max_depth=0, include_pdfs=True, ignore_epubs=True)
                result = crawl_result['content']
                if crawl_result['processed_urls']:
                    with open(urls_list_file, 'w', encoding='utf-8') as urls_file:
                        urls_file.write('\n'.join(crawl_result['processed_urls']))
            elif input_path.lower().endswith(('.xls', '.xlsx')): # Direct Excel file link
                console.print(f"Processing Excel file from URL: {input_path}")
                try:
                    filename = os.path.basename(urlparse(input_path).path)
                    base_filename = os.path.splitext(filename)[0]
                    
                    # Get markdown tables for each sheet
                    result_parts = [f'<source type="web_excel" url="{escape_xml(input_path)}">']
                    
                    try:
                        markdown_tables = excel_to_markdown_from_url(input_path)
                        for sheet_name, markdown in markdown_tables.items():
                            virtual_name = f"{base_filename}_{sheet_name}.md"
                            result_parts.append(f'<file path="{escape_xml(virtual_name)}">')
                            result_parts.append(markdown)
                            result_parts.append('</file>')
                    except Exception as e:
                        result_parts.append(f'<e>Failed to process Excel file from URL: {escape_xml(str(e))}</e>')
                    
                    result_parts.append('</source>')
                    result = '\n'.join(result_parts)
                except Exception as e:
                    console.print(f"[bold red]Error processing Excel URL {input_path}: {e}[/bold red]")
                    result = f'<source type="web_excel" url="{escape_xml(input_path)}"><e>Failed to process Excel file: {escape_xml(str(e))}</e></source>'
            # Process URL directly if it ends with a recognized file extension
            elif any(input_path.lower().endswith(ext) for ext in [ext for ext in ['.txt', '.md', '.bat', '.cmd', '.html', '.htm', '.css', '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.rs', '.lua', '.pl', '.sh', '.bash', '.zsh', '.ps1', '.sql', '.groovy', '.dart', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.cfg', '.conf', '.properties', '.csv', '.tsv', '.proto', '.graphql', '.tf', '.tfvars', '.hcl'] if is_allowed_filetype(f"test{ext}")] if ext != '.pdf'):
                console.print(f"Processing direct file URL: {input_path}")
                file_content = _download_and_read_file(input_path)
                filename = os.path.basename(urlparse(input_path).path)
                result = (f'<source type="web_file" url="{escape_xml(input_path)}">\n'
                         f'<file path="{escape_xml(filename)}">\n'
                         f'{file_content}\n'
                         f'</file>\n'
                         f'</source>')
            else: # Assume general web URL for crawling
                # Use the new async DocCrawler
                result = await process_web_crawl(input_path, args, console, progress)
                # Note: The new crawler doesn't return processed_urls separately,
                # they're included in the XML output if needed
        # Basic check for DOI (starts with 10.) or PMID (all digits)
        elif (input_path.startswith("10.") and "/" in input_path) or input_path.isdigit():
            result = process_doi_or_pmid(input_path)
        elif os.path.isdir(input_path): # Check if it's a local directory
            result = process_local_folder(input_path)
        elif os.path.isfile(input_path): # Handle single local file
            if input_path.lower().endswith('.pdf'): # Case-insensitive check
                console.print(f"Processing single local PDF file: {input_path}") # Use console for consistency
                pdf_content_text = _process_pdf_content_from_path(input_path)
                # Structure for a single local PDF file
                result = (f'<source type="local_file" path="{escape_xml(input_path)}">\n'
                         f'<file path="{escape_xml(os.path.basename(input_path))}">\n' # Wrapping content in <file>
                         f'{pdf_content_text}\n' # Raw PDF text or error message
                         f'</file>\n'
                         f'</source>')
            elif input_path.lower().endswith(('.xls', '.xlsx')): # Case-insensitive check for Excel files
                console.print(f"Processing single local Excel file: {input_path}")
                try:
                    filename = os.path.basename(input_path)
                    base_filename = os.path.splitext(filename)[0]
                    
                    # Get markdown tables for each sheet
                    result_parts = [f'<source type="local_file" path="{escape_xml(input_path)}">']
                    
                    try:
                        markdown_tables = excel_to_markdown(input_path)
                        for sheet_name, markdown in markdown_tables.items():
                            virtual_name = f"{base_filename}_{sheet_name}.md"
                            result_parts.append(f'<file path="{escape_xml(virtual_name)}">')
                            result_parts.append(markdown)
                            result_parts.append('</file>')
                    except Exception as e:
                        result_parts.append(f'<e>Failed to process Excel file: {escape_xml(str(e))}</e>')
                    
                    result_parts.append('</source>')
                    result = '\n'.join(result_parts)
                except Exception as e:
                    console.print(f"[bold red]Error processing Excel file {input_path}: {e}[/bold red]")
                    result = f'<source type="local_file" path="{escape_xml(input_path)}"><e>Failed to process Excel file: {escape_xml(str(e))}</e></source>'
            else:
                # Existing logic for other single files
                console.print(f"Processing single local file: {input_path}") # Use console
                relative_path = os.path.basename(input_path)
                file_content = safe_file_read(input_path)
                result = (f'<source type="local_file" path="{escape_xml(input_path)}">\n'
                         f'<file path="{escape_xml(relative_path)}">\n'
                         f'{file_content}\n'
                         f'</file>\n'
                         f'</source>')
        else: # Input not recognized
            raise ValueError(f"Input path or URL type not recognized: {input_path}")
            
        return result
        
    except Exception as e:
        console.print(f"\n[bold red]Error processing {input_path}:[/bold red] {str(e)}")
        # Return an error-wrapped source instead of raising
        return f'<source type="error" path="{escape_xml(input_path)}">\n<e>Failed to process: {escape_xml(str(e))}</e>\n</source>'


def show_help_topics():
    """Display available help topics."""
    from rich.table import Table
    
    console = Console()
    
    table = Table(
        title="[bold bright_green]OneFileLLM Help Topics[/bold bright_green]",
        show_header=True,
        header_style="bold bright_cyan",
        border_style="bright_blue",
        title_style="bold bright_green"
    )
    
    table.add_column("Topic", style="bright_cyan", width=20)
    table.add_column("Description", style="white", width=60)
    
    topics = [
        ("basic", "Basic usage and input sources"),
        ("aliases", "Alias system for complex workflows"),
        ("crawling", "Advanced web crawling options"),
        ("pipelines", "Integration with 'llm' tool and automation"),
        ("examples", "Advanced usage examples and patterns"),
        ("config", "Configuration and environment setup"),
    ]
    
    for topic, desc in topics:
        table.add_row(f"--help-topic {topic}", desc)
    
    console.print()
    console.print(table)
    console.print()
    console.print("[bright_green]Usage:[/bright_green] [white]python onefilellm.py --help-topic <topic>[/white]")
    console.print("[bright_green]Example:[/bright_green] [white]python onefilellm.py --help-topic pipelines[/white]")
    console.print()


def show_help_basic():
    """Show basic usage help."""
    console = Console()
    
    content = Text()
    content.append("ONEFILELLM\n", style="bold bright_green")
    content.append("Content aggregator for large language models\n\n", style="bright_cyan")
    
    content.append("📁 LOCAL FILE SOURCES\n", style="bold bright_cyan")
    content.append("  # Single files with automatic format detection\n", style="white")
    content.append("  python onefilellm.py research_paper.pdf\n", style="bright_green")
    content.append("  python onefilellm.py config.yaml\n", style="bright_green")
    content.append("  python onefilellm.py notebook.ipynb\n", style="bright_green")
    content.append("  python onefilellm.py data.csv\n", style="bright_green")
    content.append("  python onefilellm.py --format json response.txt\n\n", style="bright_green")
    
    content.append("  # Multiple files and directories\n", style="white")
    content.append("  python onefilellm.py src/ docs/ README.md\n", style="bright_green")
    content.append("  python onefilellm.py *.py requirements.txt\n", style="bright_green")
    content.append("  python onefilellm.py project/src/ project/tests/ config.yaml\n\n", style="bright_green")
    
    content.append("🐙 GITHUB SOURCES\n", style="bold bright_cyan")
    content.append("  # Repositories with different access levels\n", style="white")
    content.append("  python onefilellm.py https://github.com/microsoft/vscode\n", style="bright_green")
    content.append("  python onefilellm.py https://github.com/openai/whisper/tree/main/whisper\n", style="bright_green")
    content.append("  python onefilellm.py https://github.com/user/private-repo  # Requires GITHUB_TOKEN\n\n", style="bright_green")
    
    content.append("  # Pull requests and issues\n", style="white")
    content.append("  python onefilellm.py https://github.com/microsoft/vscode/pull/12345\n", style="bright_green")
    content.append("  python onefilellm.py https://github.com/microsoft/vscode/issues/67890\n", style="bright_green")
    content.append("  python onefilellm.py https://github.com/kubernetes/kubernetes/pulls\n\n", style="bright_green")
    
    content.append("🌐 WEB DOCUMENTATION\n", style="bold bright_cyan")
    content.append("  # Single pages with readability extraction\n", style="white")
    content.append("  python onefilellm.py https://docs.python.org/3/tutorial/\n", style="bright_green")
    content.append("  python onefilellm.py https://react.dev/learn/thinking-in-react\n", style="bright_green")
    content.append("  python onefilellm.py https://kubernetes.io/docs/concepts/overview/\n\n", style="bright_green")
    
    content.append("  # Multi-page crawling (see --help-topic crawling)\n", style="white")
    content.append("  python onefilellm.py https://docs.djangoproject.com/ --crawl-max-depth 3\n", style="bright_green")
    content.append("  python onefilellm.py https://fastapi.tiangolo.com/ --crawl-max-pages 100\n\n", style="bright_green")
    
    content.append("📺 MULTIMEDIA SOURCES\n", style="bold bright_cyan")
    content.append("  # YouTube video transcripts\n", style="white")
    content.append("  python onefilellm.py https://www.youtube.com/watch?v=dQw4w9WgXcQ\n", style="bright_green")
    content.append("  python onefilellm.py https://youtu.be/kCc8FmEb1nY\n", style="bright_green")
    content.append("  python onefilellm.py https://www.youtube.com/playlist?list=PLRqwX-V7Uu6ZF9C0YMKuns9sLDzK6zoiV\n\n", style="bright_green")
    
    content.append("📚 ACADEMIC SOURCES\n", style="bold bright_cyan")
    content.append("  # ArXiv papers by URL or ID\n", style="white")
    content.append("  python onefilellm.py https://arxiv.org/abs/2103.00020\n", style="bright_green")
    content.append("  python onefilellm.py arxiv:2103.00020\n", style="bright_green")
    content.append("  python onefilellm.py \"Attention Is All You Need\"\n\n", style="bright_green")
    
    content.append("  # DOI and PMID references\n", style="white")
    content.append("  python onefilellm.py 10.1038/s41586-021-03819-2\n", style="bright_green")
    content.append("  python onefilellm.py PMID:35177773\n", style="bright_green")
    content.append("  python onefilellm.py doi:10.1126/science.abq1158\n\n", style="bright_green")
    
    content.append("⌨️  INPUT STREAMS\n", style="bold bright_cyan")
    content.append("  # From clipboard\n", style="white")
    content.append("  python onefilellm.py --clipboard\n", style="bright_green")
    content.append("  python onefilellm.py --clipboard --format markdown\n\n", style="bright_green")
    
    content.append("  # From stdin pipe\n", style="white")
    content.append("  cat large_dataset.json | python onefilellm.py -\n", style="bright_green")
    content.append("  curl -s https://api.github.com/repos/microsoft/vscode | python onefilellm.py - --format json\n", style="bright_green")
    content.append("  echo 'Quick note content' | python onefilellm.py -\n\n", style="bright_green")
    
    content.append("📊 OUTPUT FEATURES\n", style="bold bright_cyan")
    content.append("  ✓ Structured XML with semantic <source> tags\n", style="white")
    content.append("  ✓ Content preserved unescaped for LLM readability\n", style="white")
    content.append("  ✓ Automatic token counting (tiktoken)\n", style="white")
    content.append("  ✓ Clipboard copy for immediate LLM use\n", style="white")
    content.append("  ✓ Progress tracking with Rich console\n", style="white")
    content.append("  ✓ Async processing for multiple sources\n", style="white")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_help_aliases():
    """Show alias system help."""
    console = Console()
    
    content = Text()
    content.append("ALIAS SYSTEM 2.0\n", style="bold bright_green")
    content.append("JSON-based shortcuts for massive multi-source workflows\n\n", style="bright_cyan")
    
    content.append("🎯 BASIC ALIAS CREATION\n", style="bold bright_cyan")
    content.append("  # Simple single-source aliases\n", style="white")
    content.append("  python onefilellm.py --alias-add mcp \"https://github.com/anthropics/mcp\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add docs \"https://docs.python.org/3/\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add notes \"project_notes.md\"\n\n", style="bright_green")
    
    content.append("  # Multi-source aliases (space-separated)\n", style="white")
    content.append("  python onefilellm.py --alias-add react-stack \\\n", style="bright_green")
    content.append("    \"https://github.com/facebook/react https://reactjs.org/docs/ https://github.com/vercel/next.js\"\n\n", style="bright_green")
    
    content.append("🔍 DYNAMIC PLACEHOLDERS\n", style="bold bright_cyan")
    content.append("  # Create searchable aliases with {} tokens\n", style="white")
    content.append("  python onefilellm.py --alias-add gh-search \"https://github.com/search?q={}\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add arxiv-search \"https://arxiv.org/search/?query={}\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add gh-user \"https://github.com/{}\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add docs-search \"https://docs.python.org/3/search.html?q={}\"\n\n", style="bright_green")
    
    content.append("  # Use placeholders dynamically\n", style="white")
    content.append("  python onefilellm.py gh-search \"machine learning transformers\"\n", style="bright_green")
    content.append("  python onefilellm.py arxiv-search \"attention mechanisms\"\n", style="bright_green")
    content.append("  python onefilellm.py gh-user \"microsoft\"\n", style="bright_green")
    content.append("  python onefilellm.py docs-search \"asyncio\"\n\n", style="bright_green")
    
    content.append("🏗️ COMPREHENSIVE ECOSYSTEM ALIASES\n", style="bold bright_cyan")
    content.append("  # Modern web development stack (300K+ tokens)\n", style="white")
    content.append("  python onefilellm.py --alias-add modern-web \\\n", style="bright_green")
    content.append("    \"https://github.com/facebook/react https://github.com/vercel/next.js https://github.com/tailwindlabs/tailwindcss https://github.com/prisma/prisma https://reactjs.org/docs/ https://nextjs.org/docs https://tailwindcss.com/docs https://www.prisma.io/docs\"\n\n", style="bright_green")
    
    content.append("  # AI/ML research ecosystem (600K+ tokens)\n", style="white")
    content.append("  python onefilellm.py --alias-add ai-research \\\n", style="bright_green")
    content.append("    \"arxiv:1706.03762 arxiv:2005.14165 10.1038/s41586-021-03819-2 https://github.com/huggingface/transformers https://github.com/openai/whisper https://github.com/pytorch/pytorch https://huggingface.co/docs https://pytorch.org/docs https://openai.com/research\"\n\n", style="bright_green")
    
    content.append("  # Cloud native ecosystem (900K+ tokens)\n", style="white")
    content.append("  python onefilellm.py --alias-add k8s-ecosystem \\\n", style="bright_green")
    content.append("    \"https://github.com/kubernetes/kubernetes https://github.com/kubernetes/enhancements https://kubernetes.io/docs/ https://github.com/istio/istio https://github.com/prometheus/prometheus https://github.com/envoyproxy/envoy https://istio.io/latest/docs/ https://prometheus.io/docs/\"\n\n", style="bright_green")
    
    content.append("  # Security research and tools (400K+ tokens)\n", style="white")
    content.append("  python onefilellm.py --alias-add security-stack \\\n", style="bright_green")
    content.append("    \"https://github.com/OWASP/Top10 https://github.com/aquasecurity/trivy https://github.com/falcosecurity/falco https://owasp.org/www-project-top-ten/ https://aquasec.com/trivy/ https://falco.org/docs/\"\n\n", style="bright_green")
    
    content.append("📊 SPECIALIZED DOMAIN ALIASES\n", style="bold bright_cyan")
    content.append("  # Data science and analytics\n", style="white")
    content.append("  python onefilellm.py --alias-add data-science \\\n", style="bright_green")
    content.append("    \"https://github.com/pandas-dev/pandas https://github.com/numpy/numpy https://github.com/scikit-learn/scikit-learn https://pandas.pydata.org/docs/ https://numpy.org/doc/ https://scikit-learn.org/stable/\"\n\n", style="bright_green")
    
    content.append("  # DevOps and infrastructure\n", style="white")
    content.append("  python onefilellm.py --alias-add devops-tools \\\n", style="bright_green")
    content.append("    \"https://github.com/hashicorp/terraform https://github.com/ansible/ansible https://github.com/docker/docker https://terraform.io/docs https://docs.ansible.com/ https://docs.docker.com/\"\n\n", style="bright_green")
    
    content.append("  # Blockchain and crypto research\n", style="white")
    content.append("  python onefilellm.py --alias-add crypto-research \\\n", style="bright_green")
    content.append("    \"https://github.com/ethereum/ethereum-org-website https://github.com/bitcoin/bitcoin https://ethereum.org/en/developers/docs/ https://bitcoin.org/en/developer-documentation\"\n\n", style="bright_green")
    
    content.append("🧬 ACADEMIC AND RESEARCH ALIASES\n", style="bold bright_cyan")
    content.append("  # NeurIPS 2024 conference collection\n", style="white")
    content.append("  python onefilellm.py --alias-add neurips-2024 \\\n", style="bright_green")
    content.append("    \"https://neurips.cc/virtual/2024 arxiv:2312.01234 arxiv:2311.05678 PMID:38123456\"\n\n", style="bright_green")
    
    content.append("  # Protein folding research\n", style="white")
    content.append("  python onefilellm.py --alias-add protein-folding \\\n", style="bright_green")
    content.append("    \"https://github.com/deepmind/alphafold https://github.com/deepmind/alphafold3 10.1038/s41586-021-03819-2 https://alphafold.ebi.ac.uk/help https://colabfold.mmseqs.com/\"\n\n", style="bright_green")
    
    content.append("  # Climate science data\n", style="white")
    content.append("  python onefilellm.py --alias-add climate-research \\\n", style="bright_green")
    content.append("    \"https://github.com/NCAR/cesm https://www.ipcc.ch/reports/ https://climate.nasa.gov/evidence/ doi:10.1038/s41467-021-24487-w\"\n\n", style="bright_green")
    
    content.append("💼 BUSINESS AND INDUSTRY ALIASES\n", style="bold bright_cyan")
    content.append("  # Fintech and banking APIs\n", style="white")
    content.append("  python onefilellm.py --alias-add fintech-apis \\\n", style="bright_green")
    content.append("    \"https://github.com/stripe/stripe-python https://docs.stripe.com/api https://developer.paypal.com/docs/api/ https://plaid.com/docs/\"\n\n", style="bright_green")
    
    content.append("  # E-commerce platforms\n", style="white")
    content.append("  python onefilellm.py --alias-add ecommerce-stack \\\n", style="bright_green")
    content.append("    \"https://github.com/shopify/shopify-api-js https://shopify.dev/docs https://woocommerce.com/documentation/ https://magento.com/technical-resources\"\n\n", style="bright_green")
    
    content.append("🔗 COMPLEX ALIAS COMBINATIONS\n", style="bold bright_cyan")
    content.append("  # Massive context aggregation (1.2M+ tokens)\n", style="white")
    content.append("  python onefilellm.py modern-web ai-research k8s-ecosystem \\\n", style="bright_green")
    content.append("    https://github.com/microsoft/semantic-kernel \\\n", style="bright_green")
    content.append("    https://github.com/vercel/ai \\\n", style="bright_green")
    content.append("    conference_notes_2024.pdf \\\n", style="bright_green")
    content.append("    local_research_projects/\n\n", style="bright_green")
    
    content.append("  # Multi-domain research synthesis\n", style="white")
    content.append("  python onefilellm.py ai-research protein-folding climate-research \\\n", style="bright_green")
    content.append("    \"https://www.youtube.com/watch?v=kCc8FmEb1nY\" \\\n", style="bright_green")
    content.append("    interdisciplinary_notes.md\n\n", style="bright_green")
    
    content.append("⚙️  ALIAS MANAGEMENT COMMANDS\n", style="bold bright_cyan")
    content.append("  python onefilellm.py --alias-list              # Show all aliases\n", style="bright_green")
    content.append("  python onefilellm.py --alias-list-core         # Show core aliases only\n", style="bright_green")
    content.append("  python onefilellm.py --alias-remove old-alias  # Remove user alias\n", style="bright_green")
    content.append("  cat ~/.onefilellm_aliases/aliases.json         # View raw JSON\n\n", style="bright_green")
    
    content.append("🚀 ADVANCED PIPELINE WORKFLOWS\n", style="bold bright_cyan")
    content.append("  # Research analysis pipeline\n", style="white")
    content.append("  python onefilellm.py ai-research security-stack | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract security implications of AI systems\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Identify vulnerabilities and mitigation strategies\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate comprehensive security framework\"\n\n", style="bright_green")
    
    content.append("  # Market research synthesis\n", style="white")
    content.append("  python onefilellm.py fintech-apis ecommerce-stack modern-web | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Analyze market trends and technical integration patterns\" | \\\n", style="bright_green")
    content.append("    tee market_analysis.md | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate business strategy recommendations\"\n", style="bright_green")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_help_crawling():
    """Show web crawling help."""
    console = Console()
    
    content = Text()
    content.append("ADVANCED WEB CRAWLING\n", style="bold bright_green")
    content.append("Async crawler with readability extraction and smart filtering\n\n", style="bright_cyan")
    
    content.append("🌐 DOCUMENTATION CRAWLING\n", style="bold bright_cyan")
    content.append("  # Python documentation (comprehensive)\n", style="white")
    content.append("  python onefilellm.py https://docs.python.org/3/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 4 --crawl-max-pages 800 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(tutorial|library|reference)/\" \\\n", style="bright_green")
    content.append("    --crawl-exclude-pattern \".*/(whatsnew|faq)/\" \\\n", style="bright_green")
    content.append("    --crawl-delay 0.2\n\n", style="bright_green")
    
    content.append("  # Django documentation (targeted sections)\n", style="white")
    content.append("  python onefilellm.py https://docs.djangoproject.com/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 3 --crawl-max-pages 300 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(topics|ref|howto)/\" \\\n", style="bright_green")
    content.append("    --crawl-restrict-path --crawl-include-code\n\n", style="bright_green")
    
    content.append("  # React documentation (complete ecosystem)\n", style="white")
    content.append("  python onefilellm.py https://react.dev/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 5 --crawl-max-pages 200 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(learn|reference|community)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-code --crawl-concurrency 2\n\n", style="bright_green")
    
    content.append("🏢 ENTERPRISE API DOCUMENTATION\n", style="bold bright_cyan")
    content.append("  # AWS documentation (specific services)\n", style="white")
    content.append("  python onefilellm.py https://docs.aws.amazon.com/ec2/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 3 --crawl-max-pages 500 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(UserGuide|APIReference)/\" \\\n", style="bright_green")
    content.append("    --crawl-exclude-pattern \".*/(troubleshooting|release-notes)/\" \\\n", style="bright_green")
    content.append("    --crawl-respect-robots --crawl-delay 0.5\n\n", style="bright_green")
    
    content.append("  # Kubernetes documentation (comprehensive)\n", style="white")
    content.append("  python onefilellm.py https://kubernetes.io/docs/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 4 --crawl-max-pages 600 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(concepts|tasks|tutorials)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-code --crawl-include-pdfs\n\n", style="bright_green")
    
    content.append("  # Stripe API documentation\n", style="white")
    content.append("  python onefilellm.py https://docs.stripe.com/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 3 --crawl-max-pages 400 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(api|payments|connect)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-code --crawl-delay 0.3\n\n", style="bright_green")
    
    content.append("🎓 ACADEMIC AND RESEARCH SITES\n", style="bold bright_cyan")
    content.append("  # arXiv category exploration\n", style="white")
    content.append("  python onefilellm.py https://arxiv.org/list/cs.AI/recent \\\n", style="bright_green")
    content.append("    --crawl-max-depth 2 --crawl-max-pages 100 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(abs|pdf)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-pdfs --crawl-delay 1.0\n\n", style="bright_green")
    
    content.append("  # University research pages\n", style="white")
    content.append("  python onefilellm.py https://ai.stanford.edu/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 3 --crawl-max-pages 150 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(research|publications|projects)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-pdfs --crawl-respect-robots\n\n", style="bright_green")
    
    content.append("📰 NEWS AND BLOG SITES\n", style="bold bright_cyan")
    content.append("  # Hacker News discussions\n", style="white")
    content.append("  python onefilellm.py https://news.ycombinator.com/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 2 --crawl-max-pages 50 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/item\\?id=[0-9]+\" \\\n", style="bright_green")
    content.append("    --crawl-delay 2.0 --crawl-respect-robots\n\n", style="bright_green")
    
    content.append("  # Medium publications\n", style="white")
    content.append("  python onefilellm.py https://towardsdatascience.com/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 2 --crawl-max-pages 100 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/@[^/]+/[^/]+\" \\\n", style="bright_green")
    content.append("    --crawl-exclude-pattern \".*/tag/\" --crawl-delay 1.0\n\n", style="bright_green")
    
    content.append("🛠️ ADVANCED FILTERING PATTERNS\n", style="bold bright_cyan")
    content.append("  # Include only specific file types\n", style="white")
    content.append("  --crawl-include-pattern \".*\\.(html|md|rst|txt)$\"\n", style="bright_green")
    content.append("  --crawl-exclude-pattern \".*\\.(css|js|png|jpg|gif)$\"\n\n", style="bright_green")
    
    content.append("  # Focus on documentation sections\n", style="white")
    content.append("  --crawl-include-pattern \".*/(docs?|api|guide|tutorial|manual)/\"\n", style="bright_green")
    content.append("  --crawl-exclude-pattern \".*/(blog|news|press|about)/\"\n\n", style="bright_green")
    
    content.append("  # Version-specific documentation\n", style="white")
    content.append("  --crawl-include-pattern \".*/v[0-9]+\\.[0-9]+/\"\n", style="bright_green")
    content.append("  --crawl-exclude-pattern \".*/v[0-1]\\.[0-9]+/\"  # Exclude old versions\n\n", style="bright_green")
    
    content.append("⚡ PERFORMANCE OPTIMIZATION\n", style="bold bright_cyan")
    content.append("  # High-speed crawling (use carefully)\n", style="white")
    content.append("  --crawl-concurrency 8 --crawl-delay 0.1 --crawl-timeout 10\n\n", style="bright_green")
    
    content.append("  # Respectful crawling (recommended)\n", style="white")
    content.append("  --crawl-concurrency 2 --crawl-delay 1.0 --crawl-respect-robots\n\n", style="bright_green")
    
    content.append("  # Large-scale documentation (enterprise)\n", style="white")
    content.append("  --crawl-max-pages 2000 --crawl-max-depth 6 --crawl-concurrency 4\n\n", style="bright_green")
    
    content.append("🎯 CONTENT EXTRACTION OPTIONS\n", style="bold bright_cyan")
    content.append("  --crawl-include-code         Extract code blocks and snippets\n", style="white")
    content.append("  --crawl-no-include-code      Skip code extraction\n", style="white")
    content.append("  --crawl-include-images       Include image URLs and alt text\n", style="white")
    content.append("  --crawl-include-pdfs         Download and process PDF files\n", style="white")
    content.append("  --crawl-extract-headings     Extract heading structure\n", style="white")
    content.append("  --crawl-clean-html           Apply readability extraction\n", style="white")
    content.append("  --crawl-no-strip-js          Keep JavaScript content\n", style="white")
    content.append("  --crawl-no-strip-css         Keep CSS content\n\n", style="white")
    
    content.append("🔒 COMPLIANCE AND ETHICS\n", style="bold bright_cyan")
    content.append("  # Always respect robots.txt for public sites\n", style="white")
    content.append("  --crawl-respect-robots\n\n", style="bright_green")
    
    content.append("  # Restrict to specific path hierarchies\n", style="white")
    content.append("  --crawl-restrict-path        # Stay under initial URL path\n\n", style="bright_green")
    
    content.append("  # Use appropriate delays for server load\n", style="white")
    content.append("  --crawl-delay 0.5            # 500ms between requests (recommended)\n", style="bright_green")
    content.append("  --crawl-delay 2.0            # 2s for busy/slow sites\n\n", style="bright_green")
    
    content.append("📊 REAL-WORLD CRAWLING EXAMPLES\n", style="bold bright_cyan")
    content.append("  # Complete FastAPI ecosystem\n", style="white")
    content.append("  python onefilellm.py https://fastapi.tiangolo.com/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 4 --crawl-max-pages 400 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(tutorial|advanced|deployment)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-code --crawl-concurrency 3\n\n", style="bright_green")
    
    content.append("  # Comprehensive TensorFlow documentation\n", style="white")
    content.append("  python onefilellm.py https://www.tensorflow.org/guide/ \\\n", style="bright_green")
    content.append("    --crawl-max-depth 3 --crawl-max-pages 600 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/(guide|tutorials|api_docs)/\" \\\n", style="bright_green")
    content.append("    --crawl-include-code --crawl-delay 0.3\n\n", style="bright_green")
    
    content.append("  # GitHub organization exploration\n", style="white")
    content.append("  python onefilellm.py https://github.com/microsoft \\\n", style="bright_green")
    content.append("    --crawl-max-depth 2 --crawl-max-pages 200 \\\n", style="bright_green")
    content.append("    --crawl-include-pattern \".*/microsoft/[^/]+/?$\" \\\n", style="bright_green")
    content.append("    --crawl-delay 0.5\n", style="bright_green")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_help_pipelines():
    """Show pipeline integration help."""
    console = Console()
    
    content = Text()
    content.append("ADVANCED PIPELINE INTEGRATION\n", style="bold bright_green")
    content.append("Complex workflows with Simon Willison's 'llm' tool and automation\n\n", style="bright_cyan")
    
    content.append("🔬 RESEARCH ANALYSIS PIPELINES\n", style="bold bright_cyan")
    content.append("  # Multi-stage academic paper analysis\n", style="white")
    content.append("  python onefilellm.py ai-research protein-folding | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract key methodologies and datasets\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Identify experimental approaches and results\" | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Compare methodologies across papers\" | \\\n", style="bright_green")
    content.append("    tee methodology_analysis.md | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate novel research directions\" > research_proposals.md\n\n", style="bright_green")
    
    content.append("  # Comprehensive literature review synthesis\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    \"arxiv:2103.00020\" \"arxiv:2005.14165\" \"10.1038/s41586-021-03819-2\" \\\n", style="bright_green")
    content.append("    https://github.com/huggingface/transformers \\\n", style="bright_green")
    content.append("    https://openai.com/research | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract citations and build reference network\" | \\\n", style="bright_green")
    content.append("    python -c \"import re; [print(match.group()) for match in re.finditer(r'\\d{4}\\.\\d{5}|10\\.\\d+/[^\\s]+', open('/dev/stdin').read())]\" | \\\n", style="bright_green")
    content.append("    sort | uniq | head -20 | \\\n", style="bright_green")
    content.append("    xargs -I {} python onefilellm.py {} | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Synthesize comprehensive literature review\"\n\n", style="bright_green")
    
    content.append("💼 BUSINESS INTELLIGENCE WORKFLOWS\n", style="bold bright_cyan")
    content.append("  # Competitive analysis automation\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://github.com/competitor1/product \\\n", style="bright_green")
    content.append("    https://github.com/competitor2/platform \\\n", style="bright_green")
    content.append("    https://competitor1.com/docs/ \\\n", style="bright_green")
    content.append("    https://competitor2.com/api/ | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract feature lists and capabilities\" | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Compare features and identify gaps\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Assess technical implementation approaches\" | \\\n", style="bright_green")
    content.append("    tee competitive_analysis.md | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate strategic recommendations\" > strategy.md\n\n", style="bright_green")
    
    content.append("  # Market trend analysis from multiple sources\n", style="white")
    content.append("  python onefilellm.py fintech-apis ecommerce-stack \\\n", style="bright_green")
    content.append("    https://news.ycombinator.com/item?id=38709319 \\\n", style="bright_green")
    content.append("    https://techcrunch.com/category/fintech/ \\\n", style="bright_green")
    content.append("    market_reports_q4_2024/ | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract market trends and growth metrics\" | \\\n", style="bright_green")
    content.append("    grep -E '(growth|revenue|adoption|market share)' | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Identify emerging patterns and opportunities\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate investment thesis and market forecast\"\n\n", style="bright_green")
    
    content.append("🔒 SECURITY RESEARCH AUTOMATION\n", style="bold bright_cyan")
    content.append("  # Vulnerability assessment pipeline\n", style="white")
    content.append("  python onefilellm.py security-stack \\\n", style="bright_green")
    content.append("    https://github.com/target-org/main-product \\\n", style="bright_green")
    content.append("    https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=target-product | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract security patterns and potential vulnerabilities\" | \\\n", style="bright_green")
    content.append("    grep -E '(CRITICAL|HIGH|authentication|authorization|injection|xss)' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Categorize vulnerabilities by severity and type\" | \\\n", style="bright_green")
    content.append("    awk '/CRITICAL/ {print \"🚨 \" $0} /HIGH/ {print \"⚠️ \" $0} /MEDIUM/ {print \"📝 \" $0}' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate comprehensive security assessment report\"\n\n", style="bright_green")
    
    content.append("  # Threat intelligence aggregation\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://github.com/MITRE/cti \\\n", style="bright_green")
    content.append("    https://attack.mitre.org/ \\\n", style="bright_green")
    content.append("    https://www.cisa.gov/known-exploited-vulnerabilities-catalog | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract IOCs and attack patterns\" | \\\n", style="bright_green")
    content.append("    grep -E '(CVE-[0-9]{4}-[0-9]+|T[0-9]{4}|malware|threat actor)' | \\\n", style="bright_green")
    content.append("    sort | uniq -c | sort -nr | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Analyze threat landscape and attack trends\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate threat intelligence briefing\"\n\n", style="bright_green")
    
    content.append("🏗️ TECHNICAL ARCHITECTURE ANALYSIS\n", style="bold bright_cyan")
    content.append("  # Multi-framework comparison pipeline\n", style="white")
    content.append("  python onefilellm.py modern-web k8s-ecosystem data-science | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract architectural patterns and design decisions\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Identify scalability and performance considerations\" | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Compare architectural tradeoffs and best practices\" | \\\n", style="bright_green")
    content.append("    tee architecture_analysis.md | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Design optimal technology stack recommendations\"\n\n", style="bright_green")
    
    content.append("  # API ecosystem integration analysis\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://docs.stripe.com/api \\\n", style="bright_green")
    content.append("    https://developer.paypal.com/docs/api/ \\\n", style="bright_green")
    content.append("    https://plaid.com/docs/api/ \\\n", style="bright_green")
    content.append("    https://docs.aws.amazon.com/lambda/ | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract API endpoints, authentication, and data models\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Identify integration patterns and compatibility\" | \\\n", style="bright_green")
    content.append("    python -c \"import re; print('\\n'.join(set(re.findall(r'POST|GET|PUT|DELETE\\s+/[^\\s]+', open('/dev/stdin').read()))))\" | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Design unified API integration strategy\"\n\n", style="bright_green")
    
    content.append("📊 DATA SCIENCE AND ML WORKFLOWS\n", style="bold bright_cyan")
    content.append("  # Model architecture research synthesis\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    \"arxiv:1706.03762\" \"arxiv:2005.14165\" \"arxiv:2103.00020\" \\\n", style="bright_green")
    content.append("    https://github.com/pytorch/pytorch \\\n", style="bright_green")
    content.append("    https://github.com/tensorflow/tensorflow | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract model architectures and hyperparameters\" | \\\n", style="bright_green")
    content.append("    grep -E '(layers|attention|embedding|learning_rate|batch_size)' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Compare model performance and efficiency\" | \\\n", style="bright_green")
    content.append("    python -c \"import re; [print(f'{match.group()}: {len(re.findall(match.group(), open(\"/dev/stdin\").read()))}') for match in set(re.finditer(r'\\b\\d+[BMK]?\\b', open('/dev/stdin').read()))]\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Design optimized model architecture recommendations\"\n\n", style="bright_green")
    
    content.append("  # Dataset and benchmark analysis\n", style="white")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://huggingface.co/datasets \\\n", style="bright_green")
    content.append("    https://paperswithcode.com/datasets \\\n", style="bright_green")
    content.append("    https://github.com/google-research/bert | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract dataset characteristics and benchmark results\" | \\\n", style="bright_green")
    content.append("    grep -E '(accuracy|f1|rouge|bleu|perplexity|size|samples)' | \\\n", style="bright_green")
    content.append("    awk '{print $0 | \"sort -nr\"}' | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Identify optimal datasets and evaluation metrics\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate ML experiment design recommendations\"\n\n", style="bright_green")
    
    content.append("🌍 CONTENT LOCALIZATION AND ANALYSIS\n", style="bold bright_cyan")
    content.append("  # Multi-language documentation analysis\n", style="white")
    content.append("  for lang in en es fr de zh; do \\\n", style="bright_green")
    content.append("    python onefilellm.py https://docs.example.com/$lang/ | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract content structure and completeness for $lang\"; \\\n", style="bright_green")
    content.append("  done | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Compare documentation coverage across languages\" | \\\n", style="bright_green")
    content.append("    llm -m gpt-4o \"Identify translation gaps and content strategy\"\n\n", style="bright_green")
    
    content.append("🔄 AUTOMATED CONTENT MONITORING\n", style="bold bright_cyan")
    content.append("  # Daily research update pipeline (cron job)\n", style="white")
    content.append("  #!/bin/bash\n", style="dim")
    content.append("  # Add to crontab: 0 9 * * * /path/to/daily_research.sh\n", style="dim")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://arxiv.org/list/cs.AI/recent \\\n", style="bright_green")
    content.append("    https://arxiv.org/list/cs.LG/recent | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract today's most significant papers\" | \\\n", style="bright_green")
    content.append("    grep -E '(breakthrough|novel|state-of-the-art|significant)' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Summarize key developments\" | \\\n", style="bright_green")
    content.append("    mail -s \"Daily AI Research Brief $(date)\" researcher@company.com\n\n", style="bright_green")
    
    content.append("📈 ADVANCED DATA PROCESSING\n", style="bold bright_cyan")
    content.append("  # Real-time sentiment analysis pipeline\n", style="white")
    content.append("  python onefilellm.py --clipboard | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract sentiment indicators and emotional markers\" | \\\n", style="bright_green")
    content.append("    sed 's/POSITIVE/😊/g; s/NEGATIVE/😞/g; s/NEUTRAL/😐/g' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Quantify sentiment scores and confidence levels\" | \\\n", style="bright_green")
    content.append("    python -c \"import json; data=input(); print(json.dumps({'sentiment': data, 'timestamp': __import__('datetime').datetime.now().isoformat()}))\" | \\\n", style="bright_green")
    content.append("    jq -r '.sentiment + \" (\" + .timestamp + \")\"' | \\\n", style="bright_green")
    content.append("    tee -a sentiment_log.jsonl\n\n", style="bright_green")
    
    content.append("  # Complex JSON data transformation\n", style="white")
    content.append("  curl -s https://api.github.com/repos/microsoft/vscode/issues | \\\n", style="bright_green")
    content.append("    python onefilellm.py - --format json | \\\n", style="bright_green")
    content.append("    llm -m claude-3-haiku \"Extract issue patterns and categorize by priority\" | \\\n", style="bright_green")
    content.append("    jq -r '.[] | select(.state == \"open\") | {title: .title, labels: [.labels[].name], created: .created_at}' | \\\n", style="bright_green")
    content.append("    llm -m claude-3-sonnet \"Analyze issue trends and suggest improvements\" | \\\n", style="bright_green")
    content.append("    python -c \"import sys,json; [print(json.dumps(line)) for line in sys.stdin if 'priority' in line.lower()]\" | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Generate project health assessment\"\n", style="bright_green")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_help_examples():
    """Show advanced examples help."""
    console = Console()
    
    content = Text()
    content.append("MASSIVE CONTEXT EXAMPLES\n", style="bold bright_green")
    content.append("Real-world workflows approaching 1M+ token contexts\n\n", style="bright_cyan")
    
    content.append("COMPLETE ECOSYSTEM ANALYSIS\n", style="bold bright_cyan")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://github.com/kubernetes/kubernetes \\\n", style="bright_green")
    content.append("    https://github.com/kubernetes/enhancements \\\n", style="bright_green")
    content.append("    https://github.com/kubernetes/community \\\n", style="bright_green")
    content.append("    https://kubernetes.io/docs/ \\\n", style="bright_green")
    content.append("    https://github.com/kubernetes/website \\\n", style="bright_green")
    content.append("    https://github.com/cncf/toc \\\n", style="bright_green")
    content.append("    \"cloud native computing papers\" \\\n", style="bright_green")
    content.append("    local_k8s_notes.md\n\n", style="bright_green")
    
    content.append("MULTI-ALIAS RESEARCH WORKFLOWS\n", style="bold bright_cyan")
    content.append("  # Create specialized aliases\n", style="white")
    content.append("  python onefilellm.py --alias-add ai-papers \\\n", style="bright_green")
    content.append("    \"10.1706.03762,arxiv:2005.14165,10.1038/s41586-021-03819-2\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add ai-codebases \\\n", style="bright_green")
    content.append("    \"https://github.com/openai/whisper,https://github.com/huggingface/transformers\"\n", style="bright_green")
    content.append("  python onefilellm.py --alias-add ai-docs \\\n", style="bright_green")
    content.append("    \"https://huggingface.co/docs,https://openai.com/research\"\n\n", style="bright_green")
    
    content.append("  # Combine all aliases with live sources\n", style="white")
    content.append("  python onefilellm.py ai-papers ai-codebases ai-docs \\\n", style="bright_green")
    content.append("    https://github.com/microsoft/semantic-kernel \\\n", style="bright_green")
    content.append("    https://www.youtube.com/watch?v=kCc8FmEb1nY \\\n", style="bright_green")
    content.append("    latest_ai_conference_notes.pdf \\\n", style="bright_green")
    content.append("    https://news.ycombinator.com/item?id=38709319\n\n", style="bright_green")
    
    content.append("COMPREHENSIVE TECHNOLOGY STACKS\n", style="bold bright_cyan")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    https://github.com/facebook/react \\\n", style="bright_green")
    content.append("    https://github.com/vercel/next.js \\\n", style="bright_green")
    content.append("    https://github.com/tailwindlabs/tailwindcss \\\n", style="bright_green")
    content.append("    https://github.com/prisma/prisma \\\n", style="bright_green")
    content.append("    https://github.com/trpc/trpc \\\n", style="bright_green")
    content.append("    https://github.com/vercel/swr \\\n", style="bright_green")
    content.append("    https://reactjs.org/docs/ \\\n", style="bright_green")
    content.append("    https://nextjs.org/docs \\\n", style="bright_green")
    content.append("    https://tailwindcss.com/docs \\\n", style="bright_green")
    content.append("    \"modern web development survey 2024\"\n\n", style="bright_green")
    
    content.append("ACADEMIC RESEARCH COMPILATION\n", style="bold bright_cyan")
    content.append("  python onefilellm.py \\\n", style="bright_green")
    content.append("    \"10.1038/s41586-021-03819-2\" \\\n", style="bright_green")
    content.append("    \"10.1126/science.abq1158\" \\\n", style="bright_green")
    content.append("    \"arxiv:2203.15556\" \\\n", style="bright_green")
    content.append("    \"PMID:35177773\" \\\n", style="bright_green")
    content.append("    https://github.com/deepmind/alphafold \\\n", style="bright_green")
    content.append("    https://github.com/deepmind/alphafold3 \\\n", style="bright_green")
    content.append("    https://alphafold.ebi.ac.uk/help \\\n", style="bright_green")
    content.append("    https://www.youtube.com/watch?v=gg7WjuFs8F4 \\\n", style="bright_green")
    content.append("    https://colabfold.mmseqs.com/ \\\n", style="bright_green")
    content.append("    protein_folding_conference_2024.pdf\n\n", style="bright_green")
    
    content.append("MIXED SOURCE WORKFLOWS\n", style="bold bright_cyan")
    content.append("  # From clipboard + live sources + aliases\n", style="white")
    content.append("  python onefilellm.py --clipboard --format markdown \\\n", style="bright_green")
    content.append("    ml-research-alias \\\n", style="bright_green")
    content.append("    https://github.com/openai/chatgpt-retrieval-plugin \\\n", style="bright_green")
    content.append("    local_experiments/ \\\n", style="bright_green")
    content.append("    conference_notes.txt | \\\n", style="bright_green")
    content.append("    llm -m claude-3-opus \"Synthesize research directions\"\n", style="bright_green")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_help_config():
    """Show configuration help.""" 
    console = Console()
    
    content = Text()
    content.append("CONFIGURATION\n", style="bold bright_green")
    content.append("Environment setup and customization\n\n", style="bright_cyan")
    
    content.append("ENVIRONMENT VARIABLES\n", style="bold bright_cyan")
    content.append("  export GITHUB_TOKEN=\"your_token\"    # Private repos\n", style="bright_green")
    content.append("  export CRAWL_MAX_DEPTH=5            # Default depth\n", style="bright_green")
    content.append("  export CRAWL_MAX_PAGES=1000         # Page limit\n", style="bright_green")
    content.append("  export CRAWL_USER_AGENT=\"Bot/1.0\"    # User agent\n\n", style="bright_green")
    
    content.append("DOTENV FILE\n", style="bold bright_cyan")
    content.append("  Create .env file in project directory:\n", style="white")
    content.append("    GITHUB_TOKEN=your_token_here\n", style="dim")
    content.append("    CRAWL_DELAY=0.1\n", style="dim")
    content.append("    CRAWL_CONCURRENCY=3\n\n", style="dim")
    
    content.append("COMPRESSION\n", style="bold bright_cyan")
    content.append("  pip install nltk\n", style="bright_green")
    content.append("  # Set ENABLE_COMPRESSION_AND_NLTK=True in code\n\n", style="white")
    
    content.append("ALIAS STORAGE\n", style="bold bright_cyan")
    content.append("  Aliases stored in: ~/.onefilellm_aliases/aliases.json\n", style="white")
    content.append("  JSON format with user aliases overriding core aliases\n", style="white")
    content.append("  Supports placeholder substitution with {} tokens\n", style="white")
    
    console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))


def show_interactive_help(topic=None):
    """Show interactive help system."""
    if topic is None:
        show_help_topics()
    elif topic == "basic":
        show_help_basic()
    elif topic == "aliases":
        show_help_aliases()
    elif topic == "crawling":
        show_help_crawling()
    elif topic == "pipelines":
        show_help_pipelines()
    elif topic == "examples":
        show_help_examples()
    elif topic == "config":
        show_help_config()
    else:
        console = Console()
        console.print(f"[red]Unknown help topic: {topic}[/red]")
        console.print()
        show_help_topics()


def create_argument_parser():
    """Create and return the argument parser with all CLI options."""
    parser = argparse.ArgumentParser(
        description="OneFileLLM - Content Aggregator for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
QUICK START EXAMPLES:

LOCAL FILES AND DIRECTORIES:
  python onefilellm.py research_paper.pdf config.yaml src/
  python onefilellm.py *.py requirements.txt docs/ README.md
  python onefilellm.py notebook.ipynb --format json
  python onefilellm.py large_dataset.csv logs/ --format text

GITHUB REPOSITORIES AND ISSUES:
  python onefilellm.py https://github.com/microsoft/vscode
  python onefilellm.py https://github.com/openai/whisper/tree/main/whisper
  python onefilellm.py https://github.com/microsoft/vscode/pull/12345
  python onefilellm.py https://github.com/kubernetes/kubernetes/issues

WEB DOCUMENTATION AND APIS:
  python onefilellm.py https://docs.python.org/3/tutorial/
  python onefilellm.py https://react.dev/learn/thinking-in-react
  python onefilellm.py https://docs.stripe.com/api
  python onefilellm.py https://kubernetes.io/docs/concepts/

MULTIMEDIA AND ACADEMIC SOURCES:
  python onefilellm.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
  python onefilellm.py https://arxiv.org/abs/2103.00020
  python onefilellm.py arxiv:1706.03762 PMID:35177773
  python onefilellm.py doi:10.1038/s41586-021-03819-2

INPUT STREAMS:
  python onefilellm.py --clipboard --format markdown
  cat large_dataset.json | python onefilellm.py - --format json
  curl -s https://api.github.com/repos/microsoft/vscode | python onefilellm.py -
  echo 'Quick analysis task' | python onefilellm.py -

ALIAS SYSTEM 2.0:
  # Create simple and complex aliases
  python onefilellm.py --alias-add mcp "https://github.com/anthropics/mcp"
  python onefilellm.py --alias-add modern-web \\
    "https://github.com/facebook/react https://reactjs.org/docs/ https://github.com/vercel/next.js"
  
  # Dynamic placeholders for search and parameterization
  python onefilellm.py --alias-add gh-search "https://github.com/search?q={}"
  python onefilellm.py --alias-add gh-user "https://github.com/{}"
  python onefilellm.py --alias-add arxiv-search "https://arxiv.org/search/?query={}"
  
  # Use placeholders dynamically
  python onefilellm.py gh-search "machine learning transformers"
  python onefilellm.py gh-user "microsoft"
  python onefilellm.py arxiv-search "attention mechanisms"
  
  # Complex ecosystem aliases (300K-900K+ tokens)
  python onefilellm.py --alias-add ai-research \\
    "arxiv:1706.03762 https://github.com/huggingface/transformers https://pytorch.org/docs"
  python onefilellm.py --alias-add k8s-ecosystem \\
    "https://github.com/kubernetes/kubernetes https://kubernetes.io/docs/ https://github.com/istio/istio"
  
  # Combine multiple aliases with live sources
  python onefilellm.py ai-research k8s-ecosystem modern-web \\
    conference_notes.pdf local_experiments/

MASSIVE CONTEXT AGGREGATION (800K-1.2M+ tokens):
  # Complete technology ecosystem analysis
  python onefilellm.py \\
    https://github.com/kubernetes/kubernetes \\
    https://github.com/kubernetes/enhancements \\
    https://kubernetes.io/docs/ \\
    https://github.com/istio/istio \\
    https://github.com/prometheus/prometheus \\
    https://istio.io/latest/docs/ \\
    https://prometheus.io/docs/ \\
    https://www.youtube.com/watch?v=kCc8FmEb1nY \\
    cloud_native_conference_2024.pdf

  # Academic research synthesis
  python onefilellm.py \\
    "arxiv:2103.00020" "arxiv:2005.14165" "10.1038/s41586-021-03819-2" \\
    https://github.com/deepmind/alphafold \\
    https://github.com/huggingface/transformers \\
    https://alphafold.ebi.ac.uk/help \\
    https://huggingface.co/docs \\
    protein_folding_breakthrough_2024.pdf

ADVANCED WEB CRAWLING:
  # Comprehensive documentation sites
  python onefilellm.py https://docs.python.org/3/ \\
    --crawl-max-depth 4 --crawl-max-pages 800 \\
    --crawl-include-pattern ".*/(tutorial|library|reference)/" \\
    --crawl-exclude-pattern ".*/(whatsnew|faq)/"
  
  # Enterprise API documentation
  python onefilellm.py https://docs.aws.amazon.com/ec2/ \\
    --crawl-max-depth 3 --crawl-max-pages 500 \\
    --crawl-include-pattern ".*/(UserGuide|APIReference)/" \\
    --crawl-respect-robots --crawl-delay 0.5
  
  # Academic and research sites
  python onefilellm.py https://arxiv.org/list/cs.AI/recent \\
    --crawl-max-depth 2 --crawl-max-pages 100 \\
    --crawl-include-pattern ".*/(abs|pdf)/" \\
    --crawl-include-pdfs --crawl-delay 1.0

INTEGRATION PIPELINES WITH 'llm' TOOL:
  # Multi-stage research analysis
  python onefilellm.py ai-research protein-folding | \\
    llm -m claude-3-haiku "Extract key methodologies and datasets" | \\
    llm -m claude-3-sonnet "Identify experimental approaches" | \\
    llm -m gpt-4o "Compare methodologies across papers" | \\
    llm -m claude-3-opus "Generate novel research directions"
  
  # Competitive analysis automation
  python onefilellm.py \\
    https://github.com/competitor1/product \\
    https://competitor1.com/docs/ \\
    https://competitor2.com/api/ | \\
    llm -m claude-3-haiku "Extract features and capabilities" | \\
    llm -m gpt-4o "Compare and identify gaps" | \\
    llm -m claude-3-opus "Generate strategic recommendations"
  
  # Security research automation
  python onefilellm.py security-stack \\
    https://github.com/target-org/main-product | \\
    llm -m claude-3-haiku "Extract security patterns" | \\
    llm -m claude-3-sonnet "Categorize vulnerabilities" | \\
    llm -m claude-3-opus "Generate security assessment"
  
  # Real-time sentiment analysis
  python onefilellm.py --clipboard | \\
    llm -m claude-3-haiku "Extract sentiment indicators" | \\
    llm -m claude-3-sonnet "Quantify sentiment scores" | \\
    jq -r '.sentiment + " (" + .timestamp + ")"'

BUSINESS AND ENTERPRISE WORKFLOWS:
  # Market research and competitive intelligence
  python onefilellm.py fintech-apis ecommerce-stack \\
    https://news.ycombinator.com/item?id=38709319 \\
    market_reports_q4_2024/ | \\
    llm -m claude-3-haiku "Extract market trends" | \\
    llm -m gpt-4o "Identify opportunities" | \\
    llm -m claude-3-opus "Generate investment thesis"
  
  # Technical architecture analysis
  python onefilellm.py modern-web k8s-ecosystem data-science | \\
    llm -m claude-3-haiku "Extract architectural patterns" | \\
    llm -m claude-3-sonnet "Identify scalability considerations" | \\
    llm -m claude-3-opus "Design optimal tech stack"

ACADEMIC AND RESEARCH WORKFLOWS:
  # Literature review with citation analysis
  python onefilellm.py \\
    "arxiv:2103.00020" "arxiv:2005.14165" "10.1038/s41586-021-03819-2" | \\
    llm -m claude-3-haiku "Extract citations and build reference network" | \\
    grep -E "\\d{4}\\.\\d{5}|10\\.\\d+/" | sort | uniq | head -20 | \\
    xargs -I {} python onefilellm.py {} | \\
    llm -m claude-3-opus "Synthesize comprehensive literature review"
  
  # Multi-domain research synthesis
  python onefilellm.py ai-research protein-folding climate-research \\
    https://www.youtube.com/watch?v=kCc8FmEb1nY \\
    interdisciplinary_notes.md | \\
    llm -m claude-3-opus "Identify cross-domain insights and novel approaches"

AUTOMATION AND MONITORING:
  # Daily research monitoring (cron job)
  0 9 * * * python onefilellm.py \\
    https://arxiv.org/list/cs.AI/recent \\
    https://arxiv.org/list/cs.LG/recent | \\
    llm -m claude-3-haiku "Extract significant papers" | \\
    llm -m claude-3-sonnet "Summarize key developments" | \\
    mail -s "Daily AI Research Brief" researcher@company.com

FORMAT AND INPUT OPTIONS:
  python onefilellm.py data.txt --format markdown
  python onefilellm.py config.yaml --format yaml  
  python onefilellm.py response.json --format json
  python onefilellm.py notebook.ipynb --format text
  python onefilellm.py api_docs.html --format html

ALIAS MANAGEMENT:
  python onefilellm.py --alias-list              # Show all aliases
  python onefilellm.py --alias-list-core         # Show core aliases only
  python onefilellm.py --alias-remove old-alias  # Remove user alias
  cat ~/.onefilellm_aliases/aliases.json         # View raw JSON

COMPREHENSIVE HELP SYSTEM:
  python onefilellm.py --help-topic basic      # Input sources and basic usage
  python onefilellm.py --help-topic aliases    # Alias system with real examples
  python onefilellm.py --help-topic crawling   # Web crawler patterns and ethics
  python onefilellm.py --help-topic pipelines  # 'llm' tool integration workflows
  python onefilellm.py --help-topic examples   # Advanced usage patterns
  python onefilellm.py --help-topic config     # Environment and configuration

REAL-WORLD USE CASES:
  - Technology due diligence and competitive analysis
  - Academic literature review and research synthesis
  - Security vulnerability assessment and threat intelligence
  - API integration planning and architecture analysis
  - Market research and business intelligence
  - Multi-language documentation analysis
  - Content aggregation for LLM fine-tuning datasets
  - Automated research monitoring and alerting
"""
    )
    
    # Positional arguments
    parser.add_argument('inputs', nargs='*', help='Input paths, URLs, or aliases to process')
    
    # Input source options
    parser.add_argument('-c', '--clipboard', action='store_true',
                        help='Process text from clipboard')
    parser.add_argument('-f', '--format', choices=['text', 'markdown', 'json', 'html', 'yaml', 'doculing', 'markitdown'],
                        help='Override format detection for text input')
    
    # Alias management
    alias_group = parser.add_argument_group('Alias Management')
    alias_group.add_argument('--alias-add', nargs='+', metavar=('NAME', 'COMMAND_STRING'),
                             help='Add or update a user-defined alias. Multiple arguments after NAME will be joined as COMMAND_STRING.')
    alias_group.add_argument('--alias-remove', metavar='NAME',
                             help='Remove a user-defined alias.')
    alias_group.add_argument('--alias-list', action='store_true',
                             help='List all effective aliases (user-defined aliases override core aliases).')
    alias_group.add_argument('--alias-list-core', action='store_true',
                             help='List only pre-shipped (core) aliases.')
    
    # Web crawler options
    crawler_group = parser.add_argument_group('Web Crawler Options')
    crawler_group.add_argument('--crawl-max-depth', type=int, default=3,
                               help='Maximum crawl depth (default: 3)')
    crawler_group.add_argument('--crawl-max-pages', type=int, default=1000,
                               help='Maximum pages to crawl (default: 1000)')
    crawler_group.add_argument('--crawl-user-agent', default='OneFileLLMCrawler/1.1',
                               help='User agent for web requests (default: OneFileLLMCrawler/1.1)')
    crawler_group.add_argument('--crawl-delay', type=float, default=0.25,
                               help='Delay between requests in seconds (default: 0.25)')
    crawler_group.add_argument('--crawl-include-pattern',
                               help='Regex pattern for URLs to include')
    crawler_group.add_argument('--crawl-exclude-pattern',
                               help='Regex pattern for URLs to exclude')
    crawler_group.add_argument('--crawl-timeout', type=int, default=20,
                               help='Request timeout in seconds (default: 20)')
    crawler_group.add_argument('--crawl-include-images', action='store_true',
                               help='Include image URLs in output')
    crawler_group.add_argument('--crawl-no-include-code', action='store_false', dest='crawl_include_code',
                               default=True, help='Exclude code blocks from output')
    crawler_group.add_argument('--crawl-no-extract-headings', action='store_false', dest='crawl_extract_headings',
                               default=True, help='Exclude heading extraction')
    crawler_group.add_argument('--crawl-follow-links', action='store_true',
                               help='Follow links to external domains')
    crawler_group.add_argument('--crawl-no-clean-html', action='store_false', dest='crawl_clean_html',
                               default=True, help='Disable readability cleaning')
    crawler_group.add_argument('--crawl-no-strip-js', action='store_false', dest='crawl_strip_js',
                               default=True, help='Keep JavaScript code')
    crawler_group.add_argument('--crawl-no-strip-css', action='store_false', dest='crawl_strip_css',
                               default=True, help='Keep CSS styles')
    crawler_group.add_argument('--crawl-no-strip-comments', action='store_false', dest='crawl_strip_comments',
                               default=True, help='Keep HTML comments')
    crawler_group.add_argument('--crawl-respect-robots', action='store_true', dest='crawl_respect_robots',
                               default=False, help='Respect robots.txt (default: ignore for backward compatibility)')
    crawler_group.add_argument('--crawl-concurrency', type=int, default=3,
                               help='Number of concurrent requests (default: 3)')
    crawler_group.add_argument('--crawl-restrict-path', action='store_true',
                               help='Restrict crawl to paths under start URL')
    crawler_group.add_argument('--crawl-no-include-pdfs', action='store_false', dest='crawl_include_pdfs',
                               default=True, help='Skip PDF files')
    crawler_group.add_argument('--crawl-no-ignore-epubs', action='store_false', dest='crawl_ignore_epubs',
                               default=True, help='Include EPUB files')
    
    # Help options
    parser.add_argument('--help-topic', nargs='?', const='', metavar='TOPIC',
                        help='Show help for specific topic (basic, aliases, crawling, pipelines, examples, config)')
    
    return parser


async def main():
    console = Console()
    # Ensure Rich console is used for all prints for consistency
    # For example, replace print() with console.print()

    # Initialize AliasManager
    alias_manager = AliasManager(console, CORE_ALIASES, USER_ALIASES_PATH)
    alias_manager.load_aliases() # Load aliases early

    # --- Alias Expansion (before full argparse) ---
    original_argv = sys.argv.copy()
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        potential_alias_name = sys.argv[1]
        command_str = alias_manager.get_command(potential_alias_name)
        if command_str:
            console.print(f"[dim]Alias '{potential_alias_name}' expands to: \"{command_str}\"[/dim]")
            
            # Placeholder logic
            # User command: onefilellm alias_name [val_for_placeholder] [remaining_args...]
            # sys.argv: [script_name, alias_name, val_for_placeholder?, remaining_args... ]
            
            placeholder_value_provided = len(original_argv) > 2
            placeholder_value = original_argv[2] if placeholder_value_provided else ""
            
            # Check if "{}" placeholder exists anywhere in the command string
            has_placeholder = "{}" in command_str
            consumed_placeholder_arg = False

            if has_placeholder:
                # Replace placeholder with the provided value (or empty string if none provided)
                expanded_command_str = command_str.replace("{}", placeholder_value)
                if placeholder_value_provided:
                    consumed_placeholder_arg = True
                # Determine where the rest of the original arguments start
                remaining_args_start_index = 3 if consumed_placeholder_arg else 2
            else:
                # No placeholder in alias command, use as-is
                expanded_command_str = command_str
                remaining_args_start_index = 2 # Args after alias name are appended

            # Split the expanded command string into parts
            expanded_base_parts = shlex.split(expanded_command_str)
            
            sys.argv = [original_argv[0]] + expanded_base_parts + original_argv[remaining_args_start_index:]
            console.print(f"[dim]Executing: onefilellm {' '.join(sys.argv[1:])}[/dim]")
    # --- End Alias Expansion ---

    parser = create_argument_parser()
    args = parser.parse_args(sys.argv[1:]) # Use the potentially modified sys.argv
    
    # --- Handle help options ---
    if hasattr(args, 'help_topic') and args.help_topic is not None:
        if args.help_topic == '':
            show_interactive_help()
        else:
            show_interactive_help(args.help_topic)
        return
    
    # --- Handle Alias Management CLI Commands ---
    if args.alias_add:
        if len(args.alias_add) < 2:
            console.print("[bold red]Error:[/bold red] --alias-add requires at least two arguments: NAME and COMMAND_STRING")
            return
        alias_name = args.alias_add[0]
        command_string = ' '.join(args.alias_add[1:])
        alias_manager.add_or_update_alias(alias_name, command_string)
        return # Exit after managing alias
    if args.alias_remove:
        alias_manager.remove_alias(args.alias_remove)
        return # Exit
    if args.alias_list:
        console.print("\n[bold]Effective Aliases (User overrides Core):[/bold]")
        console.print(alias_manager.list_aliases_formatted(list_user=True, list_core=True))
        return # Exit
    if args.alias_list_core:
        console.print("\n[bold]Core Aliases:[/bold]")
        console.print(alias_manager.list_aliases_formatted(list_user=False, list_core=True))
        return # Exit
    
    # --- Handle stream input modes ---
    is_stream_input_mode = False
    stream_source_dict = {}
    stream_content_to_process = None
    user_format_override = args.format
    
    # Check for stdin input ('-' in inputs)
    if '-' in args.inputs:
        is_stream_input_mode = True
        stream_source_dict = {'type': 'stdin'}
        # Remove '-' from inputs list
        args.inputs = [inp for inp in args.inputs if inp != '-']
    
    # Check for clipboard input
    elif args.clipboard:
        is_stream_input_mode = True
        stream_source_dict = {'type': 'clipboard'}

    # Process stream input if specified

    if is_stream_input_mode:
        if stream_source_dict['type'] == 'stdin':
            if not sys.stdin.isatty():
                console.print("[bright_blue]Reading from standard input...[/bright_blue]")
                stream_content_to_process = read_from_stdin()
                if stream_content_to_process is None or not stream_content_to_process.strip():
                    console.print("[bold red]Error: No input received from standard input or input is empty.[/bold red]")
                    return
            else:
                console.print("[bold red]Error: '-' specified but no data piped to stdin.[/bold red]")
                console.print("To use standard input, pipe data like: `your_command | python onefilellm.py -`")
                return
        elif stream_source_dict['type'] == 'clipboard':
            console.print("[bright_blue]Reading from clipboard...[/bright_blue]")
            stream_content_to_process = read_from_clipboard()
            if stream_content_to_process is None or not stream_content_to_process.strip():
                console.print("[bold red]Error: Clipboard is empty, does not contain text, or could not be accessed.[/bold red]")
                if sys.platform.startswith('linux'):
                    console.print("[yellow]On Linux, you might need to install 'xclip' or 'xsel': `sudo apt install xclip`[/yellow]")
                return
    
    # --- Main Processing Logic Dispatch ---
    if is_stream_input_mode:
        # We are in stream processing mode
        if stream_content_to_process: # Ensure we have content
            xml_output_for_stream = process_text_stream(
                stream_content_to_process, 
                stream_source_dict, 
                console, # Pass the console object
                user_format_override
            )

            if xml_output_for_stream:
                # For a single stream input, it forms the entire <onefilellm_output>
                final_combined_output = f"<onefilellm_output>\n{xml_output_for_stream}\n</onefilellm_output>"

                # Use existing output mechanisms
                output_file = "output.xml" 
                processed_file = "compressed_output.txt" 

                console.print(f"\nWriting output to {output_file}...")
                with open(output_file, "w", encoding="utf-8") as file:
                    file.write(final_combined_output)
                console.print("Output written successfully.")

                uncompressed_token_count = get_token_count(final_combined_output)
                estimated_uncompressed_token_count = round(uncompressed_token_count * TOKEN_ESTIMATE_MULTIPLIER)
                console.print(f"\n[bright_green]Content Token Count (tiktoken):[/bright_green] [bold bright_cyan]{uncompressed_token_count:,}[/bold bright_cyan]")
                console.print(f"[bright_green]Estimated Model Token Count (incl. overhead):[/bright_green] [bold bright_yellow]{estimated_uncompressed_token_count:,}[/bold bright_yellow]")

                if ENABLE_COMPRESSION_AND_NLTK:
                    # ... (existing compression logic using output_file and processed_file) ...
                    console.print("\n[bright_magenta]Compression and NLTK processing enabled.[/bright_magenta]")
                    print(f"Preprocessing text and writing compressed output to {processed_file}...")
                    preprocess_text(output_file, processed_file) # Pass correct output_file
                    print("Compressed file written.")
                    compressed_text_content = safe_file_read(processed_file)
                    compressed_token_count = get_token_count(compressed_text_content)
                    estimated_compressed_token_count = round(compressed_token_count * TOKEN_ESTIMATE_MULTIPLIER)
                    console.print(f"[bright_green]Compressed Content Token Count (tiktoken):[/bright_green] [bold bright_cyan]{compressed_token_count:,}[/bold bright_cyan]")
                    console.print(f"[bright_green]Compressed Estimated Model Token Count:[/bright_green] [bold bright_yellow]{estimated_compressed_token_count:,}[/bold bright_yellow]")

                try:
                    pyperclip.copy(final_combined_output)
                    console.print(f"\n[bright_white]The contents of [bold bright_blue]{output_file}[/bold bright_blue] have been copied to the clipboard.[/bright_white]")
                except Exception as clip_err:
                    console.print(f"\n[bold yellow]Warning:[/bold yellow] Could not copy to clipboard: {clip_err}")
            else:
                console.print("[bold red]Error: Text stream processing failed to generate output.[/bold red]")
        # else: stream_content_to_process was None or empty, error already printed.
        return # Exit after stream processing

    # --- ELSE: Fall through to existing file/URL/alias processing logic ---

    # Updated intro text to reflect XML output
    intro_text = Text("\nProcesses Inputs and Wraps Content in XML:\n", style="dodger_blue1")
    input_types = [
        ("• Local folder path", "bright_white"),
        ("• GitHub repository URL", "bright_white"),
        ("• GitHub pull request URL (PR + Repo)", "bright_white"),
        ("• GitHub issue URL (Issue + Repo)", "bright_white"),
        ("• Documentation URL (Web Crawl)", "bright_white"),
        ("• YouTube video URL (Transcript)", "bright_white"),
        ("• ArXiv Paper URL (PDF Text)", "bright_white"),
        ("• DOI or PMID (via Sci-Hub, best effort)", "bright_white"),
        ("• Text from stdin (e.g., `cat file.txt | onefilellm -`)", "light_sky_blue1"), # New
        ("• Text from clipboard (e.g., `onefilellm --clipboard`)", "light_sky_blue1"), # New
    ]

    for input_type, color in input_types:
        intro_text.append(f"\n{input_type}", style=color)
    intro_text.append("\n\nOutput is saved to file and copied to clipboard.", style="dim")
    intro_text.append("\nContent within XML tags remains unescaped for readability.", style="dim")
    intro_text.append("\nMultiple inputs can be provided as command line arguments.", style="bright_green")

    intro_panel = Panel(
        intro_text,
        expand=False,
        border_style="bold",
        title="[bright_white]onefilellm - Content Aggregator[/bright_white]",
        title_align="center",
        padding=(1, 1),
    )
    console.print(intro_panel)

    # --- Determine Input Paths ---
    # Note: Aliases have already been expanded before argument parsing
    final_input_sources = []
    if args.inputs:
        final_input_sources.extend(args.inputs)
    
    if not final_input_sources and not is_stream_input_mode:
        # No inputs provided - show intro panel and prompt for input
        user_input_string = Prompt.ask("\n[bold dodger_blue1]Enter the path, URL, or alias[/bold dodger_blue1]", console=console).strip()
        if user_input_string:
            # This is tricky: if user types an alias here, it hasn't gone through expansion.
            # For simplicity in this step, assume direct input here, or re-run expansion logic, which is complex.
            # Simplest: The interactive prompt does not support alias expansion itself for now.
            # Or, the alias expansion logic could be refactored into a function to be called here too.
            # For now, treat as direct input:
            final_input_sources.append(user_input_string)
    
    # For minimal changes later, assign to input_paths
    input_paths = final_input_sources
    # --- End Determine Input Paths ---

    if not input_paths:
        console.print("[yellow]No valid input sources provided. Exiting.[/yellow]")
        return

    # Define output filenames
    output_file = "output.xml" # Changed extension to reflect content
    processed_file = "compressed_output.txt" # Keep as txt for compressed
    
    # List to collect individual outputs
    outputs = []

    with Progress(
        TextColumn("[bold bright_blue]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TextColumn("{task.completed}/{task.total} sources"),
        "•",
        TimeRemainingColumn(),
        console=console,
        transient=False,
        refresh_per_second=2,  # Reduce refresh rate to minimize conflicts
        disable=False,
        expand=True
    ) as progress:

        # Make the task determinate using the number of inputs
        task = progress.add_task("[bright_blue]Processing inputs...", total=len(input_paths))

        try:
            # Process each input path
            for input_path in input_paths:
                result = await process_input(input_path, args, progress, task)
                if result:
                    outputs.append(result)
                    console.print(f"[green]Successfully processed: {input_path}[/green]")
                else:
                    console.print(f"[yellow]No output generated for: {input_path}[/yellow]")
                
                # Advance the progress bar after each item is processed
                progress.update(task, advance=1)
            
            # Combine all outputs into one final output
            if not outputs:
                raise RuntimeError("No inputs were successfully processed.")
                
            final_output = combine_xml_outputs(outputs)

            # --- Output Generation ---
            if final_output is None:
                 raise RuntimeError("Processing failed to produce any output.")

            # Write the main (uncompressed) XML output
            print(f"\nWriting output to {output_file}...")
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(final_output)
            print("Output written successfully.")

            # --- NEW: Enhanced Summary ---
            final_output_size_bytes = len(final_output.encode('utf-8'))
            final_output_size_kb = final_output_size_bytes / 1024
            console.print(f"\n[bold bright_blue]Summary:[/bold bright_blue]")
            console.print(f"  - [cyan]Sources Processed:[/cyan] [bold white]{len(outputs)}[/bold white]")
            console.print(f"  - [cyan]Final Output Size:[/cyan] [bold white]{final_output_size_kb:,.2f} KB[/bold white]")
            # --- END NEW ---

            # Get token count for the main output (strips XML tags)
            uncompressed_token_count = get_token_count(final_output)
            estimated_uncompressed_token_count = round(uncompressed_token_count * TOKEN_ESTIMATE_MULTIPLIER)
            console.print(f"\n[bright_green]Content Token Count (tiktoken):[/bright_green] [bold bright_cyan]{uncompressed_token_count:,}[/bold bright_cyan]")
            console.print(f"[bright_green]Estimated Model Token Count (incl. overhead):[/bright_green] [bold bright_yellow]{estimated_uncompressed_token_count:,}[/bold bright_yellow]")

            # --- Conditional Compression Block ---
            if ENABLE_COMPRESSION_AND_NLTK:
                console.print("\n[bright_magenta]Compression and NLTK processing enabled.[/bright_magenta]")
                print(f"Preprocessing text and writing compressed output to {processed_file}...")
                # Process the text (input is the XML file, output is compressed txt)
                preprocess_text(output_file, processed_file)
                print("Compressed file written.")

                # Get token count for the compressed file (should be plain text)
                compressed_text = safe_file_read(processed_file)
                compressed_token_count = get_token_count(compressed_text) # Pass compressed text directly
                estimated_compressed_token_count = round(compressed_token_count * TOKEN_ESTIMATE_MULTIPLIER)
                console.print(f"[bright_green]Compressed Content Token Count (tiktoken):[/bright_green] [bold bright_cyan]{compressed_token_count:,}[/bold bright_cyan]")
                console.print(f"[bright_green]Compressed Estimated Model Token Count:[/bright_green] [bold bright_yellow]{estimated_compressed_token_count:,}[/bold bright_yellow]")
                console.print(f"\n[bold bright_blue]{output_file}[/bold bright_blue] (main XML) and [bold bright_yellow]{processed_file}[/bold bright_yellow] (compressed text) created.")
            else:
                 console.print(f"\n[bold bright_blue]{output_file}[/bold bright_blue] (main XML) has been created.")
            # --- End Conditional Compression Block ---


            # Copy the main XML output to clipboard
            try:
                 pyperclip.copy(final_output)
                 console.print(f"\n[bright_white]The contents of [bold bright_blue]{output_file}[/bold bright_blue] have been copied to the clipboard.[/bright_white]")
            except Exception as clip_err: # Catch potential pyperclip errors
                 console.print(f"\n[bold yellow]Warning:[/bold yellow] Could not copy to clipboard: {clip_err}")


        except Exception as e:
            console.print(f"\n[bold red]An error occurred during processing:[/bold red]")
            console.print_exception(show_locals=False) # Print traceback
            # Optionally write the partial output if it exists
            if outputs:
                 try:
                     error_filename = "error_output.xml"
                     partial_output = combine_xml_outputs(outputs)
                     with open(error_filename, "w", encoding="utf-8") as err_file:
                         err_file.write(partial_output)
                     console.print(f"[yellow]Partial output written to {error_filename}[/yellow]")
                 except Exception as write_err:
                     console.print(f"[red]Could not write partial output: {write_err}[/red]")

        finally:
             progress.stop_task(task)
             progress.refresh() # Ensure progress bar clears


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    asyncio.run(main())
