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

Processing: https://arxiv.org/abs/2401.14295

Downloading ArXiv PDF from https://arxiv.org/pdf/2401.14295.pdf...
Extracting text from PDF...
  Processing page 1/40
  Processing page 2/40
  Processing page 3/40
  Processing page 4/40
  Processing page 5/40
  Processing page 6/40
  Processing page 7/40
  Processing page 8/40
  Processing page 9/40
  Processing page 10/40
  Processing page 11/40
  Processing page 12/40
  Processing page 13/40
  Processing page 14/40
  Processing page 15/40
  Processing page 16/40
  Processing page 17/40
  Processing page 18/40
  Processing page 19/40
  Processing page 20/40
  Processing page 21/40
  Processing page 22/40
  Processing page 23/40
  Processing page 24/40
  Processing page 25/40
  Processing page 26/40
  Processing page 27/40
  Processing page 28/40
  Processing page 29/40
  Processing page 30/40
  Processing page 31/40
  Processing page 32/40
  Processing page 33/40
  Processing page 34/40
  Processing page 35/40
  Processing page 36/40
  Processing page 37/40
  Processing page 38/40
  Processing page 39/40
  Processing page 40/40
ArXiv paper processed successfully.
Successfully processed: https://arxiv.org/abs/2401.14295

Writing output to output.xml...
Output written successfully.

Summary:
  - Sources Processed: 1
  - Final Output Size: 255.38 KB

Content Token Count (tiktoken): 68,434
Estimated Model Token Count (incl. overhead): 93,755

output.xml (main XML) has been created.

The contents of output.xml have been copied to the clipboard.
Processing inputs... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% • 1/1 sources • 0:00:00