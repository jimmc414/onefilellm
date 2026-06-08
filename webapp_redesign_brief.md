# Design Brief — OneFileLLM Web App Redesign

**Artifact under redesign:** `extras/web_app.py` (a Flask web interface for OneFileLLM)
**Prepared for:** the designer producing `redesign_onefilellm_webapp_py.md`
**Date:** 2026-06-07

---

## 0. How this document works (read first)

This is a **three-party handoff**. Please respect the boundaries:

1. **This brief** (what you're reading) gives you complete context: the product, the
   current web app, the backend contract you must design against, the agreed direction,
   and an exact spec for what you must deliver.
2. **You, the designer**, produce a single file named **`redesign_onefilellm_webapp_py.md`**.
   That file is a *design specification*, not prose — see [§9](#9-the-deliverable) for its
   required contents and format.
3. **Claude Code** (an AI coding agent) will read your `redesign_onefilellm_webapp_py.md`
   and implement it directly into `extras/web_app.py` (optionally splitting out
   `templates/` and `static/` files).

> **Critical implication:** your output is consumed by an automated coding agent, not a
> human who can fill gaps with judgment. Be **literal and complete**. Specify exact hex
> values, pixel/rem sizes, font stacks, copy strings, every UI state, and the exact
> backend data each element binds to. Avoid "make it modern," "add some spacing,"
> "use a nice green." If a value is unspecified, the implementer will guess — and guess
> inconsistently. Ambiguity is the main failure mode to avoid.

---

## Table of contents

1. [Product context](#1-product-context)
2. [The current web app (what we're replacing)](#2-the-current-web-app)
3. [The backend contract (design against this)](#3-the-backend-contract)
4. [Agreed direction (decisions already made)](#4-agreed-direction)
5. [Goals, problems, and success criteria](#5-goals-problems-success)
6. [Visual system — starting point](#6-visual-system)
7. [Screens, states, and components to design](#7-screens-states-components)
8. [Non-functional requirements](#8-non-functional-requirements)
9. [The deliverable — what `redesign_onefilellm_webapp_py.md` must contain](#9-the-deliverable)
10. [Constraints & non-goals](#10-constraints-non-goals)
11. [Appendix — reference material](#11-appendix)

---

## 1. Product context

**OneFileLLM** is a developer tool that aggregates content from many sources into a single,
structured, LLM-ready text file. You point it at a GitHub repo, an ArXiv paper, a YouTube
URL, a documentation site, a DOI, a local folder, etc., and it returns one big blob of
XML-tagged text you can paste into an LLM, along with token counts.

The primary interface is a **command-line tool** (`onefilellm.py`) with a polished
terminal UI built on the [Rich](https://github.com/Textualize/rich) library (panels,
progress bars, green/cyan syntax coloring). There is also a small, neglected **Flask web
app** (`extras/web_app.py`) that exposes a subset of the same functionality in a browser.
**That web app is what you are redesigning.**

**Who uses the web app:** a single developer, running it locally on their own machine
(`http://127.0.0.1:5000`). It is explicitly **localhost-bound and single-user**. There are
no accounts, no auth, no multi-tenant concerns. Think "local devtool dashboard," not
"public SaaS product."

**Brand identity to inherit:** the CLI's Rich TUI is the existing visual language —
dark terminal, monospace, **bright green** primary accent, **cyan** secondary accent,
boxed panels. The web redesign should feel like a natural sibling of that tool (see
[§4](#4-agreed-direction) and [§6](#6-visual-system)).

---

## 2. The current web app

`extras/web_app.py` is ~175 lines: a single Flask file with one **inline HTML template**
(a Python string), two routes, and no `static/` or `templates/` directory.

### 2.1 What it does today

- **`GET /`** — renders a near-empty page: a title, one text input, a "Process" button.
- **`POST /`** — takes the single input string, auto-detects its type, calls the matching
  backend function **synchronously**, writes two files to disk, copies text to the
  clipboard **server-side** (a bug — see below), and re-renders the same page with the
  full output dumped into a `<pre>` block plus two token counts and two download links.
- **`GET /download?filename=...`** — serves one of exactly two whitelisted files
  (`uncompressed_output.txt`, `compressed_output.txt`) as an attachment.

### 2.2 What it looks like today (verbatim layout)

```
┌──────────────────────────────────────────────────────────┐
│  1FileLLM Web Interface              (h1, sans-serif)      │
│                                                            │
│  Enter a URL, DOI, or PMID:                                │
│  ┌──────────────────────────────────────────┐ [Process]   │
│  │ e.g. https://github.com/jimmc414/1filellm │             │
│  └──────────────────────────────────────────┘             │
│                                                            │
│  ── after submit ────────────────────────────────────     │
│  Processed Output                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ <source type="github_repository" url="...">          │ │
│  │ <file path="README.md"> ...the ENTIRE output, raw,   │ │
│  │ unstyled, in one <pre> that can be 100k+ tokens...   │ │
│  └──────────────────────────────────────────────────────┘ │
│  Token Counts                                              │
│  Uncompressed Tokens: 142803                               │
│  Compressed Tokens: 78420                                  │
│  Download Uncompressed Output | Download Compressed Output │
└──────────────────────────────────────────────────────────┘
```

Styling is ~8 lines of CSS: `font-family: sans-serif; margin: 2em;` a grey `<pre>`. No
color system, no states, no responsive behavior, no dark mode, no iconography.

### 2.3 Problems with the current design (the brief's motivation)

These are the concrete failures your redesign must fix:

| # | Problem | Why it matters |
|---|---------|----------------|
| P1 | **No feedback during processing.** The POST blocks; a deep crawl or large repo can take **minutes** while the page simply hangs with a spinner-less frozen tab. | This is the single worst UX issue. Users can't tell if it's working, stuck, or dead. |
| P2 | **Output is dumped raw into one `<pre>`.** Outputs are routinely 50k–300k+ tokens (multi-megabyte). | The browser chokes, the page becomes unscrollable, nothing is scannable. |
| P3 | **"Copy to clipboard" runs server-side** (`pyperclip.copy` in the request handler). | It copies to the *server's* clipboard, not the user's browser. On a headless/remote host it does nothing or errors. Must move to client-side. |
| P4 | **Only one input type entry, no discoverability.** A single text box with one placeholder. | Users don't know it accepts ArXiv, YouTube, DOIs, docs sites, etc. |
| P5 | **No error states.** Errors are returned as a raw string in the same `<pre>`. | No visual distinction between success and failure; backend `<error>` XML tags render as plain text. |
| P6 | **No visual identity.** Doesn't resemble the polished Rich CLI at all. | Feels abandoned (its own README calls it "not actively maintained"). |
| P7 | **No metrics context.** Two bare integers. The CLI shows richer stats (sources processed, output size, *estimated model* token count). | Users lose useful information the backend already computes. |

---

## 3. The backend contract

**This section is the most important for producing an implementable design.** Everything
the UI shows must bind to data the backend actually produces, and the design must respect
how the backend behaves. Design something the backend can't deliver and the spec becomes
un-buildable.

### 3.1 Accepted inputs (auto-detected from one string)

The backend detects input type from the raw string. The web app currently supports this
subset (all detected automatically — the user does **not** pick a type):

| Input type | Trigger / example | Backend function | Typical duration |
|---|---|---|---|
| GitHub repository | `https://github.com/owner/repo` | `process_github_repo` | seconds–minutes (repo size) |
| GitHub pull request | `https://github.com/owner/repo/pull/123` | `process_github_pull_request` | seconds |
| GitHub issue | `https://github.com/owner/repo/issues/123` | `process_github_issue` | seconds |
| ArXiv paper | `https://arxiv.org/abs/2301.00001` | `process_arxiv_pdf` | seconds |
| YouTube transcript | `https://www.youtube.com/watch?v=...` | `fetch_youtube_transcript` | seconds |
| Documentation site (web crawl) | any other `http(s)://` URL | `crawl_and_extract_text` | **seconds–many minutes** (up to 1000 pages) |
| DOI or PMID | `10.1234/foo` or a bare number like `38122860` | `process_doi_or_pmid` | seconds (best-effort, often fails) |

**Explicitly blocked in the web app** (do not design entry points for these):
- **Local folder/file paths** — rejected for security (path traversal / SSRF). The CLI
  supports them; the web app must not.
- **Private/internal URLs** — an SSRF guard (`_is_safe_url`) rejects `localhost`, private
  IP ranges, and cloud metadata endpoints. Design an error state for "URL rejected by
  security policy."

**Optional new input mode you may propose** (feature parity with the CLI, not required):
a "paste raw text" mode. The CLI accepts pasted/stdin text and can be told its format via
`--format {text,markdown,json,html,yaml,doculing,markitdown}`. If you propose this, design
a format-override control; otherwise omit it. (The current web app has no such mode.)

### 3.2 The processing model — synchronous and slow

The backend functions are **blocking and opaque**: you call one, it works for anywhere from
a second to several minutes, then returns a finished string. They do **not** currently emit
incremental progress.

Because the agreed scope is a **UX overhaul that permits backend changes** (see
[§4](#4-agreed-direction)), the redesign should introduce real progress feedback. You must
design for what is *realistically* achievable; here are the honest options for the
implementer, so you design an experience that can actually be built:

- **Staged / indeterminate progress (recommended baseline).** The handler can emit coarse
  stage transitions — e.g. *detecting input → fetching → extracting → tokenizing → done* —
  via **Server-Sent Events** (Flask streams a `text/event-stream` generator; the browser
  uses native `EventSource`, no dependencies, works offline). Within a stage, show an
  indeterminate/animated indicator plus an **elapsed timer**, not a fake percentage.
- **Determinate progress where data exists.** The web crawler knows pages-fetched and a
  page cap, so a crawl *can* show `47 / 1000 pages` if wired up. Design a determinate
  variant for crawls and treat other sources as indeterminate. Mark this clearly so the
  implementer knows it's source-dependent.
- **Cancellation** is desirable (a long crawl should be abortable). Design a Cancel
  affordance; note in your spec that it requires backend support (job/abort handling) and
  may land in a later pass if the implementer defers it.

> Design the progress experience to **degrade gracefully**: if only coarse stages are
> available, it must still feel honest and alive (stage label + elapsed time + animated
> accent), never a frozen tab (P1).

### 3.3 The output — structured, large, XML-like

On success the backend returns a single string of **XML-like tagged text**. It is *not*
strict XML and should be treated as text with recognizable tags. Shape:

```xml
<source type="github_repository" url="https://github.com/owner/repo">
<file path="README.md">
...file contents, unescaped...
</file>
<file path="src/main.py">
...
</file>
</source>
```

- Different sources use different tag attributes: `type="youtube_transcript" url=...`,
  `type="arxiv" url=...`, `type="web_crawl" base_url=...`, `type="local_folder" path=...`,
  etc. (the web app won't emit `local_folder`).
- A **single** web-app request yields **one** `<source>…</source>` block. (The CLI wraps
  multiple sources in a `<onefilellm_output>…</onefilellm_output>` root; design your result
  viewer to tolerate both a bare `<source>` and a wrapped root.)
- **Errors** come back as `<source type="..." ...><error>message</error></source>` — your
  result/error states should detect an `<error>` tag and render it as a failure, not as
  content.
- **Size:** routinely tens of thousands to **hundreds of thousands of tokens** (multiple
  MB). **You must not assume the whole thing can be dumped into the DOM** (P2). Design for:
  - a **structured overview** parsed cheaply from the tags (list/tree of sources and
    `<file path="...">` entries with per-file byte/line sizes), and
  - a **bounded raw preview** (e.g. first ~100–200 KB with a "showing first X of Y" notice),
    relying on **Download** and **Copy** for the complete payload.
  - Per-file *token* counts are **not** computed by the backend today — don't show them
    unless you also specify the backend change to compute them (optional, likely out of scope).

### 3.4 Metrics the backend provides

After processing, these values are available (mirror the CLI's summary — see
[§11.4](#114-cli-summary-block)):

- **Uncompressed token count** (tiktoken `cl100k_base`).
- **Compressed token count** — a second pass (`preprocess_text`) strips whitespace/stopwords.
- **Estimated model token count** = `round(uncompressed × 1.37)` — the constant
  `TOKEN_ESTIMATE_MULTIPLIER = 1.37` accounts for tag/format overhead. The CLI surfaces this
  as *"Estimated Model Token Count (incl. overhead)."* Worth showing; it's the number users
  actually care about.
- **Final output size** in KB.
- **Sources processed** count (always 1 in the current single-input web app, but design the
  metrics panel so it reads naturally and could show >1 if multi-input is added later).

### 3.5 Outputs to download / copy

- Two server-side files exist after a run: `uncompressed_output.txt` and
  `compressed_output.txt`, both served via `GET /download?filename=...` (whitelisted).
- **Copy must become client-side** (fix P3): the browser writes to the user's clipboard via
  `navigator.clipboard.writeText`. For very large outputs, design a brief *"preparing
  copy…"* state — the implementer may need to fetch the file text before writing it.
- Provide **separate copy and download affordances for uncompressed vs compressed** (4 actions
  total, grouped clearly), since both are legitimately useful.

### 3.6 Endpoints summary (current)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | render the app shell |
| POST | `/` | process one input, return result (synchronous today) |
| GET | `/download?filename=` | download a whitelisted output file |

The implementer may add endpoints (e.g. `GET /stream` for SSE progress, `GET /result/raw`
for copy/preview fetching). If your design depends on new endpoints, **name them and
describe their payloads** in your spec so the implementer builds them.

---

## 4. Agreed direction

These decisions are **already made** by the product owner. Design within them; do not
re-litigate them in your spec.

1. **Scope: full UX overhaul (backend changes permitted).** You are not limited to a
   visual reskin. Fix the real problems — progress feedback (P1), large-output handling
   (P2), client-side copy (P3) — even where that requires backend/endpoint changes. Specify
   those backend changes in your deliverable.
2. **Tech & offline posture: self-contained and offline-safe.** Vanilla HTML/CSS/JS. **No
   CDN, no build step, no npm.** Everything inline or vendored locally so it runs with zero
   internet (OneFileLLM has an `OFFLINE_MODE` and is frequently used air-gapped). Icons must
   be **inline SVG**. Fonts must be **system stacks** (no web-font downloads). The only
   Python dependency remains **Flask**. If you want a micro-library (e.g. a tiny SSE helper),
   it must be small enough to **vendor as a local file** and you must say so.
3. **Visual style: terminal/developer console, elevated with modern SaaS polish (hybrid).**
   Keep the developer-terminal DNA — dark-first, monospace for data/output, green/cyan
   accents echoing the Rich CLI — but execute it with modern-SaaS craft: deliberate spacing,
   soft elevation, rounded surfaces, smooth (reduced-motion-aware) transitions, light/dark
   themes, and a coherent token system. Think *Warp / Vercel / Linear / Raycast* — polished
   product surfaces that still feel native to developers. Not a retro CRT skin; not a generic
   marketing landing page. See [§6](#6-visual-system).
4. **Audience: local single-user tool.** Localhost, one user, no auth/accounts. A
   **lightweight, optional session history** (recent inputs this session, in-memory or
   `localStorage`) is welcome but must stay simple. No sharing, no persistence guarantees,
   no settings server.

---

## 5. Goals, problems, success criteria

### 5.1 Primary goals

- **G1.** Make long jobs feel alive and trustworthy — never a frozen tab (fixes P1).
- **G2.** Turn the giant raw blob into something scannable and navigable (fixes P2).
- **G3.** Make every supported input type discoverable from the empty state (fixes P4).
- **G4.** Correct, client-side copy + clean downloads for both output variants (fixes P3).
- **G5.** Give the app a real identity that's unmistakably a sibling of the Rich CLI
  (fixes P6), executed with modern polish.
- **G6.** Surface the useful metrics (incl. estimated model tokens) with context (fixes P7).
- **G7.** Honest, distinct error states for security rejections, processing failures, and
  `<error>`-tagged backend responses (fixes P5).

### 5.2 Definition of done (for the eventual implementation)

The implemented redesign should let a user:
1. Land on a clear empty state that *teaches* what can be pasted (examples per type).
2. Submit an input and **immediately** see staged progress with an elapsed timer (and a
   page count for crawls), with a Cancel affordance.
3. On success, see a **metrics summary**, a **structured overview** of sources/files, and a
   **bounded, readable preview** — not a multi-MB dump.
4. **Copy** (uncompressed or compressed) to *their own* clipboard, and **download** either
   file, with clear feedback.
5. On any failure, see a clearly styled error with the message and (where relevant) a hint.
6. Toggle light/dark; use the whole thing by keyboard; have it work offline.

---

## 6. Visual system — starting point

This is a **starting palette to refine, not a finished system.** Your deliverable must
return a *complete, finalized* token system (every value locked). Use this to anchor the
hybrid "terminal × SaaS" direction and keep brand continuity with the Rich CLI.

### 6.1 Suggested color tokens (dark-first; provide a light counterpart)

| Token | Suggested dark value | Role |
|---|---|---|
| `--bg` | `#0B0E14` | app background (deep terminal charcoal) |
| `--surface` | `#11161F` | cards / panels (slightly lifted) |
| `--surface-2` | `#161B22` | nested surfaces, code/preview wells |
| `--border` | `#283041` | hairline separators, card edges |
| `--text` | `#E6EDF3` | primary text |
| `--text-muted` | `#8B949E` | secondary text, metadata |
| `--accent` | `#3FB950` (hover `#56D364`) | **primary green** — actions, success, "alive" state |
| `--accent-2` | `#39C5CF` | **cyan** — links, info, secondary highlights |
| `--info` | `#2F81F7` | informational emphasis |
| `--warn` | `#D29922` | warnings (e.g. truncated output, best-effort DOI) |
| `--danger` | `#F85149` | errors, security rejections |
| `--focus-ring` | `#56D364` @ 2px | keyboard focus (must be visible on all surfaces) |

The green/cyan pairing intentionally echoes the Rich CLI's `bright_green` + `cyan`. Provide
a **light theme** with equivalent roles (AA contrast in both). Dark is the default.

### 6.2 Typography (system stacks only — offline)

- **Monospace** (data, output, tokens, the input field's value, terminal chrome):
  `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`.
- **Sans / UI** (labels, buttons, headings, body chrome — the "SaaS" layer):
  `system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
- Define a full type scale (sizes, weights, line-heights) in your spec. The mono/sans split
  *is* the hybrid: terminal where it's data, clean sans where it's product chrome.

### 6.3 Form, motion, spacing

- **Spacing:** a 4px base scale (4/8/12/16/24/32/48…). Generous but not airy — developer-dense.
- **Radius:** ~6–8px on cards/inputs (modern, not pill-round; not sharp terminal corners).
  Chips/badges may be pill.
- **Elevation:** prefer border + subtle shadow on dark; soft shadows on light. Keep it
  restrained.
- **Motion:** purposeful and quick (120–200ms) — accent shimmer on progress, a blinking
  caret as a terminal nod, smooth state transitions. **All motion must respect
  `prefers-reduced-motion`** (provide static fallbacks).
- **A terminal signature element is encouraged** (e.g. a `>` prompt glyph in the input, a
  faux status line, a blinking caret) — used as tasteful seasoning, not a full skeuomorphic
  terminal.

---

## 7. Screens, states, and components

Your spec must cover **every** state below (not just the happy path). Treat each as a thing
to draw and annotate.

### 7.1 App shell

- **Header / status bar:** product name/logo (sibling of the CLI), theme toggle, an
  **offline/online indicator**, and version. A faux terminal "status line" treatment fits
  the hybrid.
- **Footer (optional):** minimal — links to repo/docs, keyboard-shortcut hint.

### 7.2 Input / command bar (the centerpiece)

- A prominent single input with a `>` prompt glyph and blinking caret (terminal nod).
- **Live input-type detection:** as the user types/pastes, show a badge for the detected
  type (GitHub repo / PR / issue, ArXiv, YouTube, Docs crawl, DOI/PMID) or a neutral
  "will crawl as docs site" for generic URLs. Show an inline rejection hint for blocked
  inputs (local paths, private URLs) *before* submit where detectable.
- Primary **Process** action (green). Enter-to-submit. Disabled/empty handling.
- **Empty state = teaching surface (G3):** a compact gallery of the supported input types,
  each with a real example users can click to populate (see [§11.2](#112-input-examples)).

### 7.3 Processing / progress state (G1)

- Staged progress with stage label + **elapsed timer**; indeterminate animation by default,
  **determinate page count for crawls** (`N / max pages`).
- **Cancel** affordance (note backend dependency).
- A "console log" treatment for stage transitions fits the aesthetic (append-only lines).
- Must never look frozen; must survive multi-minute jobs.

### 7.4 Result state (G2, G6)

- **Metrics panel:** uncompressed tokens, compressed tokens, **estimated model tokens
  (×1.37)**, output size (KB), sources processed, elapsed time. Make the *estimated model*
  number the hero metric.
- **Structured overview:** a collapsible tree/list of the `<source>` and `<file path="...">`
  entries parsed from the output, with per-file size (bytes/lines). This is how users
  navigate a huge result.
- **Bounded raw preview:** monospace, syntax-tinted if cheap, **truncated** with a clear
  "showing first X of Y — download for full" notice (P2). Optional toggle between
  "structured" and "raw" views.
- **Action bar:** Copy uncompressed · Copy compressed · Download uncompressed · Download
  compressed — each with success feedback ("Copied!", "preparing copy…" for large payloads).

### 7.5 Error states (G7) — design all three

1. **Security rejection** (blocked URL / local path) — `--danger`, explains the policy,
   non-alarming.
2. **Processing failure** (exception or `<error>` tag in the response) — shows the message,
   offers retry, suggests likely causes where known (e.g. DOI is "best-effort").
3. **Empty / no-content result** — e.g. a transcript-less video or an empty crawl.

### 7.6 Optional, if you choose to spec them

- Session history (recent inputs this session) in a side rail or under the input.
- "Paste raw text" input mode with `--format` override (feature parity; see [§3.1](#31-accepted-inputs)).
- Light theme as a first-class deliverable (required if you adopt theme toggle — and you should).

### 7.7 Responsive

Desktop-first (it's a local devtool), but must remain usable down to a narrow window
(~480px): the input bar, progress, metrics, and actions should reflow sanely. Specify
breakpoints and reflow behavior.

---

## 8. Non-functional requirements

- **Accessibility: WCAG 2.1 AA.** AA contrast in both themes; visible focus rings on every
  interactive element; full keyboard operability (submit, cancel, copy, download, expand
  tree, toggle theme); correct ARIA for the live progress region (`aria-live`) and for
  async status updates; `prefers-reduced-motion` honored. Specify all of this concretely.
- **Offline-first:** zero network dependencies at runtime. No CDN fonts, scripts, or styles.
- **Performance with huge outputs:** the page must stay responsive when the result is
  multi-MB. Specify the truncation threshold and the structured-overview approach so the DOM
  never holds the entire blob unbounded.
- **No new heavy dependencies:** Flask only on the Python side; vanilla on the front end.
  Any vendored micro-helper must be named, justified, and small.
- **Security model preserved:** keep localhost binding, the SSRF guard, the download
  whitelist, and the no-local-paths rule. Don't design anything that requires loosening them.

---

## 9. The deliverable

Produce **one** Markdown file named **`redesign_onefilellm_webapp_py.md`**. It is read by an
AI coding agent, so it must be precise and self-contained. Use **exactly** this top-level
structure (you may add sub-sections):

1. **Design rationale (≤1 page).** The concept, how it bridges terminal × SaaS, and how it
   maps to the goals G1–G7. Brief — the rest is specification.
2. **Design tokens (complete & final).** Every value locked: full color palette for **both**
   dark and light themes (hex, with role names and the CSS custom-property name to use);
   typography scale (font stacks, sizes in rem, weights, line-heights, letter-spacing);
   spacing scale; radii; border styles; shadow/elevation values; z-index layers; motion
   durations/easings. Present as tables and/or a ready-to-paste `:root` CSS variable block.
3. **Layout & grid.** Page structure, max-widths, the responsive breakpoints, and reflow
   rules per breakpoint.
4. **Component specifications.** For **every** component in [§7](#7-screens-states-components):
   anatomy, all states (default/hover/focus/active/disabled/loading/error/empty), exact
   sizing/spacing/colors via the tokens, copy/microcopy strings, ARIA roles/attributes, and
   keyboard behavior. Include the markup approach (semantic HTML structure / class names) so
   the implementer can build it directly.
5. **Screen-by-screen wireframes.** Annotated layouts (ASCII art, described block diagrams,
   or both) for **every state**: empty, typing/detected, blocked-input, processing
   (indeterminate + crawl-determinate), success, each of the three error states, and the
   optional modes you include. Annotate which token/component each region uses.
6. **Interaction & motion spec.** The full flow (submit → progress → result/error), each
   transition, animation specifics, and the `prefers-reduced-motion` fallback for each.
7. **Backend & data binding.** This makes it buildable. For each UI element, name the
   backend value/endpoint it binds to (from [§3](#3-the-backend-contract)). List **every
   backend/endpoint change your design requires** — e.g. an SSE `/stream` endpoint with its
   event payload shape, a copy/preview fetch endpoint, per-source parsing, cancellation —
   with enough detail that the implementer can build the Flask side. Flag anything that's
   "nice but deferrable."
8. **Accessibility checklist.** Concrete, testable items (contrast pairs with ratios, focus
   order, ARIA usage, keyboard map, reduced-motion).
9. **Asset inventory.** Every icon as **inline SVG** (provide the SVG or precise description),
   the logo/wordmark treatment, any vendored helper file (name + purpose + size).
10. **Implementation notes & file plan.** How this should land in the repo: stay single-file
    `web_app.py` vs. split into `extras/templates/` + `extras/static/`; which CSS/JS goes
    where; preserve the security model and `/download` contract. Plus **acceptance criteria**
    (a checklist the implementer can self-verify against).

**Format rules for your file:**
- Be literal. Exact values, exact strings. No "TBD," no "use your judgment."
- Prefer tables, token blocks, and annotated wireframes over prose.
- Where you make a judgment call the owner might want to revisit, mark it
  `> DESIGN DECISION:` inline so it's easy to find — but still pick a concrete default.
- Keep everything implementable under the constraints in [§10](#10-constraints-non-goals).

---

## 10. Constraints & non-goals

**Hard constraints (do not violate):**
- Offline-safe, no CDN, no build step, vanilla front end; Flask-only backend.
- Localhost-only, single-user, no auth/accounts.
- Preserve the SSRF guard, the `/download` whitelist, and the no-local-paths rule.
- System fonts and inline SVG only; no downloaded web fonts or icon fonts.
- Don't show data the backend doesn't produce (e.g. per-file token counts) unless you also
  specify the backend change and mark it optional.

**Non-goals (out of scope — don't design these):**
- Authentication, user accounts, multi-tenant or cloud deployment.
- Persistent server-side storage, databases, or a settings backend.
- Public sharing, collaboration, or result permalinks.
- Mobile-app or native packaging.
- Redesigning the CLI/TUI (only the web app is in scope).

---

## 11. Appendix

### 11.1 The current template (verbatim, for reference)

```html
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
        <p>Enter a URL, DOI, or PMID:</p>
        <input type="text" name="input_path" required placeholder="..."/>
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
            <a href="/download?filename=uncompressed_output.txt">Download Uncompressed</a> |
            <a href="/download?filename=compressed_output.txt">Download Compressed</a>
        </div>
    </div>
    {% endif %}
</body>
</html>
```

### 11.2 Input examples (for the empty-state gallery)

| Type | Example string |
|---|---|
| GitHub repo | `https://github.com/jimmc414/onefilellm` |
| GitHub PR | `https://github.com/jimmc414/onefilellm/pull/73` |
| GitHub issue | `https://github.com/jimmc414/onefilellm/issues/72` |
| ArXiv | `https://arxiv.org/abs/2401.00001` |
| YouTube | `https://www.youtube.com/watch?v=mFLlVpnGpds` |
| Docs site (crawl) | `https://docs.python.org/3/` |
| DOI | `10.1038/s41586-021-03819-2` |
| PMID | `38122860` |

### 11.3 Backend function signatures (for data-binding reference)

```text
process_github_repo(repo_url)                         -> str  (<source type="github_repository">…)
process_github_pull_request(pull_request_url)         -> str
process_github_issue(issue_url)                       -> str
process_arxiv_pdf(arxiv_abs_url)                      -> str  (<source type="arxiv">…)
fetch_youtube_transcript(url)                         -> str  (<source type="youtube_transcript">…)
crawl_and_extract_text(base_url, max_depth,           -> {'content': str, 'processed_urls': [str]}
                       include_pdfs, ignore_epubs)            (<source type="web_crawl">…)
process_doi_or_pmid(identifier)                       -> str  (best-effort; often raises/errors)
preprocess_text(input_file, output_file)              -> writes compressed file
get_token_count(text)                                 -> int  (tiktoken cl100k_base)
TOKEN_ESTIMATE_MULTIPLIER = 1.37                       # estimated model tokens = round(uncompressed * 1.37)
```

### 11.4 CLI summary block (the metrics to mirror)

The Rich CLI prints this after a run — your metrics panel should present the same
information, styled:

```
Summary:
  - Sources Processed: 1
  - Final Output Size: 142.80 KB

Content Token Count (tiktoken): 142803
Estimated Model Token Count (incl. overhead): 195640
```

### 11.5 Error-response shape

```xml
<source type="youtube_transcript" url="https://www.youtube.com/watch?v=..."><error>No transcript found for this video</error></source>
```
Security rejection (returned as page text today): `Error: URL rejected by security policy.`
Local path (returned as page text today): `Error: Local path processing is not allowed via the web interface.`

---

*End of brief. Deliver `redesign_onefilellm_webapp_py.md` per [§9](#9-the-deliverable).*
