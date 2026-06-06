# Changelog

All notable changes to **onefilellm** are documented here.

This project has never carried version tags, so releases cannot be enumerated. Instead, entries are **grouped by month in reverse-chronological order** (newest first). Within each month, changes are sorted by category: Security, Added, Changed, Fixed, Removed, Docs, Internal.

The format follows the spirit of [Keep a Changelog](https://keepachangelog.com). Each entry links to the commit (and pull request, where one exists) on GitHub. The project began in March 2023 as a small repo-to-text helper (`onefilerepo.py`), was rewritten as `1filellm.py` in early 2024, and was renamed to the current `onefilellm.py` in March 2024; the history below spans 294 commits from 2023-03 through 2026-06.

---

## 2026-06

### Fixed
- Repair YouTube transcript fetching broken by yt-dlp and transcript-api changes ([`978de2c`](https://github.com/jimmc414/onefilellm/commit/978de2c)) — Reworks the yt-dlp path (auto/manual subs, `en,en-orig` sub-langs, srt conversion, node js-runtime with retry, glob-based subtitle discovery, exit-code-independent file scanning, dedup of rolling captions) and migrates the `youtube_transcript_api` fallback to the v1.x instance API. Bumps `youtube-transcript-api` pin from 0.4.1 to `>=1.1.0,<2` and reports both failures when both paths fail.

## 2026-02

### Security
- **Breaking:** Fix 39 defects from a comprehensive security and code-quality audit ([`99c51a2`](https://github.com/jimmc414/onefilellm/commit/99c51a2)) — Web app: fixes path traversal in `/download`, blocks local-path processing, disables debug mode, and binds to localhost only. Only sends the GitHub token to `github.com` domains; wraps crawl regexes for ReDoS safety; caps issue fetching at 500 and adds 50MB crawler response limits; paginates all comment fetching; adds asyncio locking and `ClientTimeout` to the async crawler. Also fixes a mutable-default arg in `get_token_count`, alias listing of overridden core aliases, UTF-8 encoding detection, ArXiv URL query stripping, and an `is_within_depth` off-by-one.

## 2025-09

### Added
- Add offline mode and proxy-safe HTTP requests ([`2fe62b1`](https://github.com/jimmc414/onefilellm/commit/2fe62b1), [#46](https://github.com/jimmc414/onefilellm/pull/46)) — Introduces an `OFFLINE_MODE` environment flag (set to 1) that skips all network operations, and makes requests respect system proxy settings with error handling.
- Add bulk GitHub issue download for an entire repository ([`ccab710`](https://github.com/jimmc414/onefilellm/commit/ccab710), [#52](https://github.com/jimmc414/onefilellm/pull/52)) — A repository issues URL (e.g. `.../issues`) now fetches all issues with comments via paginated API calls; supports an optional state query parameter (open/closed/all, default all) and appends repo content once at the end.
- Add programmatic Python API via `onefilellm.run()` ([`2e32aaa`](https://github.com/jimmc414/onefilellm/commit/2e32aaa), [#54](https://github.com/jimmc414/onefilellm/pull/54)) — Inputs can now be processed from Python code by importing `run()` from `onefilellm`, alongside the CLI; README documents pip install and the API.
- Allow PDF and YAML/YML files to be processed ([`a438567`](https://github.com/jimmc414/onefilellm/commit/a438567), [#67](https://github.com/jimmc414/onefilellm/pull/67)) — Extends filetype detection to accept PDF and YAML inputs.
- Allow CSS files to be processed ([`6c5de3c`](https://github.com/jimmc414/onefilellm/commit/6c5de3c), [#73](https://github.com/jimmc414/onefilellm/pull/73)) — Fixes issue #72 by adding CSS to the accepted filetypes.

### Changed
- Upgrade requests dependency to support urllib3 v2 ([`f7da140`](https://github.com/jimmc414/onefilellm/commit/f7da140), [#49](https://github.com/jimmc414/onefilellm/pull/49))
- Auto-detect piped stdin input and honor format overrides ([`8dcafdc`](https://github.com/jimmc414/onefilellm/commit/8dcafdc), [#51](https://github.com/jimmc414/onefilellm/pull/51)) — When no inputs are given and stdin is not a TTY, content is now read from stdin automatically (in addition to the explicit `-` argument), and the `--format` override is applied to stream input.
- Stream file downloads and improve download error handling ([`6013367`](https://github.com/jimmc414/onefilellm/commit/6013367), [#56](https://github.com/jimmc414/onefilellm/pull/56)) — `download_file` now streams content rather than buffering whole responses, with improved error reporting.
- Add offline-mode guards to network helper functions ([`4da6aa1`](https://github.com/jimmc414/onefilellm/commit/4da6aa1), [#57](https://github.com/jimmc414/onefilellm/pull/57)) — Network helper functions now short-circuit when `OFFLINE_MODE` is enabled.
- Normalize DOI/PMID inputs with `doi:`/`pmid:` prefixes ([`6d38eae`](https://github.com/jimmc414/onefilellm/commit/6d38eae), [#70](https://github.com/jimmc414/onefilellm/pull/70)) — Inputs like `doi:10.x/...` or `pmid: 12345` are now stripped of their prefix before DOI/PMID detection and processing.
- Respect offline mode in the web crawler ([`bde4eb2`](https://github.com/jimmc414/onefilellm/commit/bde4eb2), [#71](https://github.com/jimmc414/onefilellm/pull/71)) — The web crawl path now honors `OFFLINE_MODE` and skips network access.

### Fixed
- Add offline token-counting fallback when tiktoken cannot fetch encodings ([`87a2636`](https://github.com/jimmc414/onefilellm/commit/87a2636), [#50](https://github.com/jimmc414/onefilellm/pull/50)) — Token counting no longer fails in offline/air-gapped environments where tiktoken cannot download its encoding files.
- Add timeouts and error handling to HTTP requests ([`1425b85`](https://github.com/jimmc414/onefilellm/commit/1425b85), [#55](https://github.com/jimmc414/onefilellm/pull/55)) — Network requests now use explicit timeouts and handle failures gracefully to prevent hangs.
- Use tempfile for unique download paths ([`6d89e39`](https://github.com/jimmc414/onefilellm/commit/6d89e39), [#59](https://github.com/jimmc414/onefilellm/pull/59)) — Downloads now use tempfile to avoid filename collisions and ensure cleanup.
- Handle yt-dlp subprocess failures when fetching YouTube transcripts ([`4c71e72`](https://github.com/jimmc414/onefilellm/commit/4c71e72), [#61](https://github.com/jimmc414/onefilellm/pull/61)) — Inspects the yt-dlp subprocess return code and surfaces an error instead of proceeding on failure.
- Handle YouTube live, shorts, and embed URL formats ([`8f0d047`](https://github.com/jimmc414/onefilellm/commit/8f0d047), [#64](https://github.com/jimmc414/onefilellm/pull/64)) — Video ID extraction was rewritten to robustly parse `youtu.be`, `watch?v=`, `embed/`, `v/`, `shorts/`, and `live/` URL forms with 11-char ID validation.
- Load `.env` configuration before computing runtime globals ([`650d501`](https://github.com/jimmc414/onefilellm/commit/650d501), [#65](https://github.com/jimmc414/onefilellm/pull/65)) — Ensures values like `GITHUB_TOKEN` and `OFFLINE_MODE` from `.env` are applied before module-level globals are derived from them.
- Forward auth headers on GitHub file downloads ([`017bc95`](https://github.com/jimmc414/onefilellm/commit/017bc95), [#66](https://github.com/jimmc414/onefilellm/pull/66)) — `download_file` now accepts and sends auth headers so GitHub downloads work for private/rate-limited content.
- Handle missing PyYAML during text stream parsing ([`2a56375`](https://github.com/jimmc414/onefilellm/commit/2a56375), [#69](https://github.com/jimmc414/onefilellm/pull/69)) — Stream parsing no longer crashes when PyYAML is not installed.

### Docs
- Document GitHub issue states and branch usage ([`cb6b0dc`](https://github.com/jimmc414/onefilellm/commit/cb6b0dc), [#53](https://github.com/jimmc414/onefilellm/pull/53))

### Internal
- Restore `ALIAS_DIR` constant and update tests ([`fe350e3`](https://github.com/jimmc414/onefilellm/commit/fe350e3), [#44](https://github.com/jimmc414/onefilellm/pull/44)) — Reintroduces the alias directory constant that downstream code/tests depend on.
- Thread the existing Rich console through `process_input` ([`9a305fa`](https://github.com/jimmc414/onefilellm/commit/9a305fa), [#58](https://github.com/jimmc414/onefilellm/pull/58))
- Pass console parameter into local folder processing ([`38c5653`](https://github.com/jimmc414/onefilellm/commit/38c5653), [#60](https://github.com/jimmc414/onefilellm/pull/60))
- Simplify URL filetype detection logic and add tests ([`539869b`](https://github.com/jimmc414/onefilellm/commit/539869b), [#62](https://github.com/jimmc414/onefilellm/pull/62))
- Set `sys.path` before importing repository modules in tests ([`14408c3`](https://github.com/jimmc414/onefilellm/commit/14408c3), [#68](https://github.com/jimmc414/onefilellm/pull/68))

_Several of the 2025-09-12/13 PRs (#46, #50, #55, #56, #57, #65, #69, #71) form a coordinated offline-mode and network-robustness hardening sweep; they are listed individually above but are thematically related. Merge PR #48 added a trailing newline to `cli.py` (whitespace only). Plus minor README/docs wording tweaks accompanying the feature commits._

## 2025-07

### Internal
- Lazy-load heavy imports to cut startup time from ~2.2s to ~1.0s ([`e70fec7`](https://github.com/jimmc414/onefilellm/commit/e70fec7), [#41](https://github.com/jimmc414/onefilellm/pull/41)) — Defers heavy module imports until needed, roughly halving cold startup time.

## 2025-06

### Added
- Add Alias Management 2.0 with JSON storage, placeholders, and core aliases ([`742fe55`](https://github.com/jimmc414/onefilellm/commit/742fe55)) — New `--alias-add`/`--alias-remove`/`--alias-list`/`--alias-list-core` commands. Aliases support `{}` placeholder substitution and embedded CLI flags, are stored as JSON in `~/.onefilellm_aliases/aliases.json`, and ship with pre-defined core aliases (`ofl_repo`, `gh_search`, `arxiv_search`, etc.). User aliases override core aliases.
- Add installable CLI via `pyproject.toml` with `onefilellm` console entry point ([`8d0de3c`](https://github.com/jimmc414/onefilellm/commit/8d0de3c), [#39](https://github.com/jimmc414/onefilellm/pull/39)) — Adds packaging (`pyproject.toml`, `cli.py`) so the tool can be installed with `pip install -e .` and invoked as the `onefilellm` command instead of `python onefilellm.py`. Contributed by Joost Boonzajer Flaes.

### Changed
- Scale reported token counts by configurable 1.37x multiplier for XML overhead ([`a88ca63`](https://github.com/jimmc414/onefilellm/commit/a88ca63)) — Introduces `TOKEN_ESTIMATE_MULTIPLIER` (default 1.37) applied to the tiktoken count so the displayed estimate better reflects real model token usage including XML wrapping. Changes the token numbers shown to users.

### Fixed
- Fix multi-URL alias expansion when not wrapped in quotes ([`6ddefad`](https://github.com/jimmc414/onefilellm/commit/6ddefad))
- Fix YouTube transcript fetching using yt-dlp with `youtube_transcript_api` fallback ([`d0e972e`](https://github.com/jimmc414/onefilellm/commit/d0e972e)) — Reworks transcript retrieval to use yt-dlp as the primary method (downloading subtitles) and falls back to `youtube_transcript_api`, with improved error messages for missing captions. Adds yt-dlp to requirements.

## 2025-05

### Added
- Accept multiple input sources as additional command-line arguments ([`f6f1909`](https://github.com/jimmc414/onefilellm/commit/f6f1909)) — `main()` now processes several inputs passed as extra args in a single run rather than a single input path.
- Add alias system with `--add-alias` and `--alias-from-clipboard`, plus launcher scripts ([`503d010`](https://github.com/jimmc414/onefilellm/commit/503d010)) — Adds alias management commands for saving reusable input shortcuts and cross-platform launcher scripts (`run_onefilellm.bat` / `run_onefilellm.sh`). Also fixes local PDF text extraction and renames the root output tag to `<onefilellm_output>`.
- Process text files and other supported extensions directly from URLs ([`a379a13`](https://github.com/jimmc414/onefilellm/commit/a379a13)) — Adds direct fetching/processing of remote text files and supported extensions given a URL.
- Add XLSX/XLS spreadsheet support, converting sheets to markdown ([`0f9a29e`](https://github.com/jimmc414/onefilellm/commit/0f9a29e)) — Adds Excel file processing (to markdown tables) with accompanying tests, README update, and new requirements.
- Add stdin and clipboard stream input with format detection and overrides ([`3491dc4`](https://github.com/jimmc414/onefilellm/commit/3491dc4)) — Adds text stream input processing via stdin and clipboard, including automatic format detection, format override options, and improved error handling, with new stream test suites.
- Add asynchronous web crawler with extensive crawl configuration options ([`4704f0d`](https://github.com/jimmc414/onefilellm/commit/4704f0d)) — New `DocCrawler` class using aiohttp for concurrent crawling, with options for max depth/pages, include/exclude URL patterns, robots.txt handling, concurrency, delay, path restriction, readability-based content extraction, and code-block language detection. Adds aiohttp, readability-lxml, python-dotenv to requirements.

### Changed
- Unpin dependency versions in requirements ([`07e3122`](https://github.com/jimmc414/onefilellm/commit/07e3122)) — Removed pinned versions that forced users to upgrade packages.

### Fixed
- Fix alias resolution for interactive mode ([`cd2acdf`](https://github.com/jimmc414/onefilellm/commit/cd2acdf)) — Adds `resolve_single_input_source` helper so aliases expand consistently in both CLI and interactive input, and handles empty input strings.

### Internal
- Decouple shared logic into `utils.py` and add consolidated test suite ([`0c07430`](https://github.com/jimmc414/onefilellm/commit/0c07430)) — Refactors `onefilellm.py` extracting helpers into a new `utils.py` and replaces the prior scattered test scripts with `test_all.py`, plus `test.bat`/`test.sh` runners.

_A web-scraping features commit (e3038af, 2025-05-27) was reverted two days later (9b2ffa0); the durable async crawler landed separately in `4704f0d`. Repo housekeeping: moved docs/tests into folders, removed planning docs, moved `web_app.py` into `extras/`, fixed `.gitignore` quoting, added a `CLAUDE.md`, and removed stray test/output artifacts. Plus test-suite additions and ~13 minor README/docs tweaks ("simplify readme", more examples, alias help text)._

## 2025-03

### Changed
- **Breaking:** Make NLTK download, stopword removal, and compression opt-in via `ENABLE_COMPRESSION_AND_NLTK` flag ([`1bdb819`](https://github.com/jimmc414/onefilellm/commit/1bdb819)) — NLTK stopword download and compressed output are now disabled by default behind a hard-coded config flag, avoiding unnecessary downloads and only producing the uncompressed output unless enabled.

### Fixed
- Disable XML escaping of file content and make `GITHUB_TOKEN` non-fatal ([`077f58f`](https://github.com/jimmc414/onefilellm/commit/077f58f)) — Large rework: `escape_xml` is neutered so code content (`<`, `>`, `&`) is preserved verbatim inside the XML-like tags for LLM readability, f-string escape bugs in GitHub comment processing are fixed, and a missing `GITHUB_TOKEN` now prints a warning instead of raising `EnvironmentError`.

_Plus a one-line `architecture.md` edit (e947b3c) and test-only assertion updates during the plain-text/XML output transition._

## 2025-01

### Added
- Add ability to exclude directories from GitHub repo processing ([`590ebc3`](https://github.com/jimmc414/onefilellm/commit/590ebc3), [#21](https://github.com/jimmc414/onefilellm/pull/21)) — Adds `EXCLUDED_DIRS` handling so directories like `dist`, `node_modules`, `.git`, and `__pycache__` are skipped, with a follow-up fix to correctly filter them in `process_github_repo`.
- Add file exclusion filters for generated/mock files and expand allowed extensions ([`1f1b39f`](https://github.com/jimmc414/onefilellm/commit/1f1b39f), [#22](https://github.com/jimmc414/onefilellm/pull/22)) — Introduces `is_excluded_file()` to skip patterns like `.pb.go`, `_grpc.pb.go`, `mock_`, `/generated/`, `/mocks/`, `.gen.`, `_generated.`; also adds `.go` and `.proto` to the allowed filetypes.

## 2024-12

### Added
- Add Flask `web_app.py` for a browser-based hosting option ([`b4853b1`](https://github.com/jimmc414/onefilellm/commit/b4853b1)) — New 128-line web app providing a web front end to run onefilellm in a browser instead of the CLI.
- Support GitHub repo URLs that specify a branch or tag ([`23b9097`](https://github.com/jimmc414/onefilellm/commit/23b9097)) — `process_github_repo` now parses `/tree/<branch-or-tag>/<subdir>` URLs and passes `?ref=<branch>` to the GitHub contents API, instead of only handling the default branch.

## 2024-07

### Changed
- **Breaking:** Wrap output in XML-like tags (`<source>`, `<file>`) for structure ([`73639fa`](https://github.com/jimmc414/onefilellm/commit/73639fa)) — Restructured `onefilellm.py` output to encapsulate each input source and file in XML-style tags, replacing the prior flatter format.

## 2024-06

### Fixed
- Chunk large text in token counting to avoid tiktoken encoding errors ([`4358dd4`](https://github.com/jimmc414/onefilellm/commit/4358dd4), [#14](https://github.com/jimmc414/onefilellm/pull/14)) — `get_token_count` now splits text into fixed-size chunks (default 1000 chars) and sums token counts per chunk, preventing encoding errors on large inputs.

### Docs
- Add architecture document ([`b187416`](https://github.com/jimmc414/onefilellm/commit/b187416)) — New `architecture.md` describing the project's design, iteratively expanded over several follow-up edits.
- Add data flow diagram to README ([`165adee`](https://github.com/jimmc414/onefilellm/commit/165adee)) — Adds an 86-line data flow diagram section to `README.md`.

_Plus ~8 minor `architecture.md` follow-up edits/rename and several README wording tweaks (Jun 2024)._

## 2024-05

### Added
- Add Rich-based terminal UI with panels, progress bars, and colored output ([`a74a021`](https://github.com/jimmc414/onefilellm/commit/a74a021)) — Integrates the Rich library (Console, Panel, Progress, Syntax, traceback) for an intro panel, processing progress bar, and styled output; adds rich to requirements.txt.
- Accept path or URL as a command-line argument ([`20db7d8`](https://github.com/jimmc414/onefilellm/commit/20db7d8)) — If an argument is supplied (`sys.argv[1]`) it is used as the input path/URL; otherwise the tool falls back to the interactive prompt.

## 2024-04

### Added
- Add GitHub pull request ingestion via PR URL, concatenated with full repo ([`2176beb`](https://github.com/jimmc414/onefilellm/commit/2176beb)) — Passing a GitHub pull request URL pulls the complete PR (details, diff, comments) and concatenates it with the repository contents.
- Add GitHub issue ingestion via issue URL, concatenated with full repo ([`788baf9`](https://github.com/jimmc414/onefilellm/commit/788baf9)) — Passing a GitHub issue URL pulls the specific issue and concatenates it with the repository contents.

### Fixed
- Handle inaccessible Sci-Hub or missing document gracefully ([`7b10502`](https://github.com/jimmc414/onefilellm/commit/7b10502)) — `process_doi_or_pmid` now raises a clear `ValueError` and prints a "Sci-hub appears to be inaccessible or the document was not found" message instead of crashing with `'NoneType' object has no attribute 'get'` when no PDF element is found.

## 2024-03

### Added
- Add Sci-Hub paper ingestion via DOI or PMID ([`f65117a`](https://github.com/jimmc414/onefilellm/commit/f65117a)) — New `process_doi_or_pmid()` downloads papers from Sci-Hub by DOI (e.g. `10.x/...`) or numeric PMID, extracts PDF text, and cleans up the temp file; enables ingestion of bioRxiv/medRxiv preprints. Adds wget and tqdm dependencies and expands the allowed-filetype list (adds `.js`, `.rst`, `.pyx`, `.html`, `.yaml`, `.json`, `.h`, `.c`, `.csv`). README also advertises `.Xlsx` support, but no xlsx handling exists in the code at this point.

### Changed
- **Breaking:** Rename entry-point script `1filellm.py` to `onefilellm.py` ([`852a494`](https://github.com/jimmc414/onefilellm/commit/852a494)) — Renamed so the module name does not start with a digit, enabling it to be imported by the automated test suite. Users must now invoke `onefilellm.py` instead of `1filellm.py`.
- Upgrade tiktoken dependency from 0.0.3 to 0.6.0 ([`7009f24`](https://github.com/jimmc414/onefilellm/commit/7009f24)) — Bumps the tiktoken pin in requirements.txt to a modern release for token counting.

### Internal
- Add automated self-testing module `test_onefilellm.py` ([`3a898cd`](https://github.com/jimmc414/onefilellm/commit/3a898cd)) — New `test_onefilellm.py` provides automated tests intended to safeguard program stability across changes; accompanied by a testing README.

## 2024-02

### Added
- Add YouTube transcript ingestion from video URLs ([`7fa99e0`](https://github.com/jimmc414/onefilellm/commit/7fa99e0)) — Detects `youtube.com`/`youtu.be` URLs at the ingestion prompt, extracts the video ID, and fetches the transcript via `youtube-transcript-api`, formatting it to plain text.

### Docs
- Add MIT LICENSE ([`619c2f6`](https://github.com/jimmc414/onefilellm/commit/619c2f6))

### Internal
- Add `requirements.txt` and `.gitignore`, lint README ([`bceade3`](https://github.com/jimmc414/onefilellm/commit/bceade3), [#1](https://github.com/jimmc414/onefilellm/pull/1)) — Introduces pinned-less dependency manifest (requests, bs4, PyPDF2, tiktoken, nltk, nbformat, nbconvert, pyperclip, youtube_transcript_api) plus a Python `.gitignore`. Contributed by Sam McLeod.

## 2024-01

### Security
- **Breaking:** Read GitHub token from `GITHUB_TOKEN` environment variable instead of source ([`b31f271`](https://github.com/jimmc414/onefilellm/commit/b31f271)) — `1filellm.py` loads the GitHub personal access token from the `GITHUB_TOKEN` environment variable and raises `EnvironmentError` if it is unset, removing the credential from source code. Users who previously edited an in-file token must now set the env var.

### Added
- **Breaking:** Rewrite as `1filellm.py` with depth-limited web page crawling as a new input source ([`b31f271`](https://github.com/jimmc414/onefilellm/commit/b31f271)) — New `1filellm.py` replaces `onefilerepo.py` and adds website crawling via BeautifulSoup: follows same-domain links up to a configurable depth (default 2), strips scripts/styles/comments, optionally includes PDFs and ignores EPUBs, and writes a `processed_urls.txt` list. Also broadens supported file extensions (`.h`, `.c`, `.sql`, `.csv`, etc.) and adds encoding-fallback file reads.

### Changed
- **Breaking:** Emit both compressed and uncompressed outputs and auto-copy result to clipboard ([`b31f271`](https://github.com/jimmc414/onefilellm/commit/b31f271)) — `1filellm.py` writes `uncompressed_output.txt` and `compressed_output.txt`, prints token counts for each, and copies the uncompressed text to the system clipboard via pyperclip. Output filenames changed from the prior `concatenated_files.txt`/`output.txt` scheme.

### Removed
- Remove legacy standalone scripts after consolidating into `1filellm.py` ([`757089c`](https://github.com/jimmc414/onefilellm/commit/757089c)) — Deletes the superseded `onefilerepo.py`, `clean.py`, and `urlextractor.py` now that their functionality is merged into the single `1filellm.py` entry point.

### Docs
- Rewrite README as "LLM Content Harvester" documenting the new tool ([`cb76851`](https://github.com/jimmc414/onefilellm/commit/cb76851)) — README expanded to document the renamed tool covering GitHub repos, local folders, arXiv papers and web pages, with feature list, prerequisites (requests, nbformat, nbconvert, nltk, PyPDF2, tiktoken, pyperclip), and per-source usage examples.

_Plus ~17 minor README wording/formatting tweaks on 2024-01-28/29 leading up to the final README rewrite._

## 2023-10

### Added
- Add arXiv PDF extraction, tiktoken token counting, and GitHub subdirectory support ([`891852c`](https://github.com/jimmc414/onefilellm/commit/891852c)) — `onefilerepo.py` gains arXiv abstract-to-PDF text extraction (PyPDF2), tiktoken-based token counting, NLTK stopword cleaning, and support for ingesting a specific subdirectory of a GitHub repo via `/tree/` URLs. The previously hardcoded GitHub token was replaced with a placeholder constant.

## 2023-03

### Added
- Add initial repo-to-text tool for LLM ingestion (`onefilerepo.py`) ([`9cacaa3`](https://github.com/jimmc414/onefilellm/commit/9cacaa3)) — Introduces `onefilerepo.py` plus helper scripts (`clean.py`, `urlextractor.py`) that concatenate a GitHub repo or local folder into a single text file, convert Jupyter notebooks to Python, strip stopwords/whitespace and lowercase the text, extract URLs, and report a token count. README documents the "Repo-Prep for LLM Ingestion" workflow.

_Across 2023-03 through 2024-01 there were also ~27 minor README/docs wording tweaks, minor `onefilerepo.py` edits (a37168b, 85fbfed), a trailing-newline fix to `1filellm.py` (aaf83e7), and cleanup of generated artifacts that were no longer tracked (`concatenated_files.txt`, `links.txt`, `output.txt`)._
