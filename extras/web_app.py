from flask import Flask, request, render_template_string, send_file
import os
import sys

# Import functions from onefilellm.py. 
# Ensure onefilellm.py is accessible in the same directory.
from onefilellm import process_github_repo, process_github_pull_request, process_github_issue
from onefilellm import process_arxiv_pdf, process_local_folder, fetch_youtube_transcript
from onefilellm import crawl_and_extract_text, process_doi_or_pmid, get_token_count, preprocess_text, safe_file_read
from pathlib import Path
import pyperclip

app = Flask(__name__)

# Simple HTML template using inline rendering for demonstration.
template = """
<!DOCTYPE html>
<html>
<head>
    <title>1FileLLM Web Interface</title>
    <style>
    body { font-family: sans-serif; margin: 2em; }
    input[type="text"] { width: 80%; padding: 0.5em; }
    .output-container { margin-top: 2em; }
    .file-links { margin-top: 1em; }
    pre { background: #f8f8f8; padding: 1em; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>1FileLLM Web Interface</h1>
    <form method="POST" action="/">
        <p>Enter a URL, path, DOI, or PMID:</p>
        <input type="text" name="input_path" required placeholder="e.g. https://github.com/jimmc414/1filellm or /path/to/local/folder"/>
        <button type="submit">Process</button>
    </form>

    {% if output %}
    <div class="output-container">
        <h2>Processed Output</h2>
        <pre>{{ output }}</pre>
        
        <h3>Token Counts</h3>
        <p>Uncompressed Tokens: {{ uncompressed_token_count }}<br>
        Compressed Tokens: {{ compressed_token_count }}</p>

        <div class="file-links">
            <a href="/download?filename=uncompressed_output.txt">Download Uncompressed Output</a> |
            <a href="/download?filename=compressed_output.txt">Download Compressed Output</a>
        </div>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        input_path = request.form.get("input_path", "").strip()

        # Prepare filenames
        output_file = "uncompressed_output.txt"
        processed_file = "compressed_output.txt"
        urls_list_file = "processed_urls.txt"

        # Determine input type and process accordingly (mirroring logic from onefilellm.py main)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(input_path)

            if "github.com" in input_path:
                if "/pull/" in input_path:
                    final_output = process_github_pull_request(input_path)
                elif "/issues/" in input_path:
                    final_output = process_github_issue(input_path)
                else:
                    final_output = process_github_repo(input_path)
            elif parsed.scheme in ["http", "https"]:
                if "youtube.com" in input_path or "youtu.be" in input_path:
                    final_output = fetch_youtube_transcript(input_path)
                elif "arxiv.org" in input_path:
                    final_output = process_arxiv_pdf(input_path)
                else:
                    crawl_result = crawl_and_extract_text(input_path, max_depth=2, include_pdfs=True, ignore_epubs=True)
                    final_output = crawl_result['content']
                    with open(urls_list_file, 'w', encoding='utf-8') as urls_file:
                        urls_file.write('\n'.join(crawl_result['processed_urls']))
            elif (input_path.startswith("10.") and "/" in input_path) or input_path.isdigit():
                final_output = process_doi_or_pmid(input_path)
            else:
                final_output = process_local_folder(input_path)

            # Write the uncompressed output
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(final_output)

            # Process the compressed output
            preprocess_text(output_file, processed_file)

            compressed_text = safe_file_read(processed_file)
            compressed_token_count = get_token_count(compressed_text)

            uncompressed_text = safe_file_read(output_file)
            uncompressed_token_count = get_token_count(uncompressed_text)

            # Copy to clipboard
            pyperclip.copy(uncompressed_text)

            return render_template_string(template,
                                          output=final_output,
                                          uncompressed_token_count=uncompressed_token_count,
                                          compressed_token_count=compressed_token_count)
        except Exception as e:
            return render_template_string(template, output=f"Error: {str(e)}")

    return render_template_string(template)


@app.route("/download")
def download():
    filename = request.args.get("filename")
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    # Run the app in debug mode for local development
    app.run(debug=True, host="0.0.0.0", port=5000)
