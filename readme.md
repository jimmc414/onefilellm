# OneFileLLM

Content Aggregator for LLMs - Aggregate and structure multi-source data into a single XML file for LLM context.

## Description

OneFileLLM is a command-line tool that automates data aggregation from various sources (local files, GitHub repos, web pages, PDFs, YouTube transcripts, etc.) and combines them into a single, structured XML output that's automatically copied to your clipboard for use with Large Language Models.

## Installation

```bash
git clone https://github.com/jimmc414/onefilellm.git
cd onefilellm
pip install -r requirements.txt
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

For GitHub API access (recommended):

```bash
export GITHUB_TOKEN="your_personal_access_token"
```

## Command Help

```
usage: onefilellm.py [-h] [-c]
                     [-f {text,markdown,json,html,yaml,doculing,markitdown}]
                     [--alias-add NAME [COMMAND_STRING ...]]
                     [--alias-remove NAME] [--alias-list] [--alias-list-core]
                     [--crawl-max-depth CRAWL_MAX_DEPTH]
                     [--crawl-max-pages CRAWL_MAX_PAGES]
                     [--crawl-user-agent CRAWL_USER_AGENT]
                     [--crawl-delay CRAWL_DELAY]
                     [--crawl-include-pattern CRAWL_INCLUDE_PATTERN]
                     [--crawl-exclude-pattern CRAWL_EXCLUDE_PATTERN]
                     [--crawl-timeout CRAWL_TIMEOUT] [--crawl-include-images]
                     [--crawl-no-include-code] [--crawl-no-extract-headings]
                     [--crawl-follow-links] [--crawl-no-clean-html]
                     [--crawl-no-strip-js] [--crawl-no-strip-css]
                     [--crawl-no-strip-comments] [--crawl-respect-robots]
                     [--crawl-concurrency CRAWL_CONCURRENCY]
                     [--crawl-restrict-path] [--crawl-no-include-pdfs]
                     [--crawl-no-ignore-epubs] [--help-topic [TOPIC]]
                     [inputs ...]

OneFileLLM - Content Aggregator for LLMs

positional arguments:
  inputs                Input paths, URLs, or aliases to process

options:
  -h, --help            show this help message and exit
  -c, --clipboard       Process text from clipboard
  -f {text,markdown,json,html,yaml,doculing,markitdown}, --format {text,markdown,json,html,yaml,doculing,markitdown}
                        Override format detection for text input
  --help-topic [TOPIC]  Show help for specific topic (basic, aliases,
                        crawling, pipelines, examples, config)

## Quick Start Examples

### Local Files and Directories
```bash
python onefilellm.py research_paper.pdf config.yaml src/
python onefilellm.py *.py requirements.txt docs/ README.md
python onefilellm.py notebook.ipynb --format json
python onefilellm.py large_dataset.csv logs/ --format text
```

### GitHub Repositories and Issues
```bash
python onefilellm.py https://github.com/microsoft/vscode
python onefilellm.py https://github.com/openai/whisper/tree/main/whisper
python onefilellm.py https://github.com/microsoft/vscode/pull/12345
python onefilellm.py https://github.com/kubernetes/kubernetes/issues
```

### Web Documentation and APIs
```bash
python onefilellm.py https://docs.python.org/3/tutorial/
python onefilellm.py https://react.dev/learn/thinking-in-react
python onefilellm.py https://docs.stripe.com/api
python onefilellm.py https://kubernetes.io/docs/concepts/
```

### Multimedia and Academic Sources
```bash
python onefilellm.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
python onefilellm.py https://arxiv.org/abs/2103.00020
python onefilellm.py arxiv:1706.03762 PMID:35177773
python onefilellm.py doi:10.1038/s41586-021-03819-2
```

### **Multiple Inputs**
```bash
python onefilellm.py https://github.com/jimmc414/hey-claude https://modelcontextprotocol.io/llms-full.txt https://github.com/anthropics/anthropic-sdk-python https://github.com/anthropics/anthropic-cookbook
python onefilellm.py https://github.com/openai/whisper/tree/main/whisper https://www.youtube.com/watch?v=dQw4w9WgXcQ ALIAS_MCP
python onefilellm.py https://github.com/microsoft/vscode/pull/12345 https://arxiv.org/abs/2103.00020 
python onefilellm.py https://github.com/kubernetes/kubernetes/issues https://pytorch.org/docs
```

### Input Streams
```bash
python onefilellm.py --clipboard --format markdown
cat large_dataset.json | python onefilellm.py - --format json
curl -s https://api.github.com/repos/microsoft/vscode | python onefilellm.py -
echo 'Quick analysis task' | python onefilellm.py -
```

## Alias System

### Create Simple and Complex Aliases
```bash
python onefilellm.py --alias-add mcp "https://github.com/anthropics/mcp"
python onefilellm.py --alias-add modern-web \
  "https://github.com/facebook/react https://reactjs.org/docs/ https://github.com/vercel/next.js"
```

### Dynamic Placeholders
```bash
# Create placeholders with {}
python onefilellm.py --alias-add gh-search "https://github.com/search?q={}"
python onefilellm.py --alias-add gh-user "https://github.com/{}"
python onefilellm.py --alias-add arxiv-search "https://arxiv.org/search/?query={}"

# Use placeholders dynamically
python onefilellm.py gh-search "machine learning transformers"
python onefilellm.py gh-user "microsoft"
python onefilellm.py arxiv-search "attention mechanisms"
```

### Complex Ecosystem Aliases
```bash
python onefilellm.py --alias-add ai-research \
  "arxiv:1706.03762 https://github.com/huggingface/transformers https://pytorch.org/docs"
python onefilellm.py --alias-add k8s-ecosystem \
  "https://github.com/kubernetes/kubernetes https://kubernetes.io/docs/ https://github.com/istio/istio"

# Combine multiple aliases with live sources
python onefilellm.py ai-research k8s-ecosystem modern-web \
  conference_notes.pdf local_experiments/
```

### Alias Management
```bash
python onefilellm.py --alias-list              # Show all aliases
python onefilellm.py --alias-list-core         # Show core aliases only
python onefilellm.py --alias-remove old-alias  # Remove user alias
cat ~/.onefilellm_aliases/aliases.json         # View raw JSON

  --alias-add NAME [COMMAND_STRING ...]
                        Add or update a user-defined alias. Multiple arguments
                        after NAME will be joined as COMMAND_STRING.
  --alias-remove NAME   Remove a user-defined alias.
  --alias-list          List all effective aliases (user-defined aliases
                        override core aliases).
  --alias-list-core     List only pre-shipped (core) aliases.

Web Crawler Options:
  --crawl-max-depth CRAWL_MAX_DEPTH
                        Maximum crawl depth (default: 3)
  --crawl-max-pages CRAWL_MAX_PAGES
                        Maximum pages to crawl (default: 1000)
  --crawl-user-agent CRAWL_USER_AGENT
                        User agent for web requests (default:
                        OneFileLLMCrawler/1.1)
  --crawl-delay CRAWL_DELAY
                        Delay between requests in seconds (default: 0.25)
  --crawl-include-pattern CRAWL_INCLUDE_PATTERN
                        Regex pattern for URLs to include
  --crawl-exclude-pattern CRAWL_EXCLUDE_PATTERN
                        Regex pattern for URLs to exclude
  --crawl-timeout CRAWL_TIMEOUT
                        Request timeout in seconds (default: 20)
  --crawl-include-images
                        Include image URLs in output
  --crawl-no-include-code
                        Exclude code blocks from output
  --crawl-no-extract-headings
                        Exclude heading extraction
  --crawl-follow-links  Follow links to external domains
  --crawl-no-clean-html
                        Disable readability cleaning
  --crawl-no-strip-js   Keep JavaScript code
  --crawl-no-strip-css  Keep CSS styles
  --crawl-no-strip-comments
                        Keep HTML comments
  --crawl-respect-robots
                        Respect robots.txt (default: ignore for backward
                        compatibility)
  --crawl-concurrency CRAWL_CONCURRENCY
                        Number of concurrent requests (default: 3)
  --crawl-restrict-path
                        Restrict crawl to paths under start URL
  --crawl-no-include-pdfs
                        Skip PDF files
  --crawl-no-ignore-epubs
                        Include EPUB files
```

## Advanced Web Crawling

### Comprehensive Documentation Sites
```bash
python onefilellm.py https://docs.python.org/3/ \
  --crawl-max-depth 4 --crawl-max-pages 800 \
  --crawl-include-pattern ".*/(tutorial|library|reference)/" \
  --crawl-exclude-pattern ".*/(whatsnew|faq)/"
```

### Enterprise API Documentation
```bash
python onefilellm.py https://docs.aws.amazon.com/ec2/ \
  --crawl-max-depth 3 --crawl-max-pages 500 \
  --crawl-include-pattern ".*/(UserGuide|APIReference)/" \
  --crawl-respect-robots --crawl-delay 0.5
```

### Academic and Research Sites
```bash
python onefilellm.py https://arxiv.org/list/cs.AI/recent \
  --crawl-max-depth 2 --crawl-max-pages 100 \
  --crawl-include-pattern ".*/(abs|pdf)/" \
  --crawl-include-pdfs --crawl-delay 1.0
```

## Integration with LLM Tools

### Multi-stage Research Analysis
```bash
python onefilellm.py ai-research protein-folding | \
  llm -m claude-3-haiku "Extract key methodologies and datasets" | \
  llm -m claude-3-sonnet "Identify experimental approaches" | \
  llm -m gpt-4o "Compare methodologies across papers" | \
  llm -m claude-3-opus "Generate novel research directions"
```

### Competitive Analysis Automation
```bash
python onefilellm.py \
  https://github.com/competitor1/product \
  https://competitor1.com/docs/ \
  https://competitor2.com/api/ | \
  llm -m claude-3-haiku "Extract features and capabilities" | \
  llm -m gpt-4o "Compare and identify gaps" | \
  llm -m claude-3-opus "Generate strategic recommendations"
```

### Daily Research Monitoring (cron job)
```bash
0 9 * * * python onefilellm.py \
  https://arxiv.org/list/cs.AI/recent \
  https://arxiv.org/list/cs.LG/recent | \
  llm -m claude-3-haiku "Extract significant papers" | \
  llm -m claude-3-sonnet "Summarize key developments" | \
  mail -s "Daily AI Research Brief" researcher@company.com
```

## Output Format

All output is encapsulated in XML for better LLM processing:

```xml
<onefilellm_output>
  <source type="[source_type]" [additional_attributes]>
    <[content_type]>
      [Extracted content]
    </[content_type]>
  </source>
</onefilellm_output>
```

## Supported Input Types

- **Local**: Files and directories
- **GitHub**: Repositories, issues, pull requests  
- **Web**: Pages with advanced crawling options
- **Academic**: ArXiv papers, DOIs, PMIDs
- **Multimedia**: YouTube transcripts
- **Streams**: stdin, clipboard

## Core Aliases

- `ofl_repo` - OneFileLLM GitHub repository
- `ofl_readme` - OneFileLLM README file
- `gh_search` - GitHub search with placeholder
- `arxiv_search` - ArXiv search with placeholder

## Configuration

- **Alias Storage**: `~/.onefilellm_aliases/aliases.json`
- **Environment Variables**: 
  - `GITHUB_TOKEN` - GitHub API access token
  - Can use `.env` file in project root

## Additional Help

```bash
python onefilellm.py --help-topic basic      # Input sources and basic usage
python onefilellm.py --help-topic aliases    # Alias system with real examples
python onefilellm.py --help-topic crawling   # Web crawler patterns and ethics
python onefilellm.py --help-topic pipelines  # 'llm' tool integration workflows
python onefilellm.py --help-topic examples   # Advanced usage patterns
python onefilellm.py --help-topic config     # Environment and configuration
```

