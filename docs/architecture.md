## Architecture Diagram


```plaintext
                                                   +---------------------------------+
                                                   |         External Services       |
                                                   |-------------------------------- |
                                                   | +-------------+  +------------+ |
                                                   | | GitHub API  |  | YouTube API| |
                                                   | +-------------+  +------------+ |
                                                   | | Sci-Hub     |  | ArXiv      | |
                                                   | +-------------+  +------------+ |
                                                   +---------------------------------+
                                                                ^
                                                                |
 +-------------------------------------------+                  |
 |                User                       |                  |
 |-------------------------------------------|                  |
 | - Provides input path or URL              |                  |
 | - Receives output and token count         |                  |
 +---------------------+---------------------+                  |
                       |                                        |
                       v                                        |
 +---------------------+---------------------+                  |
 |          Command Line Tool                |                  |
 |-------------------------------------------|                  |
 | - Handles user input                      |                  |
 | - Detects source type                     |                  |
 | - Calls appropriate processing modules    |                  |
 | - Preprocesses text                       |                  |
 | - Generates output files                  |                  |
 | - Copies text to clipboard                |                  |
 | - Reports token count                     |                  |
 +---------------------+---------------------+                  |
                       |                                        |
                       v                                        |
 +---------------------+---------------------+                  |
 |           Source Type Detection           |                  |
 |-------------------------------------------|                  |
 | - Determines type of source (GitHub, local|                  |
 |   YouTube, ArXiv, Sci-Hub, Webpage)       |                  |
 +---------------------+---------------------+                  |
                       |                                        |
                       v                                        |
 +-------------------------------------------+------------------+---------------------+
 |               Processing Modules          |                  |                     |
 |-------------------------------------------|                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | GitHub Repo Proc  |   | Local Dir Proc ||                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | - Requests.get()  |   | - Os.walk()    ||                  |                     |
 | | - Download_file() |   | - Safe_file_   ||                  |                     |
 | | - Process_ipynb() |   |   read()       ||                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 |                                        ^                     |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | YouTube Transcript | | ArXiv PDF Proc|  |                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | - YouTubeTranscript| | - Requests.get|  |                  |                     |
 | |   Api.get()        | | - PdfReader() |  |                  |                     |
 | | - Formatter.format |   +---------------+|                  |                     |
 | +-------------------+                     |                  |                     |
 |                                        ^                     |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | Sci-Hub Paper Proc | | Webpage Crawling||                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 | | - Requests.post() |  | - Requests.get()||                  |                     |
 | | - BeautifulSoup() |  | - BeautifulSoup ||                  |                     |
 | | - Wget.download() |  | - Urljoin()     ||                  |                     |
 | +-------------------+   +----------------+|                  |                     |
 +-------------------------------------------+                  |                     |
                       |                                        |                     |
                       v                                        |                     |
 +-------------------------------------------+                  |                     |
 |              Text Preprocessing           |                  |                     |
 |-------------------------------------------|                  |                     |
 | - Stopword removal                        |                  |                     |
 | - Lowercase conversion                    |                  |                     |
 | - Re.sub()                                |                  |                     |
 | - Nltk.stop_words                         |                  |                     |
 +-------------------------------------------+                  |                     |
                       |                                        |                     |
                       v                                        |                     |
 +-------------------------------------------+                  |                     |
 |              Output Generation            |                  |                     |
 |-------------------------------------------|                  |                     |
 | - Generates compressed text file          |                  |                     |
 | - Generates uncompressed text file        |                  |                     |
 +-------------------------------------------+                  |                     |
                       |                                        |                     |
                       v                                        |                     |
 +-------------------------------------------+                  |                     |
 |              Clipboard Interaction        |                  |                     |
 |-------------------------------------------|                  |                     |
 | - Copies uncompressed text to clipboard   |                  |                     |
 | - Pyperclip.copy()                        |                  |                     |
 +-------------------------------------------+                  |                     |
                       |                                        |                     |
                       v                                        |                     |
 +-------------------------------------------+                  |                     |
 |             Token Count Reporting         |                  |                     |
 |-------------------------------------------|                  |                     |
 | - Reports token count for both outputs    |                  |                     |
| - Cached tiktoken encoding                |                  |                     |
| - Enc.encode() / char estimate            |                  |                     |
 +-------------------------------------------+                  |                     |
                                                                v
                                          +---------------------------------+
                                          |      External Libraries/Tools   |
                                          |---------------------------------|
                                          | - Requests                      |
                                          | - BeautifulSoup                 |
                                          | - PyPDF2                        |
                                          | - Tiktoken                      |
                                          | - Nltk                          |
                                          | - Nbformat                      |
                                          | - Nbconvert                     |
                                          | - YouTube Transcript API        |
                                          | - Pyperclip                     |
                                          | - Wget                          |
                                          | - Tqdm                          |
                                          | - Rich                          |
                                          +---------------------------------+
```

### External Libraries/Tools

The tool relies on several external libraries and tools to perform its functions efficiently. Here is a brief overview of each:

- **Requests**: Used for making HTTP requests to fetch data from web APIs and other online resources.
- **BeautifulSoup4**: A library for parsing HTML and XML documents. It is used for web scraping tasks.
- **PyPDF2**: A library for reading and manipulating PDF files.
- **Tiktoken**: Utilized for encoding text into tokens, essential for LLM input preparation.
- **NLTK**: The Natural Language Toolkit, used for various NLP tasks such as stopword removal.
- **Nbformat**: For reading and writing Jupyter Notebook files.
- **Nbconvert**: Converts Jupyter Notebooks to Python scripts and other formats.
- **YouTube Transcript API**: Fetches transcripts from YouTube videos.
- **Pyperclip**: A cross-platform clipboard module for Python.
- **Wget**: A utility for downloading files from the web.
- **Tqdm**: Provides progress bars for loops.
- **Rich**: Used for rich text and aesthetic formatting in the terminal.

---


onefilellm.py
```
  |-- requests
  |-- BeautifulSoup4
  |-- PyPDF2
  |-- tiktoken
  |-- nltk
  |-- nbformat
  |-- nbconvert
  |-- youtube-transcript-api
  |-- pyperclip
  |-- wget
  |-- tqdm
  |-- rich
  |-- GitHub API
  |-- ArXiv
  |-- YouTube
  |-- Sci-Hub
  |-- Webpage
  |-- Filesystem
main()
  |-- process_github_repo
  |   |-- download_file
  |-- process_github_pull_request
  |   |-- download_file
  |-- process_github_issue
  |   |-- download_file
  |-- process_arxiv_pdf
  |   |-- PdfReader (from PyPDF2)
  |-- process_local_folder
  |-- fetch_youtube_transcript
  |-- crawl_and_extract_text
  |   |-- BeautifulSoup (from BeautifulSoup4)
  |   |-- urlparse (from urllib.parse)
  |   |-- urljoin (from urllib.parse)
  |   |-- is_same_domain
  |   |-- is_within_depth
  |   |-- process_pdf
  |-- process_doi_or_pmid
  |   |-- wget
  |   |-- PdfReader (from PyPDF2)
  |-- preprocess_text
  |   |-- re
  |   |-- stop_words (from nltk.corpus)
  |-- get_token_count
        |-- tiktoken
```

## Sequence Diagram

```
sequenceDiagram
    participant User
    participant onefilellm.py
    participant GitHub API
    participant ArXiv
    participant YouTube
    participant Sci-Hub
    participant Webpage
    participant Filesystem
    participant Clipboard

    User->>onefilellm.py: Start script (python onefilellm.py <input>)
    onefilellm.py->>User: Prompt for input if not provided (path/URL/DOI/PMID)
    User->>onefilellm.py: Provide input

    onefilellm.py->>onefilellm.py: Determine input type
    alt GitHub repository
        onefilellm.py->>GitHub API: Request repository content
        GitHub API->>onefilellm.py: Return file/directory list
        onefilellm.py->>GitHub API: Download files recursively
        onefilellm.py->>Filesystem: Save downloaded files
        onefilellm.py->>onefilellm.py: Process files (text extraction, preprocessing)
    else GitHub pull request
        onefilellm.py->>GitHub API: Request pull request data
        GitHub API->>onefilellm.py: Return PR details, diff, comments
        onefilellm.py->>onefilellm.py: Process and format PR data
        onefilellm.py->>GitHub API: Request repository content (for full repo)
        GitHub API->>onefilellm.py: Return file/directory list
        onefilellm.py->>GitHub API: Download files recursively
        onefilellm.py->>Filesystem: Save downloaded files
        onefilellm.py->>onefilellm.py: Process files (text extraction, preprocessing)
    else GitHub issue
        onefilellm.py->>GitHub API: Request issue data
        GitHub API->>onefilellm.py: Return issue details, comments
        onefilellm.py->>onefilellm.py: Process and format issue data
        onefilellm.py->>GitHub API: Request repository content (for full repo)
        GitHub API->>onefilellm.py: Return file/directory list
        onefilellm.py->>GitHub API: Download files recursively
        onefilellm.py->>Filesystem: Save downloaded files
        onefilellm.py->>onefilellm.py: Process files (text extraction, preprocessing)
    else ArXiv Paper
        onefilellm.py->>ArXiv: Download PDF
        ArXiv->>onefilellm.py: Return PDF content
        onefilellm.py->>onefilellm.py: Extract text from PDF
    else Local Folder
        onefilellm.py->>Filesystem: Read files recursively
        onefilellm.py->>onefilellm.py: Process files (text extraction, preprocessing)
    else YouTube Transcript
        onefilellm.py->>YouTube: Request transcript
        YouTube->>onefilellm.py: Return transcript
    else Web Page
        onefilellm.py->>Webpage: Crawl pages (recursive)
        Webpage->>onefilellm.py: Return HTML content
        onefilellm.py->>onefilellm.py: Extract text from HTML
    else Sci-Hub Paper (DOI/PMID)
        onefilellm.py->>Sci-Hub: Request paper
        Sci-Hub->>onefilellm.py: Return PDF content
        onefilellm.py->>onefilellm.py: Extract text from PDF
    end

    onefilellm.py->>onefilellm.py: Preprocess text (cleaning, compression)
    onefilellm.py->>Filesystem: Write outputs (uncompressed, compressed, URLs)
    onefilellm.py->>Clipboard: Copy uncompressed text to clipboard
    onefilellm.py->>User: Display token counts and file information
```

## Data Flow Diagram

```
Here's the modified Data Flow Diagram represented in plain text format:

External Entities
- User Input
- GitHub API
- ArXiv
- YouTube API
- Sci-Hub
- Web Pages
- Local Files
- Clipboard

Processes
- Input Processing
- GitHub Processing
- ArXiv Processing
- YouTube Processing
- Web Crawling
- Sci-Hub Processing
- Local File Processing
- Text Processing
- Output Handling

Data Stores
- uncompressed_output.txt
- compressed_output.txt
- processed_urls.txt

Data Flow
- User Input -> Input Processing
- Input Processing -> GitHub Processing (if GitHub URL)
- Input Processing -> ArXiv Processing (if ArXiv URL)
- Input Processing -> YouTube Processing (if YouTube URL)
- Input Processing -> Web Crawling (if Web Page URL)
- Input Processing -> Sci-Hub Processing (if DOI or PMID)
- Input Processing -> Local File Processing (if Local File/Folder Path)

- GitHub API -> GitHub Processing (Repository/PR/Issue Data)
- ArXiv -> ArXiv Processing (PDF Content)
- YouTube API -> YouTube Processing (Transcript)
- Web Pages -> Web Crawling (HTML Content)
- Sci-Hub -> Sci-Hub Processing (PDF Content)
- Local Files -> Local File Processing (File Content)

- GitHub Processing -> Text Processing (Extracted Text)
- ArXiv Processing -> Text Processing (Extracted Text)
- YouTube Processing -> Text Processing (Transcript)
- Web Crawling -> Text Processing (Extracted Text)
- Sci-Hub Processing -> Text Processing (Extracted Text)
- Local File Processing -> Text Processing (Extracted Text)

- Text Processing -> Output Handling (Processed Text)

- Output Handling -> uncompressed_output.txt (Uncompressed Text)
- Output Handling -> compressed_output.txt (Compressed Text)
- Output Handling -> processed_urls.txt (Processed URLs)
- Output Handling -> Clipboard (Uncompressed Text)

Detailed Processes
- GitHub Processing -> Process Directory (Repo URL)
  - Process Directory -> Extract Text (Files)
    - Extract Text -> Text Processing
- ArXiv Processing -> Extract PDF Text (PDF)
  - Extract PDF Text -> Text Processing
- YouTube Processing -> Fetch Transcript (Video ID)
  - Fetch Transcript -> Text Processing
- Web Crawling -> Extract Web Text (HTML)
  - Extract Web Text -> Text Processing
- Sci-Hub Processing -> Fetch Sci-Hub Paper (DOI/PMID)
  - Fetch Sci-Hub Paper -> Extract PDF Text
- Local File Processing -> Process Local Directory (Local Path)
  - Process Local Directory -> Extract Text

This plain text representation of the Data Flow Diagram shows the flow of data between external entities, processes, and data stores. It also includes the detailed processes and their interactions.
```



## Call Graph


```
main
|
+--- safe_file_read(filepath, fallback_encoding='latin1')
|
+--- process_local_folder(local_path, output_file)
|    |
|    +--- process_local_directory(local_path, output)
|         |
|         +--- os.walk(local_path)
|         +--- is_allowed_filetype(file)
|         +--- process_ipynb_file(temp_file)
|         |    |
|         |    +--- nbformat.reads(notebook_content, as_version=4)
|         |    +--- PythonExporter().from_notebook_node()
|         |
|         +--- safe_file_read(file_path)
|
+--- process_github_repo(repo_url)
|    |
|    +--- process_directory(url, repo_content)
|         |
|         +--- requests.get(url, headers=headers)
|         +--- is_allowed_filetype(file["name"])
|         +--- download_file(file["download_url"], temp_file)
|         |    |
|         |    +--- requests.get(url, headers=headers)
|         |
|         +--- process_ipynb_file(temp_file)
|         +--- os.remove(temp_file)
|
+--- process_github_pull_request(pull_request_url, output_file)
|    |
|    +--- requests.get(api_base_url, headers=headers)
|    +--- requests.get(diff_url, headers=headers)
|    +--- requests.get(comments_url, headers=headers)
|    +--- requests.get(review_comments_url, headers=headers)
|    +--- process_github_repo(repo_url)
|
+--- process_github_issue(issue_url, output_file)
|    |
|    +--- requests.get(api_base_url, headers=headers)
|    +--- requests.get(comments_url, headers=headers)
|    +--- process_github_repo(repo_url)
|
+--- process_arxiv_pdf(arxiv_abs_url, output_file)
|    |
|    +--- requests.get(pdf_url)
|    +--- PdfReader(pdf_file).pages
|
+--- fetch_youtube_transcript(url)
|    |
|    +--- YouTubeTranscriptApi.get_transcript(video_id)
|    +--- TextFormatter().format_transcript(transcript_list)
|
+--- crawl_and_extract_text(base_url, output_file, urls_list_file, max_depth, include_pdfs, ignore_epubs)
|    |
|    +--- requests.get(current_url)
|    +--- BeautifulSoup(response.content, 'html.parser')
|    +--- process_pdf(url)
|    |    |
|    |    +--- requests.get(url)
|    |    +--- PdfReader(pdf_file).pages
|    |
|    +--- is_same_domain(base_url, new_url)
|    +--- is_within_depth(base_url, current_url, max_depth)
|
+--- process_doi_or_pmid(identifier, output_file)
|    |
|    +--- requests.post(base_url, headers=headers, data=payload)
|    +--- BeautifulSoup(response.content, 'html.parser')
|    +--- wget.download(pdf_url, pdf_filename)
|    +--- PdfReader(pdf_file).pages
|
+--- preprocess_text(input_file, output_file)
|    |
|    +--- safe_file_read(input_file)
|    +--- re.sub(pattern, replacement, text)
|    +--- stop_words.words("english")
|    +--- open(output_file, "w", encoding="utf-8").write(text.strip())
|
+--- get_token_count(text, disallowed_special=[], chunk_size=1000)
|    |
|    +--- _get_cl100k_encoding()  (cached tiktoken encoding)
|    +--- enc.encode(chunk, disallowed_special=disallowed_special) or estimate
|
+--- pyperclip.copy(uncompressed_text)
```
