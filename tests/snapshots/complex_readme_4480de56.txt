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

Processing: ./src/


Error processing ./src/: Input path or URL type not recognized: ./src/
Successfully processed: ./src/

Processing: https://github.com/jimmc414/onefilellm/issues/1

Fetching issue data for: https://github.com/jimmc414/onefilellm/issues/1
Error fetching GitHub issue data for 
https://github.com/jimmc414/onefilellm/issues/1: 401 Client Error: Unauthorized 
for url: https://api.github.com/repos/jimmc414/onefilellm/issues/1
Successfully processed: https://github.com/jimmc414/onefilellm/issues/1

Processing: https://react.dev/


Initiating web crawl for: https://react.dev/
  Failed to fetch https://react.dev/link-to-suspense-below: HTTP Error 404: Not 
Found
  Failed to fetch https://react.dev/reference/react-dom/client/flushSync: HTTP 
Error 404: Not Found

Crawl complete. Pages crawled: 184. Failed URLs: 2
Failed URLs (2):
  - https://react.dev/link-to-suspense-below : HTTP Error 404: Not Found
  - https://react.dev/reference/react-dom/client/flushSync : HTTP Error 404: Not
Found
Successfully processed: https://react.dev/

Writing output to output.xml...
Output written successfully.

Summary:
  - Sources Processed: 3
  - Final Output Size: 2,488.99 KB

Content Token Count (tiktoken): 401,912
Estimated Model Token Count (incl. overhead): 550,619

output.xml (main XML) has been created.

The contents of output.xml have been copied to the clipboard.
Processing inputs... ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% • 3/3 sources      • 0:00:00
Crawl finished       ━━━━╸                      18% • 184/1000 sources • 0:03:15