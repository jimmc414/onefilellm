from flask import Flask, request, render_template_string, send_file
import os
import sys
from urllib.parse import urlparse # Added for robust error display if needed

# Import functions from onefilellm.py.
# process_input is the key new import.
# Specific process_* functions are removed as process_input handles dispatch.
from onefilellm import process_input, get_token_count, preprocess_text, safe_file_read
# ENABLE_COMPRESSION_AND_NLTK is a global flag in onefilellm, preprocess_text uses it.

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
    pre { background: #f8f8f8; padding: 1em; border: 1px solid #ccc; white-space: pre-wrap; word-wrap: break-word; }
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
            <a href="/download?filename=output.xml">Download Uncompressed Output (XML)</a> |
            <a href="/download?filename=compressed_output.txt">Download Compressed Output (TXT)</a>
        </div>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    output_data = None
    uncompressed_tokens = 0
    compressed_tokens = 0

    if request.method == "POST":
        input_path = request.form.get("input_path", "").strip()

        # Define filenames consistently with onefilellm.py
        # process_input will return XML, so output_file should reflect that.
        output_file = "output.xml" 
        processed_file = "compressed_output.txt"
        # urls_list_file is handled by onefilellm.py's crawl_and_extract_text via process_input

        try:
            # Centralized call to process_input
            # process_input handles its own console, config, and dispatch logic.
            # It's designed to return an XML string (either content or an error source).
            final_output = process_input(input_path)

            if final_output is None or not final_output.strip():
                # This case should ideally be covered by process_input returning an error XML.
                # However, as a fallback:
                print(f"Error in web_app: process_input for '{input_path}' returned None or empty.", file=sys.stderr)
                output_data = f'<source type="error" path="{input_path}"><e>Web app error: Processing returned no output.</e></source>'
            else:
                output_data = final_output # This is the XML string

                # Write the uncompressed XML output
                with open(output_file, "w", encoding="utf-8") as file:
                    file.write(output_data)

                # Process the compressed output (if ENABLE_COMPRESSION_AND_NLTK is True in onefilellm.py)
                # preprocess_text reads from output_file (XML) and writes to processed_file (TXT)
                preprocess_text(output_file, processed_file)

                # Token counting
                # For uncompressed, count tokens from the XML output (get_token_count strips tags)
                uncompressed_tokens = get_token_count(output_data)
                
                # For compressed, read the processed text file
                if os.path.exists(processed_file):
                    compressed_text = safe_file_read(processed_file)
                    compressed_tokens = get_token_count(compressed_text)
                else:
                    # This might happen if compression is disabled or failed.
                    compressed_tokens = 0 
                    print(f"Warning: Compressed file '{processed_file}' not found for token counting.", file=sys.stderr)


        except Exception as e:
            # This block catches errors that might occur *outside* of process_input's own try-except,
            # or if process_input itself raises an unexpected exception.
            print(f"Error in web_app processing for '{input_path}': {e}", file=sys.stderr)
            # Use the exception message to form an XML error string.
            output_data = f'<source type="error" path="{input_path}"><e>Web app error: {str(e)}</e></source>'
            uncompressed_tokens = 0
            compressed_tokens = 0
        
        return render_template_string(template,
                                      output=output_data,
                                      uncompressed_token_count=uncompressed_tokens,
                                      compressed_token_count=compressed_tokens)

    return render_template_string(template)


@app.route("/download")
def download():
    filename = request.args.get("filename")
    # Security: Basic check to prevent arbitrary file access.
    # In a production app, you'd want more robust validation.
    allowed_files = ["output.xml", "compressed_output.txt"]
    if filename in allowed_files and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found or access denied", 404

if __name__ == "__main__":
    # Ensure the onefilellm.py script can be found if it's not in the default Python path
    # This is usually not needed if they are in the same directory.
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # if script_dir not in sys.path:
    #    sys.path.insert(0, script_dir)

    # Run the app in debug mode for local development
    app.run(debug=True, host="0.0.0.0", port=5000)
