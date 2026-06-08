"""Conduit — Flask web app for OneFileLLM.

Single-user localhost console that pipes any source into one LLM-ready file.
See extras/redesign_onefilellm_webapp_py.md (design) and the build contract
for the authoritative machine interface. Offline-safe, Flask-only dependency,
templates/ and static/ are auto-served because Flask(__name__) roots at extras/.
"""

from flask import Flask, request, render_template, send_file, abort, Response
import os
import sys
import re
import json
import time
import queue
import threading
import ipaddress
import socket
from urllib.parse import urlparse

# requests is a core OneFileLLM dependency. Its PreparedRequest URL normaliser
# yields the EXACT host the client connects to (percent-decoded and IDNA-encoded),
# which is what _is_safe_url() validates — closing the parser/percent-encoding
# SSRF differential reported in GH issue #79.
import requests

# Import functions from onefilellm.py. onefilellm.py lives at the repo root, but
# `python extras/web_app.py` only puts extras/ on sys.path — so make the repo
# root (this file's parent directory) importable before importing onefilellm.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from onefilellm import process_github_repo, process_github_pull_request, process_github_issue
from onefilellm import process_arxiv_pdf, fetch_youtube_transcript
from onefilellm import crawl_and_extract_text, process_doi_or_pmid
from onefilellm import get_token_count, preprocess_text, safe_file_read, TOKEN_ESTIMATE_MULTIPLIER

app = Flask(__name__)

# Directory where output files are written; downloads are restricted to this directory.
OUTPUT_DIR = os.path.abspath(".")

# Allowed filenames that may be downloaded via /download (and read via /result/raw).
ALLOWED_DOWNLOAD_FILES = {"uncompressed_output.txt", "compressed_output.txt"}

# Fixed output filenames (unchanged from the original implementation).
UNCOMPRESSED_FILE = "uncompressed_output.txt"
COMPRESSED_FILE = "compressed_output.txt"

# Bounded preview cap — the DOM never receives the full payload (contract §7.2).
PREVIEW_CAP_BYTES = 262144  # 256 KB

# Node parse cap (contract §7.3).
NODE_CAP = 2000

# Version string injected into the shell. There is no __version__ in onefilellm,
# so this is intentionally None (the header version segment is hidden when absent).
APP_VERSION = None

# ---------------------------------------------------------------------------
# Single-flight job lock. /stream acquires this non-blocking; if held, the new
# request is rejected with a `busy` error event (contract §2.1).
# ---------------------------------------------------------------------------
_job_lock = threading.Lock()


# Hostnames that denote the local/internal host without being IP literals (so a
# pure-IP check would miss them). Includes the Debian/Ubuntu IPv6 loopback aliases
# from /etc/hosts. Defence-in-depth on top of the resolve-and-revalidate step.
_BLOCKED_HOSTNAMES = {
    "localhost", "localhost.localdomain",
    "localhost4", "localhost6", "ip6-localhost", "ip6-loopback", "ip6-localnet",
    "metadata.google.internal",
}


def _is_blocked_ip(addr) -> bool:
    """True if an ipaddress object is in a non-public (SSRF-sensitive) range."""
    if (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
        return True
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None and _is_blocked_ip(mapped):
        return True
    return False


def _connection_host(url: str):
    """Return the exact host requests will connect to (lowercased), or None.

    ``requests.PreparedRequest.prepare_url`` percent-decodes and IDNA-encodes the
    host into precisely the value handed to the connection pool. Validating THIS
    host (not urlparse's raw host) is what closes the parser/percent-encoding
    differential of GH #79 — e.g. ``http://127.0.0.%31/`` prepares to host
    ``127.0.0.1`` — while correctly allowing internationalised domains
    (``münchen.de`` -> ``xn--mnchen-3ya.de``).
    """
    try:
        prepared = requests.models.PreparedRequest()
        prepared.prepare_url(url, None)
    except Exception:
        return None
    host = urlparse(str(prepared.url)).hostname or ""
    return host.strip("[]").strip(".").lower() or None


def _host_ip_candidates(host):
    """Return every IP address the given host string could denote (may be empty).

    Catches IP literals in any form an HTTP client might accept so the SSRF range
    checks can't be evaded by an alternate notation: standard dotted IPv4 + all
    IPv6 forms (via ``ipaddress``), and the legacy decimal/octal/hex IPv4 forms
    (via ``inet_aton``). A bare domain name yields no candidates.
    """
    candidates = []
    # Strip an IPv6 scope/zone id ("fe80::1%eth0") before parsing.
    bare = host.split("%", 1)[0] if "%" in host else host
    try:
        candidates.append(ipaddress.ip_address(bare))
    except ValueError:
        pass
    # Legacy/alternate IPv4: decimal int, octal, hex, and short forms. inet_aton
    # accepts these and rejects real domains (OSError), so a match means the host
    # is an IPv4 literal in disguise.
    try:
        candidates.append(ipaddress.ip_address(socket.inet_ntoa(socket.inet_aton(bare))))
    except (OSError, ValueError):
        pass
    return candidates


def _resolved_addresses(host):
    """Resolve a hostname to ipaddress objects (best-effort, never raises).

    Returns an empty list on resolution failure — we fail OPEN, because a host we
    cannot resolve cannot be connected to either (the fetch will simply error),
    and that keeps offline/air-gapped use working. Catches public names that map
    to internal IPs (e.g. ``*.nip.io``, ``localtest.me``, ``ip6-localhost``).
    """
    addrs = []
    try:
        for info in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP):
            try:
                addrs.append(ipaddress.ip_address(info[4][0]))
            except ValueError:
                pass
    except Exception:
        pass
    return addrs


def _is_safe_url(url: str) -> bool:
    """Reject URLs targeting private/internal networks (SSRF protection).

    Hardened against the parser/percent-encoding differential of GH issue #79 and
    the public-name-resolves-to-private class found by adversarial review. All
    checks run before any content fetch:
      1. Reject backslashes / control chars / whitespace (clients treat ``\\`` as
         ``/`` and strip control bytes — differentials the validator can't see).
      2. http(s) only; reject embedded ``user@host`` credentials/userinfo.
      3. Validate the EXACT host requests will connect to (PreparedRequest, which
         percent-decodes + IDNA-encodes), not urlparse's raw host.
      4. Reject blocked hostnames and private/loopback/link-local/reserved/
         multicast/unspecified IPs in ANY literal form (IPv4-mapped IPv6, and the
         legacy decimal/octal/hex IPv4 notations).
      5. Resolve the host and reject if ANY resolved address is non-public —
         catching public names that map to internal IPs. Fails open on resolution
         error so offline/unreachable use degrades gracefully.

    Out of scope: DNS rebinding (a hostile resolver returning a public address
    here and a private one at fetch time) — that needs connection pinning in the
    HTTP layer. Every static case from the security review is covered.
    """
    try:
        if not url:
            return False

        # 1) No backslashes, control characters, or whitespace anywhere in the URL.
        if "\\" in url or any(ord(c) <= 0x20 or ord(c) == 0x7F for c in url):
            return False

        parsed = urlparse(url)

        # 2) Absolute http(s) only; no embedded credentials/userinfo.
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
            return False

        # 3) The exact host requests/urllib3 will dial (decoded + IDNA-normalised).
        host = _connection_host(url)
        if not host or "%" in host:
            return False

        # 4) Blocked names + IP literals (any notation).
        if host in _BLOCKED_HOSTNAMES or host == "internal" or host.endswith(".internal"):
            return False
        for addr in _host_ip_candidates(host):
            if _is_blocked_ip(addr):
                return False

        # 5) Resolve and re-validate every address (public name -> private IP).
        for addr in _resolved_addresses(host):
            if _is_blocked_ip(addr):
                return False

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Input shape detection (contract §7.4) — local-path / private-url guards.
# ---------------------------------------------------------------------------
# Local-path shapes that must never be fetched by the web app.
_LOCAL_PATH_PREFIXES = ("/", "~", "./", "../", "file://")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _is_local_path(value: str) -> bool:
    """True when input looks like a local/relative filesystem path (blocked)."""
    if not value:
        return False
    if value.startswith(_LOCAL_PATH_PREFIXES):
        return True
    if _WINDOWS_DRIVE_RE.match(value):
        return True
    return False


def _security_check(input_path):
    """Run the security guards that must precede ANY fetch (contract §5).

    Returns an error message string if the input must be blocked, else None.
    Mirrors the dispatch guards in §7.4 steps 1-2.
    """
    # 1) Local/relative path shapes — rejected, never fetched.
    if _is_local_path(input_path):
        return "Local file paths aren't allowed in the web app. Use a URL instead."
    # 2) http(s) URLs whose host fails the SSRF guard — rejected.
    parsed = urlparse(input_path)
    if parsed.scheme in ("http", "https"):
        if not _is_safe_url(input_path):
            return "URL rejected by security policy."
    return None


# ---------------------------------------------------------------------------
# Shared algorithms (contract §7.1 classify, §7.2 metrics, §7.3 nodes).
# ---------------------------------------------------------------------------
def classify(source_text):
    """Classify the bare <source> string (contract §7.1). Do NOT naively regex <error>.

    A hard failure is an <error> that is a DIRECT child of <source> with no
    content alongside it (e.g. ``<source ...><error>msg</error></source>``). A
    crawl/repo that produced <page>/<file> children is a SUCCESS even if an
    individual page/file errored.

    We detect this by the PRESENCE of <page>/<file> tags rather than by stripping
    their bodies and re-scanning: file CONTENT routinely contains tag-like text
    (e.g. onefilellm's own source builds ``</file>`` and ``<error ...>`` strings),
    which fools a strip+search and would mislabel a successful fetch as an error.
    """
    # 1) Empty backstop — get_token_count strips ALL tags, so ~0 means no real content.
    if get_token_count(source_text) < 5:
        return ("empty", None)
    # 2) Produced structured children → the fetch succeeded; any <error> inside is
    #    per-page/per-file (or just tag-like text in file content), not a hard fail.
    if re.search(r'<(?:file|page)\b', source_text, flags=re.IGNORECASE):
        return ("success", None)
    # 3) No children: a root-level <error> means the fetch hard-failed. (The source
    #    here is simple — `<source ...><error>msg</error></source>` — and processor
    #    error messages are XML-escaped, so this regex is safe on this shape.)
    m = re.search(r'<error\b[^>]*>(.*?)</error>', source_text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return ("processing", m.group(1).strip())
    # 4) Otherwise success.
    return ("success", None)


def parse_source_meta(source_text):
    """Parse the opening <source …> tag for type and url/base_url (contract §7.3)."""
    src_type = ""
    src_url = ""
    m = re.search(r'<source\b([^>]*)>', source_text, flags=re.IGNORECASE)
    if m:
        attrs = m.group(1)
        tm = re.search(r'type="([^"]*)"', attrs, flags=re.IGNORECASE)
        if tm:
            src_type = tm.group(1)
        um = re.search(r'url="([^"]*)"', attrs, flags=re.IGNORECASE)
        if not um:
            um = re.search(r'base_url="([^"]*)"', attrs, flags=re.IGNORECASE)
        if um:
            src_url = um.group(1)
    return {"type": src_type, "url": src_url}


def parse_nodes(source_text):
    """Parse <file>/<page> nodes from the bare source_text (contract §7.3)."""
    files = re.findall(r'<file\b[^>]*\bpath="([^"]*)"[^>]*>(.*?)</file>', source_text, re.DOTALL | re.IGNORECASE)
    pages = re.findall(r'<page\b[^>]*\burl="([^"]*)"[^>]*>(.*?)</page>', source_text, re.DOTALL | re.IGNORECASE)
    nodes = ([{"kind": "file", "name": n, "bytes": len(b.encode("utf-8")), "lines": b.count("\n")} for n, b in files]
             + [{"kind": "page", "name": n, "bytes": len(b.encode("utf-8")), "lines": b.count("\n")} for n, b in pages])
    node_count = len(nodes)
    nodes_truncated = node_count > NODE_CAP
    nodes = nodes[:NODE_CAP]
    return nodes, node_count, nodes_truncated


def compute_metrics(source_text):
    """Wrap source_text, write both output files, compute metrics (contract §7.2)."""
    wrapped = f"<onefilellm_output>\n{source_text}\n</onefilellm_output>"

    # write wrapped → uncompressed_output.txt ; preprocess_text(...) → compressed_output.txt
    with open(UNCOMPRESSED_FILE, "w", encoding="utf-8") as f:
        f.write(wrapped)
    preprocess_text(UNCOMPRESSED_FILE, COMPRESSED_FILE)

    uncompressed_tokens = get_token_count(wrapped)
    compressed_tokens = get_token_count(safe_file_read(COMPRESSED_FILE))
    estimated_model_tokens = round(uncompressed_tokens * TOKEN_ESTIMATE_MULTIPLIER)

    raw = wrapped.encode("utf-8")
    total_bytes = len(raw)
    output_kb = round(total_bytes / 1024, 2)

    if total_bytes <= PREVIEW_CAP_BYTES:
        preview = wrapped
    else:
        preview = raw[:PREVIEW_CAP_BYTES].decode("utf-8", errors="ignore")
    preview_bytes = len(preview.encode("utf-8"))
    truncated = total_bytes > preview_bytes

    return {
        "wrapped": wrapped,
        "uncompressed_tokens": uncompressed_tokens,
        "compressed_tokens": compressed_tokens,
        "estimated_model_tokens": estimated_model_tokens,
        "total_bytes": total_bytes,
        "output_kb": output_kb,
        "preview": preview,
        "preview_bytes": preview_bytes,
        "truncated": truncated,
        "source_count": 1,
    }


# ---------------------------------------------------------------------------
# Detection + dispatch (contract §7.4). Returns (badge, fn) where fn(progress_cb)
# runs the processor and returns the bare <source> string. Raises ValueError
# only for blocked inputs (handled upstream via _security_check); here we assume
# the security guard already passed.
# ---------------------------------------------------------------------------
def _dispatch(input_path):
    """Return (detected_badge, runner) for a security-cleared input (contract §7.4).

    `runner(progress_cb)` invokes the right processor and returns the bare source string.
    Order matches §7.4 steps 3-10 (steps 1-2 are the security guard, handled separately).
    """
    parsed = urlparse(input_path)
    is_http = parsed.scheme in ("http", "https")

    if "github.com" in input_path:
        if "/pull/" in input_path:
            return ("github · pr", lambda cb: process_github_pull_request(input_path))
        if "/issues/" in input_path:
            return ("github · issue", lambda cb: process_github_issue(input_path))
        return ("github · repo", lambda cb: process_github_repo(input_path))

    if is_http and "arxiv.org" in input_path:
        return ("arxiv", lambda cb: process_arxiv_pdf(input_path))

    if is_http and ("youtube.com/watch" in input_path or "youtu.be/" in input_path):
        return ("youtube · transcript", lambda cb: fetch_youtube_transcript(input_path))

    if is_http:
        def _crawl(cb):
            crawl_result = crawl_and_extract_text(
                input_path, max_depth=2, include_pdfs=True, ignore_epubs=True,
                progress_callback=cb,
            )
            return crawl_result['content']
        return ("docs · will crawl", _crawl)

    if re.match(r'^10\.\d{4,9}/\S+$', input_path):
        return ("doi · best-effort", lambda cb: process_doi_or_pmid(input_path))

    if re.match(r'^\d+$', input_path):
        return ("pmid · best-effort", lambda cb: process_doi_or_pmid(input_path))

    # Nothing recognized — still attempt DOI/PMID style as a last resort to mirror
    # the historical fallthrough; if it cannot be classified, surface as processing.
    return ("", lambda cb: process_doi_or_pmid(input_path))


# ---------------------------------------------------------------------------
# Shared pipeline. Used by BOTH POST / (emit=None, synchronous) and the SSE
# worker (emit pushes pre-formatted SSE strings via the queue).
# ---------------------------------------------------------------------------
def run_job(input_path, emit=None, cancel_event=None):
    """Run the full pipeline for one input.

    - emit(name, data): optional. When provided, called for stage/page/done/error
      events. When None (POST path), the function instead RETURNS a result dict
      (contract §1.2) and emits nothing.
    - cancel_event: optional threading.Event for cooperative cancel (crawl only).

    Security guard runs first on every path (contract §5). Returns the §1.2 result
    dict on the POST path; on the SSE path returns None (events carry everything).
    """
    start = time.time()

    def _t():
        return round(time.time() - start, 1)

    # --- Security guard before any fetch (contract §5 / §7.4 steps 1-2) ---
    sec_msg = _security_check(input_path)
    if sec_msg is not None:
        if emit is not None:
            emit("error", {"subtype": "security", "message": sec_msg})
            return None
        return {
            "status": "security",
            "message": sec_msg,
            "detected": "blocked · local path" if _is_local_path(input_path) else "blocked · private url",
        }

    detected, runner = _dispatch(input_path)
    is_crawl = detected == "docs · will crawl"

    # --- detect stage ---
    if emit is not None:
        emit("stage", {"key": "detect", "label": f"detected input · {detected or 'identifier'}",
                       "status": "done", "t": _t()})

    # --- progress callback for the crawler (contract §6) ---
    def _cb(done, discovered, url):
        if cancel_event is not None and cancel_event.is_set():
            return False  # cooperative cancel — crawl breaks between pages
        if emit is not None:
            emit("page", {"fetched": done, "max": discovered, "url": url})
        return None  # continue

    # --- fetch / crawl stage ---
    if emit is not None:
        stage_key = "crawl" if is_crawl else "fetch"
        emit("stage", {"key": stage_key, "label": "crawling" if is_crawl else "fetching",
                       "status": "active", "t": _t()})

    source_text = runner(_cb)

    if emit is not None:
        stage_key = "crawl" if is_crawl else "fetch"
        emit("stage", {"key": stage_key, "label": "crawled" if is_crawl else "fetched",
                       "status": "done", "t": _t()})

    # --- classify (contract §7.1) ---
    status, err_message = classify(source_text)

    if status == "empty":
        if emit is not None:
            emit("error", {"subtype": "empty",
                           "message": "The source produced no extractable content."})
            return None
        return {"status": "empty",
                "message": "The source produced no extractable content.",
                "detected": detected}

    if status == "processing":
        if emit is not None:
            emit("error", {"subtype": "processing", "message": err_message})
            return None
        return {"status": "processing", "message": err_message, "detected": detected}

    # --- success: extract stage ---
    if emit is not None:
        emit("stage", {"key": "extract", "label": "extracting", "status": "done", "t": _t()})

    # --- metrics + node parse (contract §7.2 / §7.3) ---
    metrics = compute_metrics(source_text)

    if emit is not None:
        emit("stage", {"key": "tokenize", "label": "tokenizing", "status": "done", "t": _t()})

    nodes, node_count, nodes_truncated = parse_nodes(source_text)
    source_meta = parse_source_meta(source_text)

    if emit is not None:
        # Suppress the terminal done event if the client cancelled (contract §2.4).
        if cancel_event is not None and cancel_event.is_set():
            return None
        emit("done", {
            "status": "success",
            "source_count": metrics["source_count"],
            "uncompressed_tokens": metrics["uncompressed_tokens"],
            "compressed_tokens": metrics["compressed_tokens"],
            "estimated_model_tokens": metrics["estimated_model_tokens"],
            "output_kb": metrics["output_kb"],
            "elapsed_s": _t(),
            "preview": metrics["preview"],
            "preview_bytes": metrics["preview_bytes"],
            "total_bytes": metrics["total_bytes"],
            "truncated": metrics["truncated"],
            "source": source_meta,
            "nodes": nodes,
            "node_count": node_count,
            "nodes_truncated": nodes_truncated,
        })
        return None

    # POST path success result dict (contract §1.2).
    return {
        "status": "success",
        "preview": metrics["preview"],
        "truncated": metrics["truncated"],
        "preview_bytes": metrics["preview_bytes"],
        "total_bytes": metrics["total_bytes"],
        "uncompressed_tokens": metrics["uncompressed_tokens"],
        "compressed_tokens": metrics["compressed_tokens"],
        "estimated_model_tokens": metrics["estimated_model_tokens"],
        "output_kb": metrics["output_kb"],
        "message": None,
        "detected": detected,
    }


# ---------------------------------------------------------------------------
# SSE plumbing (contract §2, §3, §4).
# ---------------------------------------------------------------------------
def _format_sse(name, data):
    """Format a single SSE message: event + compact one-line JSON data."""
    return f"event: {name}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _put_block(q, name, data):
    """Block-put a stage/done/error event (never dropped, contract §2.3)."""
    q.put(_format_sse(name, data))


def _put_drop(q, name, data):
    """Drop-on-full put for page events (contract §2.3)."""
    try:
        q.put_nowait(_format_sse(name, data))
    except queue.Full:
        pass


def _run_worker(input_path, q, cancel_event):
    """SSE worker body (contract §2.1). Always sentinels the queue and releases the lock."""
    def emit(name, data):
        # Page events are always best-effort (drop-on-full). Once the client has
        # disconnected (cancel_event set), the queue consumer is gone — so switch
        # stage/done/error to drop-on-full too, otherwise a full queue would block
        # this worker forever and never release _job_lock (wedging single-flight).
        if name == "page" or cancel_event.is_set():
            _put_drop(q, name, data)
        else:
            _put_block(q, name, data)

    try:
        run_job(input_path, emit=emit, cancel_event=cancel_event)
    except Exception as e:
        _put_block(q, "error", {"subtype": "internal", "message": str(e)})
    finally:
        q.put(None)            # sentinel — ALWAYS, guarantees the stream closes
        _job_lock.release()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """GET → app shell (result=None). POST → synchronous no-JS fallback (contract §1.1/§1.2)."""
    if request.method == "POST":
        input_path = request.form.get("input_path", "").strip()
        try:
            result = run_job(input_path, emit=None, cancel_event=None)
        except Exception as e:
            result = {"status": "processing", "message": str(e), "detected": ""}
        return render_template("index.html", result=result, version=APP_VERSION)

    return render_template("index.html", result=None, version=APP_VERSION)


@app.route("/stream")
def stream():
    """SSE progress endpoint (contract §1.3, §2, §3)."""
    input_path = (request.args.get("input") or "").strip()

    # 1) Single-flight lock — non-blocking. Busy → one error event, then terminate.
    if not _job_lock.acquire(blocking=False):
        def busy_gen():
            yield ": connected\n\n"
            yield _format_sse("error", {"subtype": "busy",
                                        "message": "A job is already running — wait for it to finish."})
        return _sse_response(busy_gen())

    # 2) Security guard before any fetch — rejection → one error event, release lock.
    sec_msg = _security_check(input_path)
    if sec_msg is not None:
        _job_lock.release()

        def sec_gen():
            yield ": connected\n\n"
            yield _format_sse("error", {"subtype": "security", "message": sec_msg})
        return _sse_response(sec_gen())

    # 3) Accepted — spawn daemon worker draining a bounded queue.
    q = queue.Queue(maxsize=1000)
    cancel_event = threading.Event()
    worker = threading.Thread(target=_run_worker, args=(input_path, q, cancel_event), daemon=True)
    worker.start()

    def generator():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    item = q.get(timeout=15)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue
                if item is None:
                    break
                yield item
        except GeneratorExit:
            cancel_event.set()
            raise
        finally:
            cancel_event.set()

    return _sse_response(generator())


def _sse_response(gen):
    """Build the text/event-stream Response with exact headers (contract §3)."""
    resp = Response(gen, mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache, no-transform"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    # Do NOT set Content-Length; do NOT apply compression.
    return resp


@app.route("/result/raw")
def result_raw():
    """Serve full whitelisted file text inline for client copy (contract §1.4)."""
    which = request.args.get("which")
    if which == "uncompressed":
        filename = UNCOMPRESSED_FILE
    elif which == "compressed":
        filename = COMPRESSED_FILE
    else:
        abort(400)

    safe_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(safe_path):
        abort(404)

    text = safe_file_read(safe_path)
    # mimetype="text/plain" — Flask appends "; charset=utf-8" itself. Passing the
    # charset here too would double it ("text/plain; charset=utf-8; charset=utf-8"),
    # violating the exact Content-Type required by the contract (§3).
    return Response(text, mimetype="text/plain")


@app.route("/download")
def download():
    filename = request.args.get("filename")
    if not filename:
        abort(404)

    # C1 fix: Only allow downloading specific output files from the output directory
    basename = os.path.basename(filename)
    if basename not in ALLOWED_DOWNLOAD_FILES:
        abort(403)

    safe_path = os.path.join(OUTPUT_DIR, basename)
    if not os.path.isfile(safe_path):
        abort(404)

    return send_file(safe_path, as_attachment=True)


if __name__ == "__main__":
    # Bind to localhost only; threaded so a live SSE stream never blocks other endpoints.
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
