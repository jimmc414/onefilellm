# OneFileLLM

A CLI utility for aggregating and structuring multi-source data for LLM context.

## Overview

A common task when using Large Language Models is providing them with sufficient context about a complex topic, such as a software project, a research paper, or technical documentation. This often involves manually gathering content from multiple sources like code files, web pages, and API responses, then copy-pasting them into a prompt.

`OneFileLLM` is a command-line tool that automates this data aggregation process. It accepts multiple input sources of various types, determines how to process each one, fetches the content, and combines it all into a single, structured XML output. The result is then copied to the system clipboard, ready for use.

For example, instead of a multi-step manual process:

```bash
# Before: Manual gathering
cat ./src/main.py
cat ./src/utils.py
# (manually open browser to view GitHub issue, copy content)
# (manually combine and paste everything into LLM)
```

`OneFileLLM` provides a direct, single-command alternative:

```bash
# After: Automated aggregation
python onefilellm.py ./src/ https://github.com/user/project/issues/123
# (manually paste into LLM)
```

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/jimmc414/onefilellm.git
    cd onefilellm
    ```
2.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```3.  (Recommended) Set the `GITHUB_TOKEN` environment variable to prevent API rate-limiting and to access private repositories.
    ```bash
    export GITHUB_TOKEN="your_personal_access_token"
    ```

## Usage

The tool is invoked by providing a list of input sources. It supports a variety of source types, which it detects automatically.

**Synopsis:**
`python onefilellm.py [OPTIONS] [INPUT_SOURCES...]`

**Supported Input Sources:**

*   **Local Files & Directories:** `path/to/file.py`, `path/to/project/`
*   **GitHub URLs:**
    *   Repository: `https://github.com/user/repo`
    *   Issue: `https://github.com/user/repo/issues/1`
    *   Pull Request: `https://github.com/user/repo/pull/1`
*   **Web URLs:** `https://docs.example.com/` (for crawling)
*   **Academic Sources:**
    *   ArXiv: `https://arxiv.org/abs/1706.03762`
    *   DOI: `10.1038/s41586-021-03819-2`
*   **YouTube Transcripts:** `https://www.youtube.com/watch?v=...`
*   **Streamed Input:**
    *   From `stdin`: `cat file.txt | python onefilellm.py -`
    *   From Clipboard: `python onefilellm.py --clipboard`

## Key Features

### Handling Multiple Input Sources

The tool can process and aggregate any number of different sources in a single command, including a mix of live inputs and pre-defined aliases. It processes inputs concurrently and combines the structured results into one XML document.

**Example:** Combine a local directory, a specific GitHub issue, and a documentation page.
```bash
python onefilellm.py ./src/ https://github.com/jimmc414/onefilellm/issues/1 https://react.dev/
```This allows for the creation of rich, multi-faceted contexts for an LLM.

### Creating Workflow Aliases

The aliasing system allows you to save and re-use complex data aggregation commands. This is useful for recurring tasks, such as gathering the context for a specific project or technology stack.

**Creating an Alias:**
The `--alias-add` command defines a new alias. The alias name is the first argument, followed by a space-separated list of sources.

```bash
# Alias for a project's key components
python onefilellm.py --alias-add project-context src/ docs/README.md https://github.com/user/project/issues

# Alias for an entire SDK (repository + documentation)
python onefilellm.py --alias-add vercel-ai-sdk https://github.com/vercel/ai https://sdk.vercel.ai/docs

# Alias for a technical specification (Model Context Protocol)
python onefilellm.py --alias-add mcp-spec https://modelcontextprotocol.io/llms-full.txt https://github.com/modelcontextprotocol/python-sdk
```

## Command-Line Interface (CLI)

This project can also be installed as a command-line tool, which allows you to run `onefilellm` directly from your terminal.

### CLI Installation

To install the CLI, run the following command in the project's root directory:

```bash
pip install -e .
```

This will install the package in "editable" mode, meaning any changes you make to the source code will be immediately available to the command-line tool.

### CLI Usage

Once installed, you can use the `onefilellm` command instead of `python onefilellm.py`.

**Synopsis:**
`onefilellm [OPTIONS] [INPUT_SOURCES...]`

**Example:**
```bash
onefilellm ./docs/ https://github.com/user/project/issues/123
```

All other command-line arguments and options work the same as the script-based approach.

**Using an Alias:**
You can then invoke an alias by its name.
```bash
python onefilellm.py project-context
```

**Aliases with Placeholders:**
Aliases can include a `{}` placeholder for dynamic input. This is useful for creating searchable shortcuts.

```bash
# Create an alias to search a GitHub organization
python onefilellm.py --alias-add search-msft "https://github.com/microsoft/{}"

# Use the alias with a search term
python onefilellm.py search-msft "terminal"
```

**Managing Aliases:**
*   `--alias-list`: View all defined aliases.
*   `--alias-remove <name>`: Remove a user-defined alias.

## Practical Use-Cases

1.  **Combining Multiple Aliases for Cross-Stack Analysis**
    Aggregate the context from several pre-defined aliases to analyze interactions between different technology stacks.
    ```bash
    # Prerequisite: Create aliases for each stack
    python onefilellm.py --alias-add k8s-stack https://github.com/kubernetes/kubernetes https://kubernetes.io/docs/
    python onefilellm.py --alias-add istio-stack https://github.com/istio/istio https://istio.io/latest/docs/

    # Combine aliases in a single command
    python onefilellm.py k8s-stack istio-stack
    ```
    *Outcome:* Provides an LLM with the source code and documentation for both Kubernetes and Istio, enabling questions about their integration, configuration, and comparative features.

2.  **In-depth and Respectful Documentation Crawling**
    Perform a deep crawl of a large documentation site while filtering noise and respecting the server's load.
    ```bash
    python onefilellm.py https://kubernetes.io/docs/concepts/ \
      --crawl-max-depth 5 \
      --crawl-restrict-path \
      --crawl-delay 0.5 \
      --crawl-exclude-pattern ".(jpg|png|svg)$"
    ```
    *Outcome:* Gathers a comprehensive snapshot of the Kubernetes concepts documentation.
    *   `--crawl-restrict-path`: Ensures the crawler does not leave the `/docs/concepts/` section.
    *   `--crawl-delay 0.5`: Adds a 500ms delay between requests to avoid overloading the server.
    *   `--crawl-exclude-pattern`: Prevents the crawler from downloading image files.

3.  **Aggregating Industry Specifications and SDKs**
    Gather the complete context for a technical standard by combining its specification file, reference implementation, and a related tool.
    ```bash
    # Prerequisite: Create an alias for the Model Context Protocol
    python onefilellm.py --alias-add mcp-spec https://modelcontextprotocol.io/llms-full.txt https://github.com/modelcontextprotocol/python-sdk

    # Combine the alias with another relevant SDK
    python onefilellm.py mcp-spec https://github.com/anthropics/anthropic-sdk-python
    ```
    *Outcome:* Creates a prompt context containing the MCP specification, its Python SDK, and the official Anthropic Python SDK, allowing for detailed analysis of implementation and compatibility.

4.  **Codebase Review with Full Context**
    Aggregate a local directory of code changes, a relevant GitHub Pull Request, and its corresponding issue to provide a complete context for code review.
    ```bash
    python onefilellm.py ./my-feature-branch/ https://github.com/user/repo/pull/42 https://github.com/user/repo/issues/35
    ```
    *Outcome:* Provides the LLM with the PR diff, discussion, related issue, and the current state of local code for a comprehensive review.

5.  **Pipeline Integration with other CLI tools**
    Use `onefilellm` as the data aggregation stage in a larger command-line workflow, piping its output to another LLM tool for analysis.
    ```bash
    python onefilellm.py k8s-stack | llm -m claude-3-opus "Summarize the key architectural patterns."
    ```
    *Outcome:* Demonstrates how the tool can function as a modular component in automated, script-driven AI workflows.

## Configuration

*   **Alias Storage:** User-defined aliases are stored in a JSON file located at `~/.onefilellm_aliases/aliases.json`. This file can be edited directly.
    ```json
    {
      "project-context": "src/ docs/README.md https://github.com/user/project/issues",
      "search-msft": "https://github.com/microsoft/{}",
      "mcp-spec": "https://modelcontextprotocol.io/llms-full.txt https://github.com/modelcontextprotocol/python-sdk"
    }
    ```
*   **Environment Variables:** For full functionality, especially with GitHub, the following environment variable is recommended:
    *   `GITHUB_TOKEN`: A GitHub Personal Access Token. Used to access private repositories and to avoid public API rate limits.
-----

old readme.md below

-----


# OneFileLLM: Efficient Data Aggregation for LLM Ingestion
OneFileLLM is a command-line tool designed to streamline the creation of information-dense prompts for large language models (LLMs). It aggregates and preprocesses data from a variety of sources, compiling them into a single text file that is automatically copied to your clipboard for quick use.

## Features

- Automatic source type detection based on provided path, URL, or identifier
- Support for local files and/or directories, GitHub repositories, GitHub pull requests, GitHub issues, academic papers from ArXiv, YouTube transcripts, web page documentation, Sci-Hub hosted papers via DOI or PMID
- Handling of multiple file formats, including Jupyter Notebooks (.ipynb), PDFs, and Excel files (.xls/.xlsx)
- Advanced asynchronous web crawling with extensive configuration options for depth, concurrency, content filtering, and robots.txt compliance
- Integration with Sci-Hub for automatic downloading of research papers using DOIs or PMIDs
- Text preprocessing, including compressed and uncompressed outputs, stopword removal, and lowercase conversion
- Automatic copying of uncompressed text to the clipboard for easy pasting into LLMs
- Token count reporting for both compressed and uncompressed outputs
- XML encapsulation of output for improved LLM performance
- Text stream input processing directly from stdin or clipboard
- Format detection and processing for plain text, Markdown, JSON, HTML, and YAML
- Format override option to control input processing
- Excel spreadsheet (.xls/.xlsx) processing to Markdown tables
- Alias system for frequently used sources
- Proper PDF text extraction from local files
- Cross-platform launcher scripts for easy execution

![image](https://github.com/jimmc414/1filellm/assets/6346529/73c24bcb-7be7-4b67-8591-3f1404b98fba)

## Installation

### Prerequisites

Install the required dependencies:

```bash
pip install -U -r requirements.txt
```

### GitHub Personal Access Token

To access private GitHub repositories, generate a personal access token as described in the 'Obtaining a GitHub Personal Access Token' section here: 

[Obtaining a GitHub Personal Access Token](https://github.com/jimmc414/onefilellm?tab=readme-ov-file#obtaining-a-github-personal-access-token)
### Setup

Clone the repository or download the source code.

## Usage

Run the script using the following command:

```bash
python onefilellm.py
```

![image](https://github.com/jimmc414/1filellm/assets/6346529/b4e281eb-8a41-4612-9d73-b2c115691013)


You can pass a single URL or path as a command line argument for faster processing:

```bash
python onefilellm.py https://github.com/jimmc414/1filellm
```

### Text Stream Processing

OneFileLLM now supports processing text directly from standard input (stdin) or the system clipboard:

#### Processing from Standard Input

Use the `-` argument to process text from standard input:

```bash
# Process text from a file via pipe
cat README.md | python onefilellm.py -

# Process output from another command
git diff | python onefilellm.py -
```

#### Processing from Clipboard

Use the `--clipboard` or `-c` argument to process text from the system clipboard:

```bash
# Copy text to clipboard first, then run:
python onefilellm.py --clipboard

# Or using the short form:
python onefilellm.py -c
```

#### Format Detection and Override

OneFileLLM automatically detects the format of input text (plain text, Markdown, JSON, HTML, YAML) and processes it accordingly. You can override this detection with the `--format` or `-f` option:

```bash
# Force processing as JSON
cat data.txt | python onefilellm.py - --format json

# Force processing clipboard content as Markdown 
python onefilellm.py --clipboard -f markdown
```

Supported format types: `text`, `markdown`, `json`, `html`, `yaml`, `doculing`, `markitdown`

### Multiple Inputs

OneFileLLM supports processing multiple inputs at once. Simply provide multiple paths or URLs as command line arguments:

```bash
python onefilellm.py https://github.com/jimmc414/1filellm test_file1.txt test_file2.txt
```

When multiple inputs are provided, OneFileLLM will:
1. Process each input separately according to its type
2. Combine all outputs into a single XML document with the `<onefilellm_output>` root tag
3. Save the combined output to `output.xml`
4. Copy the content to your clipboard for immediate use with LLMs

### Using Aliases

OneFileLLM includes a powerful alias system that allows you to create shortcuts for frequently used commands with support for placeholders and advanced management:

#### Managing Aliases

Create, list, and remove aliases using the new alias management commands:

```bash
# Add or update an alias
python onefilellm.py --alias-add myrepo "https://github.com/user/repo"

# Add alias with flags and options
python onefilellm.py --alias-add deepcrawl "https://docs.example.com --crawl-max-depth 4 --crawl-include-pattern '/docs/'"

# List all aliases (core and user-defined)
python onefilellm.py --alias-list

# List only pre-shipped core aliases
python onefilellm.py --alias-list-core

# Remove a user-defined alias
python onefilellm.py --alias-remove myrepo
```

#### Placeholder Support

Aliases support a `{}` placeholder that gets replaced with your input:

```bash
# Create alias with placeholder
python onefilellm.py --alias-add github_search "https://github.com/search?q={}"

# Use with replacement value
python onefilellm.py github_search "onefilellm"
# Expands to: https://github.com/search?q=onefilellm

# Create complex alias with multiple flags
python onefilellm.py --alias-add crawl_site "{} --crawl-max-depth 3 --crawl-respect-robots"

# Use it
python onefilellm.py crawl_site "https://docs.python.org"
# Expands to: https://docs.python.org --crawl-max-depth 3 --crawl-respect-robots
```

#### Core Aliases

OneFileLLM comes with useful pre-shipped aliases:

- `ofl_repo` - OneFileLLM GitHub repository
- `ofl_readme` - OneFileLLM README file  
- `gh_search` - GitHub search with placeholder: `https://github.com/search?q={}`
- `arxiv_search` - ArXiv search with placeholder

#### Alias Precedence and Storage

- **User aliases override core aliases** with the same name
- **JSON storage**: User aliases stored in `~/.onefilellm_aliases/aliases.json`
- **Robust error handling**: Graceful handling of missing or corrupted alias files
- **Validation**: Alias names must be alphanumeric with optional hyphens/underscores

#### Using Aliases

Use aliases just like any other input:

```bash
# Use a simple alias
python onefilellm.py ofl_repo

# Use alias with placeholder
python onefilellm.py gh_search "python"

# Mix aliases with direct inputs
python onefilellm.py ofl_repo local_file.txt

# Combine multiple aliases and arguments
python onefilellm.py ofl_repo github_search "machine learning" --format markdown
```

### Advanced Web Crawling

OneFileLLM features a powerful asynchronous web crawler with extensive configuration options for precise control over content extraction:

#### Basic Web Crawling

```bash
# Basic web crawl (default: 3 levels deep, up to 1000 pages)
python onefilellm.py https://docs.example.com

# Custom depth and page limits
python onefilellm.py https://example.com --crawl-max-depth 5 --crawl-max-pages 200
```

#### URL Pattern Filtering

```bash
# Include only specific URL patterns
python onefilellm.py https://docs.example.com --crawl-include-pattern "/docs/"

# Exclude specific patterns (CSS, JS, images)
python onefilellm.py https://example.com --crawl-exclude-pattern "\.(css|js|png|jpg|gif)$"

# Restrict crawling to paths under the start URL
python onefilellm.py https://example.com/docs --crawl-restrict-path
```

#### Content Control

```bash
# Include images and code blocks
python onefilellm.py https://example.com --crawl-include-images

# Exclude code blocks from output
python onefilellm.py https://example.com --crawl-no-include-code

# Disable heading extraction
python onefilellm.py https://example.com --crawl-no-extract-headings

# Include PDF files in crawl
python onefilellm.py https://example.com --crawl-include-pdfs

# Follow external links (default: stay on same domain)
python onefilellm.py https://example.com --crawl-follow-links
```

#### HTML Processing Options

```bash
# Disable readability cleaning (keep raw HTML structure)
python onefilellm.py https://example.com --crawl-no-clean-html

# Keep JavaScript and CSS code
python onefilellm.py https://example.com --crawl-no-strip-js --crawl-no-strip-css

# Keep HTML comments
python onefilellm.py https://example.com --crawl-no-strip-comments
```

#### Crawling Behavior

```bash
# Custom user agent
python onefilellm.py https://example.com --crawl-user-agent "MyBot/1.0"

# Delay between requests (seconds)
python onefilellm.py https://example.com --crawl-delay 1.0

# Request timeout (seconds)
python onefilellm.py https://example.com --crawl-timeout 30

# Concurrent requests (default: 3)
python onefilellm.py https://example.com --crawl-concurrency 5

# Respect robots.txt (default: ignore for backward compatibility)
python onefilellm.py https://example.com --crawl-respect-robots
```

#### Complete Advanced Example

```bash
# Comprehensive crawl with custom settings
python onefilellm.py https://docs.example.com \
  --crawl-max-depth 4 \
  --crawl-max-pages 500 \
  --crawl-include-pattern "/docs/|/api/" \
  --crawl-exclude-pattern "\.(pdf|zip|exe)$" \
  --crawl-include-images \
  --crawl-delay 0.5 \
  --crawl-concurrency 2 \
  --crawl-respect-robots \
  --crawl-restrict-path
```

#### Web Crawler Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--crawl-max-depth` | int | 3 | Maximum crawl depth from start URL |
| `--crawl-max-pages` | int | 1000 | Maximum number of pages to crawl |
| `--crawl-user-agent` | str | OneFileLLMCrawler/1.1 | User agent string for requests |
| `--crawl-delay` | float | 0.25 | Delay between requests in seconds |
| `--crawl-include-pattern` | str | None | Regex pattern for URLs to include |
| `--crawl-exclude-pattern` | str | None | Regex pattern for URLs to exclude |
| `--crawl-timeout` | int | 20 | Request timeout in seconds |
| `--crawl-include-images` | flag | False | Include image URLs in output |
| `--crawl-no-include-code` | flag | False | Exclude code blocks from output |
| `--crawl-no-extract-headings` | flag | False | Exclude heading extraction |
| `--crawl-follow-links` | flag | False | Follow links to external domains |
| `--crawl-no-clean-html` | flag | False | Disable readability cleaning |
| `--crawl-no-strip-js` | flag | False | Keep JavaScript code |
| `--crawl-no-strip-css` | flag | False | Keep CSS styles |
| `--crawl-no-strip-comments` | flag | False | Keep HTML comments |
| `--crawl-respect-robots` | flag | False | Respect robots.txt files |
| `--crawl-concurrency` | int | 3 | Number of concurrent requests |
| `--crawl-restrict-path` | flag | False | Restrict crawl to paths under start URL |
| `--crawl-no-include-pdfs` | flag | False | Skip PDF files during crawl |
| `--crawl-no-ignore-epubs` | flag | False | Include EPUB files in crawl |

### Expected Inputs and Resulting Outputs
The tool supports the following input options:

- Local file path (e.g., C:\documents\report.pdf)
- Local directory path (e.g., C:\projects\research) -> (files of selected filetypes segmented into one flat text file)
- GitHub repository URL (e.g., https://github.com/jimmc414/onefilellm) -> (Repo files of selected filetypes segmented into one flat text file)
- GitHub pull request URL (e.g., https://github.com/dear-github/dear-github/pull/102) -> (Pull request diff detail and comments and entire repository content concatenated into one flat text file)
- GitHub issue URL (e.g., https://github.com/isaacs/github/issues/1191) -> (Issue details, comments, and entire repository content concatenated into one flat text file)
- ArXiv paper URL (e.g., https://arxiv.org/abs/2401.14295) -> (Full paper PDF to text file)
- YouTube video URL (e.g., https://www.youtube.com/watch?v=KZ_NlnmPQYk) -> (Video transcript to text file)
- Webpage URL (e.g., https://llm.datasette.io/en/stable/) -> (To scrape pages to x depth in segmented text file)
- Sci-Hub Paper DOI (Digital Object Identifier of Sci-Hub hosted paper) (e.g., 10.1053/j.ajkd.2017.08.002) -> (Full Sci-Hub paper PDF to text file)
- Sci-Hub Paper PMID (PubMed Identifier of Sci-Hub hosted paper) (e.g., 29203127) -> (Full Sci-Hub paper PDF to text file)
- Standard input via pipe (e.g., `cat file.txt | python onefilellm.py -`)
- Clipboard content (e.g., `python onefilellm.py --clipboard`)

The tool supports the following input options, with their corresponding output actions. Note that the input file extensions are selected based on the following section of code (Applicable to Repos only):

```python
allowed_extensions = ['.xyz', '.pdq', '.example']
```

**The output for all options is encapsulated in LLM prompt-appropriate XML and automatically copied to the clipboard.**

1. **Local file path**
   - **Example Input:** `C:\documents\report.pdf`
   - **Output:** The contents of the PDF file are extracted and saved into a single text file.

2. **Local directory path**
   - **Example Input:** `C:\projects\research`
   - **Output:** Files of selected file types within the directory are segmented and saved into a single flat text file.

3. **GitHub repository URL**
   - **Example Input:** `https://github.com/jimmc414/onefilellm`
   - **Output:** Repository files of selected file types are segmented and saved into a single flat text file.

4. **GitHub pull request URL**
   - **Example Input:** `https://github.com/dear-github/dear-github/pull/102`
   - **Output:** Pull request diff details, comments, and the entire repository content are concatenated into a single flat text file.

5. **GitHub issue URL**
   - **Example Input:** `https://github.com/isaacs/github/issues/1191`
   - **Output:** Issue details, comments, and the entire repository content are concatenated into a single flat text file.

6. **ArXiv paper URL**
   - **Example Input:** `https://arxiv.org/abs/2401.14295`
   - **Output:** The full paper PDF is converted into a text file.

7. **YouTube video URL**
   - **Example Input:** `https://www.youtube.com/watch?v=KZ_NlnmPQYk`
   - **Output:** The video transcript is extracted and saved into a text file.

8. **Webpage URL**
   - **Example Input:** `https://llm.datasette.io/en/stable/`
   - **Output:** The webpage content and linked pages up to a specified depth are scraped and segmented into a text file.

9. **Sci-Hub Paper DOI**
   - **Example Input:** `10.1053/j.ajkd.2017.08.002`
   - **Output:** The full Sci-Hub paper PDF is converted into a text file.

10. **Sci-Hub Paper PMID**
    - **Example Input:** `29203127`
    - **Output:** The full Sci-Hub paper PDF is converted into a text file.

11. **Standard Input**
    - **Example Input:** `cat file.txt | python onefilellm.py -`
    - **Output:** The piped text content is processed according to its detected format (or format override).

12. **Clipboard**
    - **Example Input:** `python onefilellm.py --clipboard`
    - **Output:** The clipboard text content is processed according to its detected format (or format override).

The script generates the following output files:

- `output.xml`: The full XML-structured output, automatically copied to the clipboard.
- `compressed_output.txt`: Cleaned and compressed text (when NLTK processing is enabled).
- `processed_urls.txt`: A list of all processed URLs during web crawling.

## Configuration

### File Type Configuration

To modify the allowed file types for repository processing, update the `allowed_extensions` list in the code:

```python
allowed_extensions = ['.py', '.txt', '.js', '.rst', '.sh', '.md', '.pyx', '.html', '.yaml','.json', '.jsonl', '.ipynb', '.h', '.c', '.sql', '.csv']
```

### Web Crawling Configuration

Web crawling behavior is now controlled through command-line arguments rather than hardcoded values. You can configure:

- **Crawl depth**: Use `--crawl-max-depth N` (default: 3)
- **Page limits**: Use `--crawl-max-pages N` (default: 1000)  
- **URL filtering**: Use `--crawl-include-pattern` and `--crawl-exclude-pattern`
- **Content processing**: Use flags like `--crawl-include-images`, `--crawl-no-include-code`
- **Request behavior**: Use `--crawl-delay`, `--crawl-timeout`, `--crawl-concurrency`
- **Domain restrictions**: Use `--crawl-follow-links`, `--crawl-restrict-path`
- **Robots.txt compliance**: Use `--crawl-respect-robots`

### Environment Variables

The tool supports environment variables for configuration:

- **GITHUB_TOKEN**: Set your GitHub personal access token for private repository access
- **RUN_INTEGRATION_TESTS**: Set to `true` to enable integration tests
- **RUN_SLOW_TESTS**: Set to `true` to enable slow tests

You can also use a `.env` file in the project root directory to set these variables:

```bash
# .env file
GITHUB_TOKEN=your_github_token_here
RUN_INTEGRATION_TESTS=false
RUN_SLOW_TESTS=false
```

## Obtaining a GitHub Personal Access Token

To access private GitHub repositories, you need a personal access token. Follow these steps:

1. Log in to your GitHub account and go to Settings.
2. Navigate to Developer settings > Personal access tokens.
3. Click on "Generate new token" and provide a name.
4. Select the necessary scopes (at least `repo` for private repositories).
5. Click "Generate token" and copy the token value.

In the `onefilellm.py` script, replace `GITHUB_TOKEN` with your actual token or set it as an environment variable:

- For Windows:
  ```shell
  setx GITHUB_TOKEN "YourGitHubToken"
  ```

- For Linux:
  ```shell
  echo 'export GITHUB_TOKEN="YourGitHubToken"' >> ~/.bashrc
  source ~/.bashrc
  ```

## XML Output Format

All output is encapsulated in XML tags. This structure was implemented based on evaluations showing that LLMs perform better with prompts structured in XML. The general structure of the output is as follows:

### Single Source Output

```xml
<onefilellm_output>
  <source type="[source_type]" [additional_attributes]>
    <[content_type]>
      [Extracted content]
    </[content_type]>
  </source>
</onefilellm_output>
```

### Multiple Sources Output

```xml
<onefilellm_output>
  <source type="[source_type_1]" [additional_attributes]>
    <[content_type]>
      [Extracted content 1]
    </[content_type]>
  </source>
  <source type="[source_type_2]" [additional_attributes]>
    <[content_type]>
      [Extracted content 2]
    </[content_type]>
  </source>
  <!-- Additional sources as needed -->
</onefilellm_output>
```

Where `[source_type]` could be one of: "github_repository", "github_pull_request", "github_issue", "arxiv_paper", "youtube_transcript", "web_documentation", "sci_hub_paper", "local_directory", "local_file", "stdin", or "clipboard".

This XML structure provides clear delineation of different content types and sources, improving the LLM's understanding and processing of the input.


## Data Flow Diagram

```
                                 +--------------------------------+
                                 |      External Services         |
                                 |--------------------------------|
                                 |  GitHub API  | YouTube API     |
                                 |  Sci-Hub     | ArXiv           |
                                 +--------------------------------+
                                           |
                                           |
                                           v
 +----------------------+          +---------------------+         +----------------------+
 |                      |          |                     |         |                      |
 |        User          |          |  Command Line Tool  |         |  External Libraries  |
 |----------------------|          |---------------------|         |----------------------|
 | - Provides input URL |--------->| - Handles user input|         | - Requests           |
 | - Provides text via  |          | - Detects source    |<--------| - BeautifulSoup      |
 |   pipe or clipboard  |          |   type              |         | - PyPDF2             |
 | - Receives text      |          | - Calls appropriate |         | - Tiktoken           |
 |   in clipboard       |<---------| - processing modules|         | - NLTK               |
 |                      |          | - Preprocesses text |         | - Nbformat           |
 +----------------------+          | - Generates output  |         | - Nbconvert          |
                                   |   files             |         | - YouTube Transcript |
                                   | - Copies text to    |         |   API                |
                                   |   clipboard         |         | - Pyperclip          |
                                   | - Reports token     |         | - Wget               |
                                   |   count             |         | - Tqdm               |
                                   +---------------------+         | - Rich               |
                                           |                       | - PyYAML             |
                                           |                       +----------------------+
                                           v
                                    +---------------------+
                                    | Source Type         |
                                    | Detection           |
                                    |---------------------|
                                    | - Determines type   |
                                    |   of source         |
                                    +---------------------+
                                           |
                                           v
                                    +---------------------+
                                    | Processing Modules  |
                                    |---------------------|
                                    | - GitHub Repo Proc  |
                                    | - Local Dir Proc    |
                                    | - YouTube Transcript|
                                    |   Proc              |
                                    | - ArXiv PDF Proc    |
                                    | - Sci-Hub Paper Proc|
                                    | - Webpage Crawling  |
                                    |   Proc              |
                                    | - Text Stream Proc  |
                                    +---------------------+
                                           |
                                           v
                                    +---------------------+
                                    | Text Preprocessing  |
                                    |---------------------|
                                    | - Stopword removal  |
                                    | - Lowercase         |
                                    |   conversion        |
                                    | - Text cleaning     |
                                    +---------------------+
                                           |
                                           v
                                    +---------------------+
                                    | Output Generation   |
                                    |---------------------|
                                    | - Compressed text   |
                                    |   file output       |
                                    | - Uncompressed text |
                                    |   file output       |
                                    +---------------------+
                                           |
                                           v
                                    +---------------------+
                                    | Token Count         |
                                    | Reporting           |
                                    |---------------------|
                                    | - Report token count|
                                    |                     |
                                    | - Copies text to    |
                                    |   clipboard         |
                                    +---------------------+
```



## Recent Changes

- **2025-06-01:**
  - **Major Enhancement: Alias Management 2.0**: Complete overhaul of the alias system
  - Added powerful new alias management with JSON-based storage (`~/.onefilellm_aliases/aliases.json`)
  - Implemented placeholder support using `{}` token for dynamic command substitution
  - Added new CLI commands: `--alias-add`, `--alias-remove`, `--alias-list`, `--alias-list-core`
  - Created pre-shipped core aliases (ofl_repo, ofl_readme, gh_search, arxiv_search)
  - Added user alias precedence over core aliases for customization
  - Implemented early alias expansion before argument parsing for proper command-line integration
  - Enhanced alias validation and robust error handling for missing/corrupted files
  - Replaced old file-per-alias system with centralized JSON management

- **2025-05-30:**
  - **Major Enhancement**: Implemented advanced asynchronous web crawler with extensive configuration options
  - Added 19 new command-line switches for web crawling control (`--crawl-*` options)
  - Integrated structured content extraction with support for headings, code blocks, tables, and images
  - Added robots.txt compliance, concurrent request control, and URL pattern filtering
  - Implemented python-dotenv support for environment variable management
  - Enhanced test suite with 57 comprehensive tests covering GitHub Issues/PRs, advanced web crawling, and multiple input processing
  - Converted core functionality to async/await architecture for improved performance

- **2025-05-14:**
  - Added text stream input processing directly from stdin or clipboard
  - Implemented format detection for plain text, Markdown, JSON, HTML, and YAML
  - Added format override option with `--format TYPE` or `-f TYPE` flags
  - Updated help messages and error handling for stream processing
  - Added comprehensive test suite for stream processing features

- **2025-05-10:**
  - Added Excel spreadsheet (.xls/.xlsx) processing with conversion to Markdown tables
  - Support for both local Excel files and Excel files via URL
  - Each sheet in an Excel workbook is converted to a separate Markdown table
  - Added intelligent header detection for tables with varying formats

- **2025-05-07:**
  - Added alias management system for frequently used sources
  - Added legacy alias management system (replaced by Alias Management 2.0)
  - Fixed PDF text extraction for local PDF files
  - Changed root XML tag from `<combined_sources>` to `<onefilellm_output>`
  - Added cross-platform launcher scripts for Windows and Linux/macOS
  - Improved user feedback during alias operations

- **2025-05-03:**
  - Added support for processing multiple inputs as command line arguments
  - Implemented functionality to combine multiple outputs into a cohesive XML document
  - Refactored code to improve modularity and reusability
  - Added test files to demonstrate multi-input capabilities

- **2025-01-20:**
  - Added file and directory exclusion functionality to reduce context window usage
  - Added ability to exclude auto-generated files (*.pb.go, etc.)
  - Added ability to exclude mock files and test directories
  - Updated documentation with exclusion configuration instructions
- **2025-01-17:**
  - Added ability to exclude specific directories from processing
  - Updated directory traversal logic to respect exclusion rules
- **2024-07-29:**
  - Updated output format to encapsulate content in XML tags. This change was implemented due to evaluations showing that LLMs perform better with prompts structured in XML.
  - Added tests for GitHub issues and GitHub pull requests to improve robustness and reliability.
  - Updated various processing functions to return formatted content instead of writing directly to files, improving consistency and testability.
- **2024-05-17:** Added ability to pass path or URL as command line argument.
- **2024-05-16:** Updated text colors.
- **2024-05-11:** 
  - Updated requirements.txt.
  - Added Rich library to `onefilellm.py`.
- **2024-04-04:**
  - Added GitHub PR and issue tests.
  - Added GitHub PR and issues.
  - Added tests for GitHub PRs and issues.
  - Added ability to concatenate specific GitHub issue and repo when GitHub issue URL is passed.
  - Updated tests to include pull request changes.
  - Added ability to concatenate pull request and repo when GitHub pull request URL is passed.
- **2024-04-03:**
  - Included the ability to pull a complete GitHub pull request given the GitHub pull request URL.
  - Updated `onefilellm.py` to return an error when Sci-hub is inaccessible or no document is found.


## Notes

### Repository Processing
- **File types**: Modify the `allowed_extensions` list in the code to add or remove file types:
  ```python
  allowed_extensions = ['.py', '.txt', '.js', '.rst', '.sh', '.md', '.pyx', '.html', '.yaml','.json', '.jsonl', '.ipynb', '.h', '.c', '.sql', '.csv']
  ```
- **File exclusion**: Modify the `excluded_patterns` list to customize which files are filtered out
- **Directory exclusion**: Modify the `EXCLUDED_DIRS` list to customize which directories are skipped

### Web Crawling
- **Crawl depth**: Use `--crawl-max-depth N` command-line option (default: 3)
- **Page limits**: Use `--crawl-max-pages N` command-line option (default: 1000)
- **URL filtering**: Use `--crawl-include-pattern` and `--crawl-exclude-pattern` for precise control
- **Content control**: Use various `--crawl-*` flags for images, code blocks, headings, etc.
- **Performance**: Use `--crawl-concurrency N` and `--crawl-delay X` for request management
- **Compliance**: Use `--crawl-respect-robots` to honor robots.txt files

### General
- Token counts are displayed in the console for both output files
- Environment variables can be set via `.env` file for easier configuration
- All web crawling configuration is now done via command-line arguments rather than code modification

