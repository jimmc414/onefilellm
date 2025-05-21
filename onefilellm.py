import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from PyPDF2 import PdfReader 
import os
import sys
import json
import tiktoken
import nltk 
from nltk.corpus import stopwords 
import re
import nbformat
from nbconvert import PythonExporter
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import pyperclip
from pathlib import Path
import io 
import html 

from rich import print 
from rich.console import Console 
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
import xml.etree.ElementTree as ET 
import pandas as pd
from typing import Union, List, Dict, Any 

try:
    import yaml
except ImportError:
    yaml = None
    print("[Warning] PyYAML module not found. YAML format detection/parsing will be limited.", file=sys.stderr)

ENABLE_COMPRESSION_AND_NLTK = False
EXCLUDED_DIRS = ["dist", "node_modules", ".git", "__pycache__"]
ALIAS_DIR_NAME = ".onefilellm_aliases"
ALIAS_DIR = Path.home() / ALIAS_DIR_NAME

def ensure_alias_dir_exists():
    ALIAS_DIR.mkdir(parents=True, exist_ok=True)

def safe_file_read(filepath, fallback_encoding='latin1'):
    try:
        with open(filepath, "r", encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding=fallback_encoding) as file:
            return file.read()

def read_from_clipboard() -> str | None:
    try:
        clipboard_content = pyperclip.paste()
        return clipboard_content if clipboard_content and clipboard_content.strip() else None
    except pyperclip.PyperclipException as e:
        print(f"[DEBUG] PyperclipException in read_from_clipboard: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[DEBUG] Unexpected error in read_from_clipboard: {e}", file=sys.stderr)
        return None

def read_from_stdin() -> str | None:
    if sys.stdin.isatty():
        return None
    try:
        stdin_content = sys.stdin.read()
        return stdin_content if stdin_content and stdin_content.strip() else None
    except Exception as e:
        print(f"[DEBUG] Error reading from stdin: {e}", file=sys.stderr)
        return None

def detect_text_format(text_sample: str) -> str:
    if not text_sample or not text_sample.strip(): return "text"
    sample = text_sample[:2000].strip()
    try:
        if (sample.startswith('{') and sample.endswith('}')) or \
           (sample.startswith('[') and sample.endswith(']')):
            json.loads(text_sample)
            return "json"
    except json.JSONDecodeError: pass
    if 'yaml' in sys.modules and yaml is not None:
        try:
            if ":" in sample and "\n" in sample:
                yaml.safe_load(text_sample)
                return "yaml"
        except (yaml.YAMLError, AttributeError): pass
    if re.search(r"<[^>]+>", sample) and \
       (re.search(r"<html[^>]*>", sample, re.IGNORECASE) or \
        re.search(r"<body[^>]*>", sample, re.IGNORECASE) or \
        re.search(r"<div[^>]*>", sample, re.IGNORECASE) or \
        re.search(r"<p[^>]*>", sample, re.IGNORECASE)):
        return "html"
    if re.search(r"^(#\s|\#{2,6}\s)", sample, re.MULTILINE) or \
       re.search(r"^(\*\s|-\s|\+\s|\d+\.\s)", sample, re.MULTILINE) or \
       re.search(r"\[.+?\]\(.+?\)", sample) or \
       re.search(r"(\*\*|__).+?(\*\*|__)", sample) or \
       re.search(r"(\*|_).+?(\*|_)", sample):
        return "markdown"
    return "text"

def parse_as_plaintext(text_content: str) -> str: return text_content
def parse_as_markdown(text_content: str) -> str: return text_content
def parse_as_json(text_content: str) -> str:
    json.loads(text_content)
    return text_content
def parse_as_html(text_content: str) -> str:
    soup = BeautifulSoup(text_content, 'html.parser')
    for element in soup(['script', 'style', 'head', 'title', 'meta', '[document]', 'nav', 'footer', 'aside']):
        element.decompose()
    return soup.get_text(separator='\n', strip=True)
def parse_as_yaml(text_content: str) -> str:
    if 'yaml' not in sys.modules or yaml is None: return text_content
    yaml.safe_load(text_content)
    return text_content
def parse_as_doculing(text_content: str) -> str: return text_content
def parse_as_markitdown(text_content: str) -> str: return text_content

def get_parser_for_format(format_name: str) -> callable:
    parsers = {"text": parse_as_plaintext, "markdown": parse_as_markdown, "json": parse_as_json,
               "html": parse_as_html, "yaml": parse_as_yaml, "doculing": parse_as_doculing,
               "markitdown": parse_as_markitdown}
    return parsers.get(format_name, parse_as_plaintext)

def process_text_stream(raw_text_content: str, source_info: dict, console: Console, format_override: str | None = None) -> str | None:
    actual_format = format_override.lower() if format_override else detect_text_format(raw_text_content)
    if format_override: console.print(f"[green]Processing input as [bold]{actual_format}[/bold] (user override).[/green]")
    else: console.print(f"[green]Detected format: [bold]{actual_format}[/bold][/green]")
    parser_function = get_parser_for_format(actual_format)
    try:
        parsed_content = parser_function(raw_text_content)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to parse content as {actual_format}. Details: {e}")
        return None
    source_type_attr = escape_xml(source_info.get('type', 'unknown_stream'))
    format_attr = escape_xml(actual_format)
    return f'<source type="{source_type_attr}" processed_as_format="{format_attr}">\n<content>{escape_xml(parsed_content)}</content>\n</source>'

stop_words = set()
if ENABLE_COMPRESSION_AND_NLTK:
    try:
        nltk.download("stopwords", quiet=True)
        stop_words = set(stopwords.words("english"))
    except Exception as e:
        print(f"[bold yellow]Warning:[/bold yellow] Failed to download NLTK stopwords. Error: {e}")

TOKEN = os.getenv('GITHUB_TOKEN', 'default_token_here')
if TOKEN == 'default_token_here':
    print("[bold red]Warning:[/bold red] GITHUB_TOKEN not set. Some operations may fail.")
headers = {"Authorization": f"token {TOKEN}"} if TOKEN != 'default_token_here' else {}


def download_file(url: str, target_path: str, headers_to_use: dict):
    response = requests.get(url, headers=headers_to_use)
    response.raise_for_status()
    with open(target_path, "wb") as f:
        f.write(response.content)

def process_ipynb_file(temp_file):
    try:
        with open(temp_file, "r", encoding='utf-8', errors='ignore') as f: nb_content = f.read()
        exporter = PythonExporter()
        py_code, _ = exporter.from_notebook_node(nbformat.reads(nb_content, as_version=4))
        return py_code 
    except Exception as e:
        print(f"[bold red]Error processing notebook {temp_file}: {e}[/bold red]")
        return f"# ERROR PROCESSING NOTEBOOK: {escape_xml(str(e))}\n" 

def escape_xml(text: str) -> str:
    return html.escape(str(text), quote=True)

def _extract_text_from_pdf_object(pdf_reader: PdfReader, source_description: str, console: Console) -> str:
    if not pdf_reader.pages:
        console.print(f"  [bold yellow]Warning:[/bold yellow] PDF file has no pages or is encrypted: {source_description}")
        return "<e>PDF file has no pages or could not be read (possibly encrypted).</e>"
    text_list = []
    for i, page_obj in enumerate(pdf_reader.pages):
        try:
            page_text = page_obj.extract_text()
            if page_text: text_list.append(page_text) 
            else: console.print(f"  [dim]No text extracted from page {i+1} of {source_description} (blank/image-based).[/dim]")
        except Exception as page_e:
            console.print(f"  [bold yellow]Warning:[/bold yellow] Could not extract text from page {i+1} of {source_description}: {page_e}")
            text_list.append(f"\n<e>Error extracting text from page {i+1}: {escape_xml(str(page_e))}</e>\n") 
    if not text_list:
        console.print(f"  [bold yellow]Warning:[/bold yellow] No text extracted from any page of PDF: {source_description}")
        return "<e>No text could be extracted from PDF.</e>"
    return ' '.join(text_list) 

def process_github_repo(repo_url: str, headers_to_use: dict):
    api_base_url = "https://api.github.com/repos/"
    repo_url_parts = repo_url.split("https://github.com/")[-1].split("/")
    repo_name = "/".join(repo_url_parts[:2])
    branch_or_tag, subdirectory = "", ""
    if len(repo_url_parts) > 2 and repo_url_parts[2] == "tree":
        if len(repo_url_parts) > 3: branch_or_tag = repo_url_parts[3]
        if len(repo_url_parts) > 4: subdirectory = "/".join(repo_url_parts[4:])
    contents_url = f"{api_base_url}{repo_name}/contents"
    if subdirectory: contents_url = f"{contents_url}/{subdirectory}"
    if branch_or_tag: contents_url = f"{contents_url}?ref={branch_or_tag}"
    
    repo_content_xml = [f'<source type="github_repository" url="{escape_xml(repo_url)}">']
    
    def process_directory_recursive(url, content_list_xml):
        try:
            response = requests.get(url, headers=headers_to_use); response.raise_for_status(); files = response.json()
            for file_info in files:
                if file_info["type"] == "dir" and file_info["name"] in EXCLUDED_DIRS: continue
                if file_info["type"] == "file" and is_allowed_filetype(file_info["name"]):
                    print(f"Processing {file_info['path']}...")
                    temp_file = f"temp_{file_info['name']}"
                    try:
                        download_file(file_info["download_url"], temp_file, headers_to_use=headers_to_use)
                        content_list_xml.append(f'\n<file path="{escape_xml(file_info["path"])}">')
                        file_content_raw = ""
                        if file_info["name"].endswith(".ipynb"): file_content_raw = process_ipynb_file(temp_file)
                        else: file_content_raw = safe_file_read(temp_file)
                        content_list_xml.append(escape_xml(file_content_raw)) 
                        content_list_xml.append('</file>')
                    except Exception as e:
                        print(f"[bold red]Error processing file {file_info['path']}: {e}[/bold red]")
                        content_list_xml.extend([f'\n<file path="{escape_xml(file_info["path"])}">', f'<error>Failed to download/process: {escape_xml(str(e))}</error>', '</file>'])
                    finally:
                        if os.path.exists(temp_file): os.remove(temp_file)
                elif file_info["type"] == "dir": process_directory_recursive(file_info["url"], content_list_xml)
        except Exception as e:
            print(f"[bold red]Error processing directory {url}: {e}[/bold red]")
            content_list_xml.append(f'<error>Failed processing directory {escape_xml(url)}: {escape_xml(str(e))}</error>')

    process_directory_recursive(contents_url, repo_content_xml)
    repo_content_xml.append('\n</source>')
    print("GitHub repository processing finished.")
    return "\n".join(repo_content_xml)

def process_local_folder(local_path):
    content_xml = [f'<source type="local_folder" path="{escape_xml(local_path)}">']
    def process_local_directory_recursive(current_path, content_list_xml):
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                relative_path = os.path.relpath(item_path, local_path)
                if os.path.isdir(item_path):
                    if item not in EXCLUDED_DIRS: process_local_directory_recursive(item_path, content_list_xml)
                elif os.path.isfile(item_path) and is_allowed_filetype(item):
                    print(f"Processing {item_path}...")
                    content_list_xml.append(f'\n<file path="{escape_xml(relative_path)}">')
                    try:
                        file_content_raw = ""
                        if item.lower().endswith(".ipynb"): file_content_raw = process_ipynb_file(item_path)
                        elif item.lower().endswith(".pdf"): file_content_raw = _process_pdf_content_from_path(item_path) 
                        elif item.lower().endswith(('.xls', '.xlsx')):
                            content_list_xml.pop() 
                            for sheet, md in excel_to_markdown(item_path).items(): 
                                virtual_name = f"{os.path.splitext(relative_path)[0]}_{sheet}.md"
                                content_list_xml.extend([f'\n<file path="{escape_xml(virtual_name)}">', escape_xml(md), '</file>'])
                            continue 
                        else: file_content_raw = safe_file_read(item_path)
                        if not item.lower().endswith(".pdf") and not item.lower().endswith(('.xls', '.xlsx')):
                            content_list_xml.append(escape_xml(file_content_raw))
                        elif item.lower().endswith(".pdf"): 
                             content_list_xml.append(file_content_raw) # Already text or <e>
                    except Exception as e:
                        print(f"[bold red]Error reading file {item_path}: {e}[/bold red]")
                        content_list_xml.append(f'<error>Failed to read file: {escape_xml(str(e))}</error>')
                    content_list_xml.append('</file>')
        except Exception as e:
            print(f"[bold red]Error reading directory {current_path}: {e}[/bold red]")
            content_list_xml.append(f'<error>Failed reading directory {escape_xml(current_path)}: {escape_xml(str(e))}</error>')
    process_local_directory_recursive(local_path, content_xml)
    content_xml.append('\n</source>')
    print("Local folder processing finished.")
    return '\n'.join(content_xml)

def _process_pdf_content_from_path(file_path: str) -> str:
    console = Console() 
    console.print(f"  Extracting text from local PDF: {file_path}")
    try:
        with open(file_path, 'rb') as pdf_file_obj:
            pdf_reader = PdfReader(pdf_file_obj)
            return _extract_text_from_pdf_object(pdf_reader, file_path, console) 
    except FileNotFoundError:
        console.print(f"[bold red]Error: PDF file not found at {file_path}[/bold red]")
        return f"<e>PDF file not found: {escape_xml(file_path)}</e>"
    except Exception as e: 
        console.print(f"[bold red]Error reading PDF file {file_path}: {e}[/bold red]")
        return f"<e>Failed to read or process PDF file: {escape_xml(str(e))}</e>"

def _download_and_read_file(url: str, headers_to_use: dict):
    print(f"  Downloading and reading content from: {url}")
    try:
        response = requests.get(url, headers=headers_to_use); response.raise_for_status()
        encoding = response.encoding or 'utf-8'
        try: return response.content.decode(encoding) 
        except UnicodeDecodeError:
            try: return response.content.decode('latin-1') 
            except Exception as de: return f"<e>Failed to decode content: {escape_xml(str(de))}</e>"
    except requests.RequestException as e: return f"<e>Failed to download file: {escape_xml(str(e))}</e>"
    except Exception as e: return f"<e>Unexpected error: {escape_xml(str(e))}</e>"

def _convert_excel_sheets_to_markdown(
    workbook_data: Union[pd.ExcelFile, Dict[str, pd.DataFrame]], 
    source_description: str, 
    console: Console,
    skip_rows: int = 0, 
    min_header_cells: int = 2, 
    sheet_filter: List[str] | None = None
) -> Dict[str, str]:
    md_tables: Dict[str, str] = {}
    sheet_names = []
    if isinstance(workbook_data, pd.ExcelFile): sheet_names = workbook_data.sheet_names
    elif isinstance(workbook_data, dict): sheet_names = list(workbook_data.keys())
    else:
        console.print(f"[bold red]Error: Invalid workbook_data for '{source_description}'.[/bold red]"); return md_tables
    if not sheet_names:
        console.print(f"[bold yellow]Warning: No sheets in Excel: {source_description}[/bold yellow]"); return md_tables

    for sheet_name in sheet_names:
        if sheet_filter and sheet_name not in sheet_filter:
            console.print(f"  Skipping sheet '{sheet_name}' (filtered) from '{source_description}'."); continue
        try:
            df = pd.read_excel(workbook_data, sheet_name=sheet_name, header=None) if isinstance(workbook_data, pd.ExcelFile) else workbook_data[sheet_name]
            if isinstance(workbook_data, dict) and (df.columns.name is not None or any(str(c).startswith("Unnamed:") for c in df.columns)):
                df.columns = range(df.shape[1]); df = df.reset_index(drop=True)
            
            df_processed = df.iloc[skip_rows:].reset_index(drop=True)
            header_idx = -1
            try: header_idx = next(i for i, r in df_processed.iterrows() if r.count() >= min_header_cells)
            except StopIteration: console.print(f"  [dim]No clear header in '{sheet_name}' of '{source_description}'. Fallback.[/dim]")

            if header_idx != -1:
                header = df_processed.loc[header_idx].copy().ffill()
                body = df_processed.loc[header_idx + 1:].copy(); body.columns = header; body.dropna(how="all", inplace=True)
                md_tables[sheet_name] = body.to_markdown(index=False) 
                console.print(f"  Processed sheet '{sheet_name}' from '{source_description}' (header at {header_idx + skip_rows}).")
            else:
                console.print(f"  [dim]Fallback: header=0 for sheet '{sheet_name}' of '{source_description}'.[/dim]")
                df_header0 = pd.read_excel(workbook_data,sheet_name=sheet_name,header=skip_rows) if isinstance(workbook_data,pd.ExcelFile) else \
                             (df_processed.iloc[1:].set_axis(df_processed.iloc[0],axis=1,inplace=False) if not df_processed.empty and not df_processed.iloc[0].isnull().all() else pd.DataFrame()) # inplace=False for set_axis
                df_header0.dropna(how="all", inplace=True)
                if not df_header0.empty:
                    md_tables[sheet_name] = df_header0.to_markdown(index=False) 
                    console.print(f"  Processed sheet '{sheet_name}' from '{source_description}' (fallback, header at {skip_rows}).")
                else: console.print(f"  [yellow]Warning: Sheet '{sheet_name}' from '{source_description}' empty after fallback.[/yellow]")
        except Exception as e: console.print(f"[bold red]Error processing sheet '{sheet_name}' from '{source_description}': {e}[/bold red]")
    if not md_tables: console.print(f"[bold yellow]Warning: No usable data from any sheet in: {source_description}[/bold yellow]")
    return md_tables

def excel_to_markdown(file_path:Union[str,Path],*,skip_rows:int=0,min_header_cells:int=2,sheet_filter:List[str]|None=None)->Dict[str,str]:
    file_path = Path(file_path).expanduser().resolve(); console = Console()
    console.print(f"Processing Excel file: {file_path}")
    if file_path.suffix.lower() not in {".xls",".xlsx"}: raise ValueError("Only .xls/.xlsx supported")
    try:
        workbook_data = pd.read_excel(file_path, sheet_name=None, header=None)
        if not workbook_data: raise RuntimeError("Excel file empty or no sheets.")
        markdown_tables = _convert_excel_sheets_to_markdown(workbook_data, str(file_path), console, skip_rows, min_header_cells, sheet_filter)
        if not markdown_tables: raise RuntimeError(f"Workbook '{file_path}' no usable data.")
        return markdown_tables
    except FileNotFoundError: console.print(f"[bold red]Error: Excel file not found: '{file_path}'.[/bold red]"); raise
    except Exception as e: console.print(f"[bold red]Error processing local Excel '{file_path}': {e}[/bold red]"); raise RuntimeError(f"Failed Excel '{file_path}': {e}")

def excel_to_markdown_from_url(url:str, headers_to_use: dict, *, skip_rows:int=0,min_header_cells:int=2,sheet_filter:List[str]|None=None)->Dict[str,str]:
    console = Console(); console.print(f"  Downloading Excel from URL: {url}")
    try:
        response = requests.get(url, headers=headers_to_use); response.raise_for_status()
        excel_buffer = io.BytesIO(response.content)
        workbook_data = pd.read_excel(excel_buffer, sheet_name=None, header=None)
        if not workbook_data: raise RuntimeError("Excel from URL empty or no sheets.")
        markdown_tables = _convert_excel_sheets_to_markdown(workbook_data, url, console, skip_rows, min_header_cells, sheet_filter)
        if not markdown_tables: raise RuntimeError(f"Workbook from URL '{url}' no usable data.")
        return markdown_tables
    except requests.RequestException as e: console.print(f"[bold red]Error downloading Excel {url}: {e}[/bold red]"); raise
    except Exception as e: console.print(f"[bold red]Error processing Excel from URL '{url}': {e}[/bold red]"); raise RuntimeError(f"Failed Excel from URL '{url}': {e}")

def process_arxiv_pdf(arxiv_abs_url): # Uses requests.get directly without headers
    pdf_url = arxiv_abs_url.replace("/abs/", "/pdf/") + ".pdf"; temp_pdf_path = 'temp_arxiv.pdf'; console = Console() 
    try:
        console.print(f"Downloading ArXiv PDF from {pdf_url}...")
        response = requests.get(pdf_url); response.raise_for_status() # No headers passed here
        with open(temp_pdf_path, 'wb') as pdf_file: pdf_file.write(response.content)
        console.print("Extracting text from PDF...")
        with open(temp_pdf_path, 'rb') as pdf_file_obj:
            pdf_reader = PdfReader(pdf_file_obj)
            extracted_text_or_error = _extract_text_from_pdf_object(pdf_reader, arxiv_abs_url, console)
        content_to_insert = extracted_text_or_error if extracted_text_or_error.strip().startswith("<e>") else escape_xml(extracted_text_or_error)
        formatted_output = f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}">\n{content_to_insert}\n</source>'
        if "<e>" not in extracted_text_or_error: console.print("ArXiv paper processed successfully.")
        return formatted_output
    except requests.RequestException as e:
        console.print(f"[bold red]Error downloading ArXiv PDF {pdf_url}: {e}[/bold red]")
        return f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}"><error>Failed to download PDF: {escape_xml(str(e))}</error></source>'
    except Exception as e: 
        console.print(f"[bold red]Error processing ArXiv PDF {arxiv_abs_url}: {e}[/bold red]")
        return f'<source type="arxiv" url="{escape_xml(arxiv_abs_url)}"><error>Failed to process PDF: {escape_xml(str(e))}</error></source>'
    finally:
        if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)

def fetch_youtube_transcript(url): # Does not use headers
    def extract_video_id(url):
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, url); return match.group(1) if match else None
    video_id = extract_video_id(url)
    if not video_id:
        print(f"[bold red]Could not extract YouTube video ID from: {url}[/bold red]")
        return f'<source type="youtube_transcript" url="{escape_xml(url)}">\n<error>Could not extract video ID.</error>\n</source>'
    try:
        print(f"Fetching transcript for YouTube video ID: {video_id}")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter(); formatted_transcript = formatter.format_transcript(transcript) 
        print("Transcript fetched successfully.")
        return f'<source type="youtube_transcript" url="{escape_xml(url)}">\n{escape_xml(formatted_transcript)}\n</source>' 
    except Exception as e:
        print(f"[bold red]Error fetching YouTube transcript for {url}: {e}[/bold red]")
        return f'<source type="youtube_transcript" url="{escape_xml(url)}">\n<error>{escape_xml(str(e))}</error>\n</source>'

def preprocess_text(input_file: str, output_file: str):
    """
    Processes text from an input XML file for compression.
    It attempts to parse the input file as XML. If successful, it iterates
    through all elements, extracts their text content, processes this text
    (lowercasing, regex substitutions, optional stopword removal), and
    concatenates all processed text pieces with newlines.
    If XML parsing fails, it falls back to processing the entire file content
    as a single block of plain text.
    The processed plain text is then written to the output file.
    """
    print("Preprocessing text for compression (if enabled)...")
    try:
        with open(input_file, "r", encoding="utf-8") as infile:
            input_text = infile.read()
    except Exception as e:
        print(f"[bold red]Error reading input file {input_file}: {e}[/bold red]")
        return # Cannot proceed if input file cannot be read

    # This helper function remains unchanged as per requirements
    def process_content(text_content: str) -> str:
        text_content = re.sub(r"[\n\r]+", "\n", text_content) # Normalize newlines
        # The following regex is aggressive and might be revisited later.
        # It strips characters not in the allowed set.
        text_content = re.sub(r"[^a-zA-Z0-9\s_.,!?:;@#$%^&*()+\-=[\]{}|\\<>`~'\"/]+", "", text_content)
        text_content = re.sub(r"\s+", " ", text_content) # Normalize whitespace
        text_content = text_content.lower()
        if ENABLE_COMPRESSION_AND_NLTK and stop_words:
            words = text_content.split()
            words = [word for word in words if word not in stop_words]
            text_content = " ".join(words)
        return text_content

    final_processed_text = ""
    try:
        # Attempt to parse as XML
        root = ET.fromstring(input_text)
        processed_texts = []
        for elem in root.iter():
            if elem.text and elem.text.strip(): # Ensure text exists and is not just whitespace
                cleaned_text = process_content(elem.text)
                processed_texts.append(cleaned_text)
        final_processed_text = "\n".join(processed_texts)
        print("Text preprocessing with XML parsing completed.")
    except ET.ParseError:
        # Fallback: process as plain text if input is not valid XML
        print("[yellow]Warning: Input for preprocessing was not valid XML. Processing as plain text.[/yellow]")
        final_processed_text = process_content(input_text)
    except Exception as e:
        # Catch any other unexpected errors during the try block (e.g., within process_content)
        print(f"[bold red]Error during text preprocessing: {e}[/bold red]")
        print("[bold yellow]Warning:[/bold yellow] Preprocessing failed, writing original content to compressed file as a fallback.")
        # Fallback to writing the original input if processing fails catastrophically
        final_processed_text = input_text 

    try:
        with open(output_file, "w", encoding="utf-8") as out_file:
            out_file.write(final_processed_text)
        print(f"Processed text written to {output_file}")
    except Exception as e:
        print(f"[bold red]Error writing processed text to {output_file}: {e}[/bold red]")


def is_potential_alias(arg_string):
    return bool(arg_string) and not any(c in arg_string for c in ['.', '/', ':', '\\'])

def handle_add_alias(args, console):
    ensure_alias_dir_exists()
    alias_name = ""
    targets = []
    if '--add-alias' in args: 
        alias_name_idx = args.index("--add-alias") + 1
        if alias_name_idx < len(args): alias_name = args[alias_name_idx]
        else: console.print("[bold red]Error: Alias name not provided after --add-alias.[/bold red]"); return True
        targets = args[alias_name_idx+1:]
    else: 
        console.print("[bold red]Error: --add-alias flag not found correctly in handle_add_alias.[/bold red]"); return True


    if any(c in alias_name for c in ['/', '\\', '.', ':']): console.print(f"[bold red]Error: Invalid alias name '{alias_name}'.[/bold red]"); return True
    if not targets: console.print("[bold red]Error: No targets for alias.[/bold red]"); return True
    try:
        with open(ALIAS_DIR / alias_name, "w", encoding="utf-8") as f:
            for target in targets: f.write(target + "\n") 
        console.print(f"[green]Alias '{alias_name}' created/updated for: {', '.join(targets)}[/green]")
    except IOError as e: console.print(f"[bold red]Error creating alias file: {e}[/bold red]")
    return True

def handle_alias_from_clipboard(args, console):
    ensure_alias_dir_exists()
    alias_name = ""
    if '--alias-from-clipboard' in args :
        alias_name_idx = args.index("--alias-from-clipboard") + 1
        if alias_name_idx < len(args): alias_name = args[alias_name_idx]
        else: console.print("[bold red]Error: Alias name not provided after --alias-from-clipboard.[/bold red]"); return True
    else: 
        console.print("[bold red]Error: --alias-from-clipboard flag not found correctly.[/bold red]"); return True

    if any(c in alias_name for c in ['/', '\\', '.', ':']): console.print(f"[bold red]Error: Invalid alias name '{alias_name}'.[/bold red]"); return True
    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content or not clipboard_content.strip(): console.print("[yellow]Clipboard empty. Alias not created.[/yellow]"); return True
        targets = [line.strip() for line in clipboard_content.splitlines() if line.strip()] 
        if not targets: console.print("[yellow]No valid targets from clipboard. Alias not created.[/yellow]"); return True
        with open(ALIAS_DIR / alias_name, "w", encoding="utf-8") as f:
            for target in targets: f.write(target + "\n")
        console.print(f"[green]Alias '{alias_name}' created/updated from clipboard: {', '.join(targets)}[/green]")
    except Exception as e: console.print(f"[bold red]Error with clipboard/alias file: {e}[/bold red]")
    return True

def load_alias(alias_name, console):
    ensure_alias_dir_exists()
    alias_file = ALIAS_DIR / alias_name
    if alias_file.is_file():
        try:
            with open(alias_file, "r", encoding="utf-8") as f: targets = [l.strip() for l in f if l.strip()]
            if not targets: console.print(f"[yellow]Warning: Alias '{alias_name}' is empty.[/yellow]"); return []
            return targets
        except IOError as e: console.print(f"[bold red]Error reading alias {alias_file}: {e}[/bold red]"); return None
    return None

def resolve_single_input_source(source_string, console):
    if is_potential_alias(source_string):
        console.print(f"[dim]Checking if '{source_string}' is an alias...[/dim]")
        resolved = load_alias(source_string, console)
        if resolved is not None:
            if resolved: console.print(f"[cyan]Alias '{source_string}' expanded to: {', '.join(resolved)}[/cyan]")
            else: console.print(f"[yellow]Alias '{source_string}' is empty. Skipping.[/yellow]")
            return resolved
        else: 
            console.print(f"[dim]'{source_string}' not a known alias or error reading. Treating as direct input.[/dim]")
            return [source_string]
    return [source_string]

def get_token_count(text, disallowed_special=[], chunk_size=1000):
    enc = tiktoken.get_encoding("cl100k_base")
    text_no_tags = re.sub(r'<[^>]+>', '', text) 
    chunks = [text_no_tags[i:i+chunk_size] for i in range(0,len(text_no_tags),chunk_size)]; total_tokens=0
    for chunk in chunks:
        try: total_tokens += len(enc.encode(chunk, disallowed_special=disallowed_special))
        except Exception as e: print(f"[yellow]Warning: Error encoding chunk for token count: {e}[/yellow]"); total_tokens += len(chunk)//4
    return total_tokens

def is_same_domain(base, new): return urlparse(base).netloc == urlparse(new).netloc
def is_within_depth(base, current, max_depth):
    base_p = urlparse(base).path.rstrip('/'); current_p = urlparse(current).path.rstrip('/')
    if not current_p.startswith(base_p): return False
    return (len(current_p.split('/')) if current_p else 0) - (len(base_p.split('/')) if base_p else 0) <= max_depth

def process_web_pdf(url: str) -> str | None: 
    temp_pdf_path = 'temp_web.pdf'
    console = Console() 
    try:
        console.print(f"  Downloading PDF: {url}")
        response = requests.get(url, timeout=30); response.raise_for_status()
        if 'application/pdf' not in response.headers.get('Content-Type', '').lower():
            console.print(f"  [bold yellow]Warning:[/bold yellow] URL doesn't report as PDF, skipping: {url}")
            return "<error>Skipped non-PDF content reported at PDF URL.</error>" 
        with open(temp_pdf_path, 'wb') as pdf_file: pdf_file.write(response.content)
        console.print(f"  Extracting text from PDF: {url}")
        with open(temp_pdf_path, 'rb') as pdf_file_obj:
            pdf_reader = PdfReader(pdf_file_obj)
            return _extract_text_from_pdf_object(pdf_reader, url, console) 
    except requests.RequestException as e:
        console.print(f"  [bold red]Error downloading PDF {url}: {e}[/bold red]")
        return f"<error>Failed to download PDF: {escape_xml(str(e))}</error>" 
    except Exception as e: 
        console.print(f"  [bold red]Error processing PDF {url}: {e}[/bold red]")
        return f"<error>Failed to process PDF: {escape_xml(str(e))}</error>" 
    finally:
        if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)

def crawl_and_extract_text(base_url, max_depth, include_pdfs, ignore_epubs, headers_to_use: dict = None): 
    if headers_to_use is None: headers_to_use = {} 

    visited, to_visit, processed_content = set(), [(base_url,0)], {}
    all_text_xml = [f'<source type="web_crawl" base_url="{escape_xml(base_url)}">'] 
    print(f"Crawling: {base_url} (Depth: {max_depth}, PDFs: {include_pdfs})")
    while to_visit:
        curr_url, depth = to_visit.pop(0)
        parsed = urlparse(curr_url); clean_url = parsed._replace(fragment="").geturl()
        if not parsed.scheme: clean_url = "http://" + clean_url
        if clean_url in visited or not is_same_domain(base_url,clean_url) or not is_within_depth(base_url,clean_url,max_depth): continue
        if ignore_epubs and clean_url.lower().endswith('.epub'): print(f"Skipping EPUB: {clean_url}"); visited.add(clean_url); continue
        print(f"Processing (Depth {depth}): {clean_url}"); visited.add(clean_url)
        page_content_xml_inner = f'\n<page url="{escape_xml(clean_url)}">' 
        try:
            if clean_url.lower().endswith('.pdf'):
                if include_pdfs:
                    pdf_text_or_error = process_web_pdf(clean_url) 
                    content_to_add = pdf_text_or_error if (pdf_text_or_error and pdf_text_or_error.strip().startswith("<e>")) else escape_xml(pdf_text_or_error or "")
                    page_content_xml_inner += f'\n{content_to_add}\n'
                else: page_content_xml_inner += '\n<skipped>PDF ignored by config</skipped>\n'
            else:
                response = requests.get(clean_url, headers={'User-Agent':'Mozilla/5.0'}, timeout=30); response.raise_for_status()
                if 'text/html' not in response.headers.get('Content-Type','').lower():
                    page_content_xml_inner += f'\n<skipped>Non-HTML: {escape_xml(response.headers.get("Content-Type","N/A"))}</skipped>\n'
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for el in soup(['script','style','head','title','meta','[document]','nav','footer','aside']): el.decompose()
                    for comment in soup.find_all(string=lambda t: isinstance(t,Comment)): comment.extract()
                    text_raw = soup.get_text(separator='\n', strip=True)
                    page_content_xml_inner += f'\n{escape_xml(text_raw)}\n' 
                    if depth < max_depth:
                        for link in soup.find_all('a', href=True):
                            try:
                                new_raw = link['href']
                                if new_raw and not new_raw.startswith(('mailto:','javascript:','#')):
                                    new_url = urljoin(clean_url, new_raw)
                                    parsed_new = urlparse(new_url)
                                    if not parsed_new.scheme: new_url = parsed_new._replace(scheme=urlparse(clean_url).scheme).geturl()
                                    new_clean = urlparse(new_url)._replace(fragment="").geturl()
                                    if new_clean not in visited and is_same_domain(base_url,new_clean) and is_within_depth(base_url,new_clean,max_depth) and not (ignore_epubs and new_clean.lower().endswith('.epub')):
                                        if (new_clean, depth+1) not in to_visit: to_visit.append((new_clean, depth+1))
                            except Exception as le: print(f"  [yellow]Link parse error '{link.get('href')}': {le}[/yellow]")
        except Exception as e: page_content_xml_inner += f'\n<error>Failed to process page: {escape_xml(str(e))}</error>\n'
        page_content_xml_inner += '</page>'; all_text_xml.append(page_content_xml_inner); processed_content[clean_url]=page_content_xml_inner
    all_text_xml.append('\n</source>'); print("Crawl finished.")
    return {'content': '\n'.join(all_text_xml), 'processed_urls': list(processed_content.keys())}


def process_doi_or_pmid(identifier): 
    sci_hub_domains = ['https://sci-hub.se/', 'https://sci-hub.st/', 'https://sci-hub.ru/'] 
    pdf_filename = f"temp_doi_{identifier.replace('/', '-')}.pdf"
    pdf_text_content_raw = None 
    console = Console() 
    sci_hub_req_headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}

    for domain in sci_hub_domains:
        console.print(f"Attempting Sci-Hub domain: {domain} for identifier: {identifier}")
        try:
            response = requests.post(domain, headers=sci_hub_req_headers, data={'request': identifier}, timeout=60)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            pdf_url_on_page = None
            iframe = soup.find('iframe', id='pdf')
            if iframe and iframe.get('src'): pdf_url_on_page = urljoin(domain, iframe['src'])
            else: 
                links = soup.find_all('a', href=lambda h: h and ('.pdf' in h or 'download=true' in h))
                if links: pdf_url_on_page = urljoin(domain, links[0]['href']) 

            if not pdf_url_on_page: console.print(f"  No PDF link found on page from {domain}"); continue
            if pdf_url_on_page.startswith("//"): pdf_url_on_page = "https:" + pdf_url_on_page
            
            console.print(f"  Downloading PDF from: {pdf_url_on_page}")
            pdf_response = requests.get(pdf_url_on_page, headers=sci_hub_req_headers, timeout=120)
            pdf_response.raise_for_status()
            if 'application/pdf' not in pdf_response.headers.get('Content-Type','').lower():
                console.print(f"  [yellow]Downloaded content not PDF from {pdf_url_on_page}, trying next domain.[/yellow]"); continue
            with open(pdf_filename, 'wb') as f: f.write(pdf_response.content)
            console.print("  Extracting text from PDF...")
            with open(pdf_filename, 'rb') as pdf_file_obj:
                pdf_reader = PdfReader(pdf_file_obj)
                pdf_text_content_raw = _extract_text_from_pdf_object(pdf_reader, identifier, console) 
            if not pdf_text_content_raw.strip().startswith("<e>"): console.print(f"Identifier {identifier} processed successfully via {domain}."); break 
            else: console.print(f"  [yellow]Failed to extract text cleanly from PDF via {domain}, trying next.[/yellow]")
        except Exception as e: console.print(f"  Error with {domain}: {e}"); continue
        finally:
            if os.path.exists(pdf_filename): os.remove(pdf_filename)
    
    output_xml = f'<source type="sci-hub" identifier="{escape_xml(identifier)}">\n'
    if pdf_text_content_raw:
        content_to_insert = pdf_text_content_raw if pdf_text_content_raw.strip().startswith("<e>") else escape_xml(pdf_text_content_raw)
        output_xml += content_to_insert
    else: 
        console.print(f"[bold red]Failed to process identifier {identifier} using all Sci-Hub domains.[/bold red]")
        output_xml += '<error>Could not retrieve or process PDF via Sci-Hub after trying multiple domains.</error>'
    output_xml += '\n</source>'
    return output_xml

def process_github_pull_request(pull_request_url: str, headers_to_use: dict):
    url_parts = pull_request_url.split("/")
    if len(url_parts) < 7 or url_parts[-2] != 'pull':
        return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Invalid URL format.</error></source>'
    
    repo_owner, repo_name, pull_request_number = url_parts[3], url_parts[4], url_parts[-1]
    api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pull_request_number}"
    repo_url_for_content = f"https://github.com/{repo_owner}/{repo_name}"
    
    try:
        print(f"Fetching PR: {pull_request_url}"); 
        response = requests.get(api_base_url, headers=headers_to_use); response.raise_for_status(); data = response.json()
        
        text_l = [f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}">', 
                  f'<title>{escape_xml(data.get("title","N/A"))}</title>', 
                  '<description>', escape_xml(data.get("body","") or ""), '</description>', 
                  f"<details>User: {escape_xml(data.get('user',{}).get('login','N/A'))}, State: {escape_xml(data.get('state','N/A'))}, Commits: {escape_xml(data.get('commits','N/A'))}, Base: {escape_xml(data.get('base',{}).get('label','N/A'))}, Head: {escape_xml(data.get('head',{}).get('label','N/A'))}</details>"]
        
        if data.get("diff_url"):
            print("Fetching PR diff..."); 
            diff_r = requests.get(data["diff_url"], headers=headers_to_use); diff_r.raise_for_status()
            text_l.extend(['\n<diff>', escape_xml(diff_r.text), '</diff>']) 
        
        comments_l = []
        for url_key in ["comments_url", "review_comments_url"]:
            if data.get(url_key):
                print(f"Fetching {url_key.split('_')[0]} comments..."); 
                c_r = requests.get(data[url_key], headers=headers_to_use)
                if c_r.ok: comments_l.extend(c_r.json())
                else: print(f"[yellow]Warning: Could not fetch {url_key.split('_')[0]} comments: {c_r.status_code}[/yellow]")
        
        if comments_l:
            text_l.append('\n<comments>'); comments_l.sort(key=lambda c:c.get("created_at",""))
            for c in comments_l:
                author=escape_xml(c.get('user',{}).get('login','N/A')); body=escape_xml(c.get('body','')or"")
                path_attr=escape_xml(c.get("path","")); line_attr=escape_xml(str(c.get("line") or c.get("original_line","")))
                ctx=f' path="{path_attr}"' if path_attr else ''; ctx+=f' line="{line_attr}"' if line_attr else ''
                text_l.extend([f'<comment author="{author}"{ctx}>', body, '</comment>'])
            text_l.append('</comments>')
        
        print(f"Fetching repo content: {repo_url_for_content}"); base_ref=data.get('base',{}).get('ref')
        repo_url_with_ref = f"{repo_url_for_content}/tree/{base_ref}" if base_ref else repo_url_for_content
        text_l.extend(['\n<!-- Associated Repository Content -->', process_github_repo(repo_url_with_ref, headers_to_use=headers_to_use), '\n</source>'])
        print(f"PR {pull_request_number} processed."); return "\n".join(text_l)
    
    except requests.RequestException as e:
        print(f"[bold red]Error fetching GitHub PR data for {pull_request_url}: {e}[/bold red]")
        return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Failed to fetch PR data: {escape_xml(str(e))}</error></source>'
    except Exception as e: 
         print(f"[bold red]Unexpected error processing GitHub PR {pull_request_url}: {e}[/bold red]")
         return f'<source type="github_pull_request" url="{escape_xml(pull_request_url)}"><error>Unexpected error: {escape_xml(str(e))}</error></source>'

def process_github_issue(issue_url: str, headers_to_use: dict):
    url_parts = issue_url.split("/")
    if len(url_parts) < 7 or url_parts[-2] != 'issues':
        return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Invalid URL format.</error></source>'
        
    repo_owner, repo_name, issue_number = url_parts[3], url_parts[4], url_parts[-1]
    api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
    repo_url_for_content = f"https://github.com/{repo_owner}/{repo_name}"
    
    try:
        print(f"Fetching Issue: {issue_url}"); 
        response = requests.get(api_base_url, headers=headers_to_use); response.raise_for_status(); data = response.json()
        
        text_l = [f'<source type="github_issue" url="{escape_xml(issue_url)}">', 
                  f'<title>{escape_xml(data.get("title","N/A"))}</title>', 
                  '<description>', escape_xml(data.get("body","") or ""), '</description>', 
                  f"<details>User: {escape_xml(data.get('user',{}).get('login','N/A'))}, State: {escape_xml(data.get('state','N/A'))}, Number: {escape_xml(data.get('number','N/A'))}</details>"]
        
        if data.get("comments_url"):
            print("Fetching issue comments..."); 
            c_r = requests.get(data["comments_url"], headers=headers_to_use)
            if c_r.ok:
                comments_data = c_r.json()
                if comments_data:
                    text_l.append('\n<comments>'); comments_data.sort(key=lambda c:c.get("created_at",""))
                    for c_item in comments_data: 
                        author=escape_xml(c_item.get('user',{}).get('login','N/A')); body=escape_xml(c_item.get('body','')or"")
                        text_l.extend([f'<comment author="{author}">', body, '</comment>'])
                    text_l.append('</comments>')
            else: print(f"[yellow]Warning: Could not fetch issue comments: {c_r.status_code}[/yellow]")
        
        print(f"Fetching repo content: {repo_url_for_content}")
        text_l.extend(['\n<!-- Associated Repository Content -->', process_github_repo(repo_url_for_content, headers_to_use=headers_to_use), '\n</source>'])
        print(f"Issue {issue_number} processed."); return "\n".join(text_l)

    except requests.RequestException as e:
        print(f"[bold red]Error fetching GitHub issue data for {issue_url}: {e}[/bold red]")
        return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Failed to fetch issue data: {escape_xml(str(e))}</error></source>'
    except Exception as e: 
         print(f"[bold red]Unexpected error processing GitHub issue {issue_url}: {e}[/bold red]")
         return f'<source type="github_issue" url="{escape_xml(issue_url)}"><error>Unexpected error: {escape_xml(str(e))}</error></source>'


def dispatch_processing(input_path_or_url: str, console: Console, config: dict) -> str:
    console.print(f"\n[green]Dispatching for:[/] [yellow]{input_path_or_url}[/]")
    max_d, inc_pdf, ign_epub, urls_file = config.get('max_depth',1), config.get('include_pdfs',True), config.get('ignore_epubs',True), config.get('urls_list_file',"processed_urls.txt")
    headers_for_dispatch = config.get('headers', {}) 
    
    result = "" 
    
    if "github.com" in input_path_or_url:
        if "/pull/" in input_path_or_url: result = process_github_pull_request(input_path_or_url, headers_to_use=headers_for_dispatch)
        elif "/issues/" in input_path_or_url: result = process_github_issue(input_path_or_url, headers_to_use=headers_for_dispatch)
        else: result = process_github_repo(input_path_or_url, headers_to_use=headers_for_dispatch)
    elif urlparse(input_path_or_url).scheme in ["http","https"]:
        if "youtube.com" in input_path_or_url or "youtu.be" in input_path_or_url: 
            result = fetch_youtube_transcript(input_path_or_url) 
        elif "arxiv.org/abs/" in input_path_or_url: 
            result = process_arxiv_pdf(input_path_or_url) 
        elif input_path_or_url.lower().endswith('.pdf'):
            console.print("[yellow]Direct PDF URL - single page crawl[/yellow]")
            crawl_res = crawl_and_extract_text(input_path_or_url,0,True,ign_epub, headers_to_use=headers_for_dispatch); result=crawl_res['content']
        elif input_path_or_url.lower().endswith(('.xls','.xlsx')):
            console.print(f"Excel URL: {input_path_or_url}")
            fname=os.path.basename(urlparse(input_path_or_url).path); bname=os.path.splitext(fname)[0]
            parts=[f'<source type="web_excel" url="{escape_xml(input_path_or_url)}">']
            try:
                for sname,md_raw in excel_to_markdown_from_url(input_path_or_url, headers_to_use=headers_for_dispatch).items(): 
                    parts.append(f'<file path="{escape_xml(f"{bname}_{sname}.md")}">{escape_xml(md_raw)}</file>') 
            except Exception as e: parts.append(f'<e>Failed Excel URL: {escape_xml(str(e))}</e>')
            parts.append('</source>'); result='\n'.join(parts)
        elif any(input_path_or_url.lower().endswith(ext) for ext in [x for x in ['.txt','.md','.rst','.tex','.html','.htm','.css','.js','.ts','.py','.java','.c','.cpp','.h','.hpp','.cs','.rb','.php','.swift','.kt','.scala','.rs','.lua','.pl','.sh','.bash','.zsh','.ps1','.sql','.groovy','.dart','.json','.yaml','.yml','.xml','.toml','.ini','.cfg','.conf','.properties','.csv','.tsv','.proto','.graphql','.tf','.tfvars','.hcl'] if is_allowed_filetype(f"test{x}")] if ext != '.pdf'):
            console.print(f"Direct file URL: {input_path_or_url}")
            fcontent_raw=_download_and_read_file(input_path_or_url, headers_to_use=headers_for_dispatch) 
            fname=os.path.basename(urlparse(input_path_or_url).path)
            content_to_insert = fcontent_raw if (fcontent_raw and fcontent_raw.strip().startswith("<e>")) else escape_xml(fcontent_raw or "")
            result = f'<source type="web_file" url="{escape_xml(input_path_or_url)}">\n<file path="{escape_xml(fname)}">\n{content_to_insert}\n</file>\n</source>' 
        else:
            crawl_res = crawl_and_extract_text(input_path_or_url,max_d,inc_pdf,ign_epub, headers_to_use=headers_for_dispatch); result=crawl_res['content'] 
            if crawl_res['processed_urls']:
                with open(urls_file,'w',encoding='utf-8') as uf: uf.write('\n'.join(crawl_res['processed_urls']))
    elif (input_path_or_url.startswith("10.") and "/" in input_path_or_url) or input_path_or_url.isdigit():
        result = process_doi_or_pmid(input_path_or_url) 
    elif os.path.isdir(input_path_or_url): 
        result = process_local_folder(input_path_or_url) 
    elif os.path.isfile(input_path_or_url):
        if input_path_or_url.lower().endswith('.pdf'):
            pdf_text_raw = _process_pdf_content_from_path(input_path_or_url) 
            content_to_insert = pdf_text_raw if pdf_text_raw.strip().startswith("<e>") else escape_xml(pdf_text_raw)
            result = f'<source type="local_file" path="{escape_xml(input_path_or_url)}">\n<file path="{escape_xml(os.path.basename(input_path_or_url))}">\n{content_to_insert}\n</file>\n</source>' 
        elif input_path_or_url.lower().endswith(('.xls','.xlsx')):
            fname=os.path.basename(input_path_or_url);bname=os.path.splitext(fname)[0]
            parts=[f'<source type="local_file" path="{escape_xml(input_path_or_url)}">']
            try:
                for sname,md_raw in excel_to_markdown(input_path_or_url).items(): 
                    parts.append(f'<file path="{escape_xml(f"{bname}_{sname}.md")}">{escape_xml(md_raw)}</file>') 
            except Exception as e: parts.append(f'<e>Failed local Excel: {escape_xml(str(e))}</e>')
            parts.append('</source>'); result='\n'.join(parts)
        else:
            fcontent_raw=safe_file_read(input_path_or_url); fname=os.path.basename(input_path_or_url)
            result = f'<source type="local_file" path="{escape_xml(input_path_or_url)}">\n<file path="{escape_xml(fname)}">\n{escape_xml(fcontent_raw)}\n</file>\n</source>' 
    else: raise ValueError(f"Input type not recognized: {input_path_or_url}")
    return result

def process_input(input_path, progress=None, task=None):
    console=Console(); 
    cfg={'github_token':TOKEN, 'headers':headers, 'max_depth':1, 'include_pdfs':True, 'ignore_epubs':True, 'urls_list_file':"processed_urls.txt"}
    try:
        if task and progress: progress.update(task,description=f"[blue]Processing {input_path}...")
        return dispatch_processing(input_path, console, cfg)
    except Exception as e:
        console.print(f"\n[red]Error processing '{input_path}': {e}[/red]"); console.print_exception(show_locals=False)
        return f'<source type="error" path="{escape_xml(input_path)}"><e>Failed: {escape_xml(str(e))}</e></source>'

def main():
    console=Console()
    if any(arg in sys.argv for arg in ["--help","-h"]): 
        console.print("onefilellm - Aggregate content into a single XML structure.")
        console.print("Usage: python onefilellm.py [options] [input_path|url|alias ...]")
        console.print("\nUse --add-alias or --alias-from-clipboard for alias management.")
        return

    raw_args = sys.argv[1:]; stream_input_mode=False; stream_source_dict={}; stream_content=None; user_fmt_override=None
    input_paths = []
    temp_raw_args = list(raw_args) 

    try:
        if "--format" in temp_raw_args:
            idx = temp_raw_args.index("--format")
            if idx + 1 < len(temp_raw_args): user_fmt_override = temp_raw_args.pop(idx + 1).lower(); temp_raw_args.pop(idx) 
            else: console.print("[bold red]Error: --format requires a TYPE.[/bold red]"); return
        elif "-f" in temp_raw_args:
            idx = temp_raw_args.index("-f")
            if idx + 1 < len(temp_raw_args): user_fmt_override = temp_raw_args.pop(idx + 1).lower(); temp_raw_args.pop(idx)
            else: console.print("[bold red]Error: -f requires a TYPE.[/bold red]"); return
    except ValueError: console.print("[bold red]Error parsing --format/-f.[/bold red]"); return
    raw_args = temp_raw_args 

    if "-" in raw_args:
        if not sys.stdin.isatty():
            console.print("[blue]Reading from stdin...[/blue]")
            stream_content = read_from_stdin()
            if not stream_content: console.print("[red]Error: No input from stdin.[/red]"); return
            is_stream_input_mode = True; stream_source_dict = {'type': 'stdin'}; raw_args.remove("-")
    elif "--clipboard" in raw_args or "-c" in raw_args:
        console.print("[blue]Reading from clipboard...[/blue]")
        stream_content = read_from_clipboard()
        if not stream_content: console.print("[red]Error: No input from clipboard.[/red]"); return
        is_stream_input_mode = True; stream_source_dict = {'type': 'clipboard'}
        if "--clipboard" in raw_args: raw_args.remove("--clipboard")
        if "-c" in raw_args: raw_args.remove("-c")

    if raw_args:
        current_arg = raw_args[0]
        if current_arg == "--add-alias": handle_add_alias(raw_args, console); return
        elif current_arg == "--alias-from-clipboard": handle_alias_from_clipboard(raw_args, console); return
        else: 
            for arg_str in raw_args: input_paths.extend(resolve_single_input_source(arg_str, console))
    
    if not input_paths and not is_stream_input_mode :
        if sys.stdin.isatty() and "-" not in sys.argv[1:]: 
             user_input = Prompt.ask("\nEnter path, URL, or alias", console=console).strip()
             if user_input: input_paths.extend(resolve_single_input_source(user_input, console))
        elif "-" in sys.argv[1:] and sys.stdin.isatty(): 
            console.print("[yellow]Warning: '-' given but no data piped to stdin.[/yellow]")

    if not input_paths and not is_stream_input_mode: console.print("[yellow]No input. Exiting.[/yellow]"); return
    
    outputs=[]
    if is_stream_input_mode and stream_content:
        res = process_text_stream(stream_content, stream_source_dict, console, user_fmt_override)
        if res: outputs.append(res)
    elif input_paths:
        with Progress(TextColumn("[blue]{task.description}"), BarColumn(), TimeRemainingColumn(), console=console, transient=True) as progress:
            task = progress.add_task("Processing inputs...", total=len(input_paths))
            for i, path in enumerate(input_paths):
                res = process_input(path, progress, task) 
                if res: outputs.append(res); console.print(f"[green]Processed: {path}[/green]")
                else: console.print(f"[yellow]No output for: {path}[/yellow]")
                progress.update(task, advance=1)
    
    if not outputs: console.print("[red]No output generated.[/red]"); return
    final_xml = combine_xml_outputs(outputs)
    output_file="output.xml"; compressed_file="compressed_output.txt"
    
    try:
        with open(output_file, "w", encoding="utf-8") as f: f.write(final_xml)
        console.print(f"\nOutput written to {output_file}")
        console.print(f"Uncompressed Tokens: {get_token_count(final_xml)}")

        if ENABLE_COMPRESSION_AND_NLTK:
            console.print(f"Compressing and writing to {compressed_file}...")
            preprocess_text(output_file, compressed_file) 
            compressed_content = safe_file_read(compressed_file)
            console.print(f"Compressed Tokens: {get_token_count(compressed_content)}")
        
        pyperclip.copy(final_xml)
        console.print(f"Main output copied to clipboard.")
    except Exception as e:
        console.print(f"[red]Error during final output/compression: {e}[/red]")

if __name__ == "__main__":
    main()
