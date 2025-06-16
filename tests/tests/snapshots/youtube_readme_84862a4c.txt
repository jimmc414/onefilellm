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

Processing: https://www.youtube.com/watch?v=KZ_NlnmPQYk

Fetching transcript for YouTube video ID: KZ_NlnmPQYk
Direct method failed: no element found: line 1, column 0
Trying alternative method: listing available transcripts...
Attempting to fetch English transcript...
Attempting to fetch English (auto-generated) transcript...
Error fetching YouTube transcript for 
https://www.youtube.com/watch?v=KZ_NlnmPQYk: No captions/transcript available 
for this video (parsing error)
Successfully processed: https://www.youtube.com/watch?v=KZ_NlnmPQYk

Writing output to output.xml...
Output written successfully.

Summary:
  - Sources Processed: 1
  - Final Output Size: 0.21 KB

Content Token Count (tiktoken): 14
Estimated Model Token Count (incl. overhead): 19

output.xml (main XML) has been created.

The contents of output.xml have been copied to the clipboard.
Processing inputs... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% • 1/1 sources • 0:00:00