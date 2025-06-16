STDOUT:
╭───────────── onefilellm - Content Aggregator ──────────────╮
│                                                            │
│                                                            │
│ Processes Inputs and Wraps Content in XML:                 │
│                                                            │
│ • Local folder path                                        │
│ • GitHub repository URL                                    │
│ • GitHub pull request URL (PR + Repo)                      │
│ • GitHub issue URL (Issue + Repo)                          │
│ • Documentation URL (Web Crawl)                            │
│ • YouTube video URL (Transcript)                           │
│ • ArXiv Paper URL (PDF Text)                               │
│ • DOI or PMID (via Sci-Hub, best effort)                   │
│ • Text from stdin (e.g., `cat file.txt | onefilellm -`)    │
│ • Text from clipboard (e.g., `onefilellm --clipboard`)     │
│                                                            │
│ Output is saved to file and copied to clipboard.           │
│ Content within XML tags remains unescaped for readability. │
│ Multiple inputs can be provided as command line arguments. │
│                                                            │
╰────────────────────────────────────────────────────────────╯

Processing: 10.1053/j.ajkd.2017.08.002

Attempting Sci-Hub domain: https://sci-hub.se/ for identifier: 
10.1053/j.ajkd.2017.08.002
  Error with https://sci-hub.se/: 403 Client Error: Forbidden for url: 
https://sci-hub.se/
Attempting Sci-Hub domain: https://sci-hub.st/ for identifier: 
10.1053/j.ajkd.2017.08.002
  Found potential PDF URL: 
https://dacemirror.sci-hub.st/journal-article/926f6c4c63391eb19a4ca8172d8b56d9/m
akkapati2017.pdf?download=true
  Downloading PDF from: 
https://dacemirror.sci-hub.st/journal-article/926f6c4c63391eb19a4ca8172d8b56d9/m
akkapati2017.pdf?download=true
  Extracting text from PDF...
Identifier 10.1053/j.ajkd.2017.08.002 processed successfully via 
https://sci-hub.st/.
Successfully processed: 10.1053/j.ajkd.2017.08.002

Writing output to output.xml...
Output written successfully.

Summary:
  - Sources Processed: 1
  - Final Output Size: 27.51 KB

Content Token Count (tiktoken): 2,777
Estimated Model Token Count (incl. overhead): 3,804

output.xml (main XML) has been created.

The contents of output.xml have been copied to the clipboard.
Processing inputs... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% • 1/1 sources • 0:00:00