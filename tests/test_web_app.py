#!/usr/bin/env python3
"""Pytest suite for the Conduit Flask web app (extras/web_app.py).

Runs entirely against Flask's `app.test_client()` with every network-touching
processor MONKEYPATCHED, so NO real HTTP/crawl ever happens. Asserts the
machine interface defined in the build contract (/tmp/conduit_contract.md):
endpoints, exact SSE event JSON, the no-JS POST result rendering, the result
classifier, the security invariants, and the /download // /result/raw whitelist.

Import approach (per the contract §0 and the test brief): put BOTH the repo root
AND extras/ on sys.path, then `import web_app`. The processors are imported INTO
the web_app namespace (`from onefilellm import process_github_repo, ...`), so we
monkeypatch the names on the `web_app` module object, not on `onefilellm`.

Run from the repo root:
    python -m pytest tests/test_web_app.py -q
"""

import os
import sys
import importlib

import pytest

# ---------------------------------------------------------------------------
# Import web_app with repo root + extras/ on sys.path. web_app captures
# OUTPUT_DIR = os.path.abspath(".") at IMPORT time, so we chdir into a private
# temp dir first and then pin OUTPUT_DIR to it. compute_metrics() writes the two
# output files with bare relative names (process cwd), while /download and
# /result/raw read from OUTPUT_DIR; keeping cwd == OUTPUT_DIR makes them agree.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTRAS = os.path.join(_REPO_ROOT, "extras")
for _p in (_REPO_ROOT, _EXTRAS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# Fixed filenames from the contract whitelist.
UNCOMPRESSED = "uncompressed_output.txt"
COMPRESSED = "compressed_output.txt"

# A GitHub repo URL that passes the SSRF guard and dispatches to process_github_repo.
GH_URL = "https://github.com/jimmc414/onefilellm"

# A success-shaped <source>. NOTE: the classifier's empty backstop rejects any
# source whose stripped token count is < 5. The brief's literal "hello world
# body" tokenizes to only 3 tokens, which classify() (correctly, per contract
# §7.1) would label "empty". So the body is padded with enough real words to
# exceed the threshold while STILL containing the substring "hello world body"
# so the preview-text assertions remain meaningful.
SUCCESS_BODY = (
    "hello world body with plenty of additional readme words here "
    "to exceed the five token empty backstop threshold easily now"
)
SUCCESS_SOURCE = (
    '<source type="github_repository" url="%s">'
    '<file path="README.md">%s</file></source>' % (GH_URL, SUCCESS_BODY)
)


@pytest.fixture(scope="session")
def web_app_module(tmp_path_factory):
    """Import web_app once, with cwd + OUTPUT_DIR pinned to a private temp dir."""
    workdir = tmp_path_factory.mktemp("ofllm_webapp_cwd")
    old_cwd = os.getcwd()
    os.chdir(str(workdir))
    try:
        if "web_app" in sys.modules:
            web_app = importlib.reload(sys.modules["web_app"])
        else:
            web_app = importlib.import_module("web_app")
        # Pin reads (OUTPUT_DIR) to the same dir writes (cwd) land in.
        web_app.OUTPUT_DIR = str(workdir)
        web_app.app.config["TESTING"] = True
        yield web_app
    finally:
        os.chdir(old_cwd)


@pytest.fixture
def client(web_app_module):
    """A fresh Flask test client per test."""
    return web_app_module.app.test_client()


@pytest.fixture(autouse=True)
def clean_outputs_and_lock(web_app_module):
    """Per-test isolation: clear output files before/after and free the lock.

    Several tests intentionally write/remove the two whitelisted output files in
    OUTPUT_DIR; wipe them around every test so a leftover file can't make a 404
    test pass for the wrong reason. Also defensively release the single-flight
    lock in case a test left it held.
    """
    out_dir = web_app_module.OUTPUT_DIR

    def _wipe():
        for name in (UNCOMPRESSED, COMPRESSED):
            p = os.path.join(out_dir, name)
            try:
                os.remove(p)
            except OSError:
                pass

    _wipe()
    yield
    _wipe()
    if web_app_module._job_lock.locked():
        try:
            web_app_module._job_lock.release()
        except RuntimeError:
            pass


# ===========================================================================
# GET /  — app shell
# ===========================================================================
def test_get_index_renders_shell(client):
    """GET / → 200 and the SSE shell renders with the #cmd prompt input."""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # The command input and its form are the load-bearing shell markers (§8.3).
    assert 'id="cmd"' in body
    assert 'name="input_path"' in body
    assert 'id="prompt-form"' in body
    # No-JS result block must be absent on a bare GET (result=None).
    assert 'id="noscript-result"' not in body


# ===========================================================================
# POST /  — synchronous no-JS fallback
# ===========================================================================
def test_post_index_success_renders_result(client, web_app_module):
    """POST / success: a monkeypatched processor → 200 with tokens, both
    /download links, and the preview text in the no-JS result block (§1.2)."""
    web_app_module.process_github_repo = lambda url: SUCCESS_SOURCE

    resp = client.post("/", data={"input_path": GH_URL})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    # The success no-JS block must show the token-count labels...
    assert "Uncompressed tokens:" in body
    assert "Compressed tokens:" in body
    assert "Estimated model tokens:" in body
    # ...both /download links (whitelisted filenames, unchanged §1.5)...
    assert "/download?filename=uncompressed_output.txt" in body
    assert "/download?filename=compressed_output.txt" in body
    # ...and the preview text (the wrapped source contains the file body).
    # Jinja HTML-escapes the <pre><code> content, so the wrapper tag appears as
    # &lt;onefilellm_output&gt;; the plain-text body passes through verbatim.
    assert "hello world body" in body
    assert "&lt;onefilellm_output&gt;" in body
    # Output files were written to OUTPUT_DIR by compute_metrics().
    assert os.path.isfile(os.path.join(web_app_module.OUTPUT_DIR, UNCOMPRESSED))
    assert os.path.isfile(os.path.join(web_app_module.OUTPUT_DIR, COMPRESSED))


def test_post_index_security_block_url(client, web_app_module):
    """POST / with a loopback URL → security notice shown, NO processor called."""
    called = {"hit": False}

    def _boom(url):
        called["hit"] = True
        raise AssertionError("processor must not run on a blocked input")

    # Guard every dispatchable processor: none may be invoked.
    for name in (
        "process_github_repo", "process_github_pull_request", "process_github_issue",
        "process_arxiv_pdf", "fetch_youtube_transcript", "process_doi_or_pmid",
        "crawl_and_extract_text",
    ):
        setattr(web_app_module, name, _boom)

    resp = client.post("/", data={"input_path": "http://127.0.0.1"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'data-error="security"' in body
    assert "Blocked by the security policy" in body
    assert called["hit"] is False


def test_post_index_security_block_local_path(client, web_app_module):
    """POST / with a local filesystem path → security notice, NO processor."""
    called = {"hit": False}

    def _boom(url):
        called["hit"] = True
        raise AssertionError("processor must not run on a local path")

    for name in (
        "process_github_repo", "process_doi_or_pmid", "crawl_and_extract_text",
    ):
        setattr(web_app_module, name, _boom)

    resp = client.post("/", data={"input_path": "/etc/passwd"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'data-error="security"' in body
    assert called["hit"] is False


# ===========================================================================
# Result classifier (contract §7.1) — exercised directly.
# ===========================================================================
def test_classify_success_shape(web_app_module):
    """A real <file> body over the token threshold → ('success', None)."""
    status, msg = web_app_module.classify(SUCCESS_SOURCE)
    assert status == "success"
    assert msg is None


def test_classify_processing_error_shape(web_app_module):
    """Source-level <error> (after page/file strip) → ('processing', message).

    The error text must clear the 5-token empty backstop (which runs FIRST in
    classify, contract §7.1) to reach the <error> branch; a too-short error is
    indistinguishable from empty by design — see
    test_classify_short_error_is_empty_by_backstop below."""
    msg_text = (
        "No transcript was found for this video because captions are "
        "disabled by the uploader entirely"
    )
    src = (
        '<source type="youtube_transcript" url="https://youtu.be/x">'
        '<error>%s</error></source>' % msg_text
    )
    status, msg = web_app_module.classify(src)
    assert status == "processing"
    assert msg == msg_text


def test_classify_short_error_is_empty_by_backstop(web_app_module):
    """Documents contract §7.1 precedence: the empty backstop (<5 tokens) runs
    BEFORE the <error> search, so a very short error like 'No transcript found'
    (3 tokens) classifies as 'empty', NOT 'processing'. This is intended by the
    contract algorithm, not a bug; recorded so the behavior is pinned."""
    src = (
        '<source type="youtube_transcript" url="https://youtu.be/x">'
        '<error>No transcript found</error></source>'
    )
    status, msg = web_app_module.classify(src)
    assert status == "empty"
    assert msg is None


def test_classify_empty_shape(web_app_module):
    """A source with no extractable content → ('empty', None)."""
    src = '<source type="github_repository" url="https://github.com/x/y"></source>'
    status, msg = web_app_module.classify(src)
    assert status == "empty"
    assert msg is None


def test_classify_partial_crawl_is_success(web_app_module):
    """A crawl with one timed-out <page> plus a real page → ('success', None).

    The source-level <error> search must run AFTER stripping <page> subtrees, so
    a per-page <error> does NOT downgrade the whole result (contract §7.1)."""
    src = (
        '<source type="web_crawl" base_url="https://docs.example.com">'
        '<page url="a"><error>Timeout</error></page>'
        '<page url="b">lots of real text content here to exceed the token '
        'threshold with many additional words appended for good measure</page>'
        '</source>'
    )
    status, msg = web_app_module.classify(src)
    assert status == "success"
    assert msg is None


# ===========================================================================
# GET /stream  — SSE progress
# ===========================================================================
def test_stream_success(client, web_app_module):
    """A fast processor → body has `event: stage`, a terminal `event: done`
    with the metrics JSON, the right headers, and NO `event: error` (§3, §4)."""
    web_app_module.process_github_repo = lambda url: SUCCESS_SOURCE

    resp = client.get("/stream", query_string={"input": GH_URL})
    assert resp.status_code == 200
    # Exact streaming headers (contract §3).
    assert resp.headers.get("Content-Type") == "text/event-stream; charset=utf-8"
    assert resp.headers.get("Cache-Control") == "no-cache, no-transform"
    assert resp.headers.get("X-Accel-Buffering") == "no"

    body = resp.get_data(as_text=True)
    assert "event: stage" in body
    assert "event: done" in body
    assert "event: error" not in body
    # The terminal done event carries the metrics JSON.
    assert "uncompressed_tokens" in body
    assert "estimated_model_tokens" in body
    assert '"status":"success"' in body
    # Lock must be released once the worker has sentinelled the queue.
    assert web_app_module._job_lock.locked() is False


def test_stream_security(client, web_app_module):
    """GET /stream with a loopback host → `event: error` subtype 'security'."""
    resp = client.get("/stream", query_string={"input": "http://localhost"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "event: error" in body
    # Compact JSON: no space after the colon.
    assert '"subtype":"security"' in body
    # The security path must release the lock (it never started a job).
    assert web_app_module._job_lock.locked() is False


def test_stream_busy(client, web_app_module):
    """With the single-flight lock already held → `event: error` subtype 'busy'
    and NO job is started (contract §1.3 step 1 / §2.1)."""
    called = {"hit": False}

    def _boom(url):
        called["hit"] = True
        raise AssertionError("no worker should run while the lock is held")

    web_app_module.process_github_repo = _boom

    acquired = web_app_module._job_lock.acquire(blocking=False)
    assert acquired is True
    try:
        resp = client.get("/stream", query_string={"input": GH_URL})
        body = resp.get_data(as_text=True)
        assert "event: error" in body
        assert '"subtype":"busy"' in body
        assert called["hit"] is False
    finally:
        web_app_module._job_lock.release()


# ===========================================================================
# GET /result/raw  — inline copy/preview fetch
# ===========================================================================
def test_result_raw_uncompressed_ok(client, web_app_module):
    """?which=uncompressed → 200 text/plain with the file's exact content (§1.4)."""
    content = "RAW UNCOMPRESSED CONTENT for copy\nsecond line"
    path = os.path.join(web_app_module.OUTPUT_DIR, UNCOMPRESSED)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    resp = client.get("/result/raw", query_string={"which": "uncompressed"})
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type") == "text/plain; charset=utf-8"
    # Inline, never an attachment (contract §1.4 / §3).
    assert "attachment" not in (resp.headers.get("Content-Disposition") or "")
    assert resp.get_data(as_text=True) == content


def test_result_raw_compressed_ok(client, web_app_module):
    """?which=compressed → 200 with the compressed file's content."""
    content = "RAW COMPRESSED CONTENT"
    path = os.path.join(web_app_module.OUTPUT_DIR, COMPRESSED)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    resp = client.get("/result/raw", query_string={"which": "compressed"})
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == content


def test_result_raw_bogus_which_400(client):
    """Any unrecognized ?which value → 400 (contract §1.4)."""
    resp = client.get("/result/raw", query_string={"which": "bogus"})
    assert resp.status_code == 400


def test_result_raw_missing_file_404(client, web_app_module):
    """Whitelisted which= but the file is absent → 404 (contract §1.4)."""
    # autouse fixture already wiped both files; assert absence then hit endpoint.
    path = os.path.join(web_app_module.OUTPUT_DIR, UNCOMPRESSED)
    assert not os.path.isfile(path)
    resp = client.get("/result/raw", query_string={"which": "uncompressed"})
    assert resp.status_code == 404


# ===========================================================================
# GET /download  — whitelist (UNCHANGED, contract §1.5 / §5)
# ===========================================================================
def test_download_whitelisted_ok(client, web_app_module):
    """?filename=uncompressed_output.txt (present) → 200 attachment."""
    path = os.path.join(web_app_module.OUTPUT_DIR, UNCOMPRESSED)
    with open(path, "w", encoding="utf-8") as f:
        f.write("downloadable body")

    resp = client.get("/download", query_string={"filename": UNCOMPRESSED})
    assert resp.status_code == 200
    assert resp.get_data() == b"downloadable body"
    assert "attachment" in (resp.headers.get("Content-Disposition") or "")


def test_download_traversal_403(client):
    """A path-traversal filename → 403 (basename not in whitelist)."""
    resp = client.get("/download", query_string={"filename": "../../etc/passwd"})
    assert resp.status_code == 403


def test_download_whitelisted_but_missing_404(client, web_app_module):
    """Whitelisted name but the file is absent → 404 (not 403)."""
    # Use the compressed slot; the autouse fixture guarantees it's wiped.
    path = os.path.join(web_app_module.OUTPUT_DIR, COMPRESSED)
    assert not os.path.isfile(path)
    resp = client.get("/download", query_string={"filename": COMPRESSED})
    assert resp.status_code == 404


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
