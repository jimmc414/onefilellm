# Extras

This folder contains additional tools, examples, and experimental features for OneFileLLM.

## web_app.py — Conduit

A single-user, localhost Flask web console for OneFileLLM ("Conduit"). It pipes any
supported source (GitHub repo / PR / issue, ArXiv, YouTube, docs site, DOI, PMID) into one
LLM-ready file and shows live progress, structured results, and one-click copy/download.

It is offline-safe by design: no CDN, no web fonts, no icon fonts, no build step — vanilla
JavaScript, system font stacks, and inline SVG only. The only Python dependency is Flask;
everything else reuses the existing OneFileLLM pipeline in `onefilellm.py`.

### Running it

```bash
# 1) Install the core OneFileLLM dependencies (from the repo root)
pip install -r requirements.txt

# 2) Install the web app's only extra dependency (Flask)
pip install -r extras/requirements.txt

# 3) Start the app from the repo root
python extras/web_app.py

# 4) Open it in a browser
#    http://127.0.0.1:5000
```

Run `python extras/web_app.py` **from the repo root** so the output files land there and
`onefilellm.py` is importable. (The app also inserts the repo root onto `sys.path` itself, so
the import works regardless of the current directory.)

### Features

- **Live SSE progress** — a `text/event-stream` endpoint streams per-stage events
  (detect / fetch / crawl / extract / tokenize). Web crawls show a determinate
  "N / M pages" bar with a moving denominator.
- **Structured result** — estimated model tokens (hero), uncompressed/compressed token
  counts with a compression delta, output size, source count, and elapsed time.
- **Output tree** — a server-parsed list of the files/pages in the output (virtualized for
  large outputs), with a Raw tab showing a bounded preview (first 256 KB on a UTF-8
  boundary; a notice appears when the full output is larger).
- **Client-side copy** — copy the full uncompressed or compressed output to the clipboard
  (fetched from `/result/raw`), with a select-and-Ctrl/Cmd-C fallback if the clipboard API
  is unavailable.
- **Download** — download `uncompressed_output.txt` or `compressed_output.txt`.
- **Light / dark theme** — toggle in the header (persisted in `localStorage`), defaulting to
  the OS preference; `Alt`+`T` switches it, `/` focuses the input.
- **No-JS fallback** — submitting the form without JavaScript runs the same pipeline
  synchronously and server-renders the result (bounded `<pre>`, token counts, download
  links) or the matching error notice. JS clients intercept submit and use the live stream
  instead.
- **Recent inputs** — an optional session history popover (stored in `localStorage`).

### Security model (preserved)

The web app reuses OneFileLLM's security guards on **every** path (live stream and the no-JS
POST fallback), before any network fetch:

- **SSRF guard (`_is_safe_url`)** — rejects URLs pointing at localhost, private, link-local,
  reserved, or cloud-metadata hosts. Kept byte-for-byte from the original.
- **No local paths** — filesystem-path-shaped inputs (`/…`, `~`, `./`, `../`, `C:\…`,
  `file://`) are rejected; the web app never reads local files.
- **Download whitelist** — `/download` and `/result/raw` only ever serve the two fixed output
  filenames (`uncompressed_output.txt`, `compressed_output.txt`); anything else is refused.
- **Localhost only** — the server binds `127.0.0.1`, runs with `debug=False`, and has no
  authentication because it is intended for **single-user localhost** use only. Do not expose
  it to a network.
- Untrusted result text reaches the page only via `textContent` (never `innerHTML`); the
  no-JS preview is autoescaped by Jinja.

### Requirements

- Flask (`extras/requirements.txt`)
- All OneFileLLM dependencies (`requirements.txt`)
- A modern web browser

## Contributing

If you build upon these extras or create your own integrations, consider submitting a pull
request to share with the community!
