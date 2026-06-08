# OneFileLLM Web App — Redesign Specification

**Target file:** `extras/web_app.py` (Flask; may split into `extras/templates/` + `extras/static/`)
**Codename:** **Conduit** — a single console that pipes any source into one LLM-ready file.
**Status:** Implementation-ready. Read top to bottom; every value is literal and final.
**Audience:** Claude Code (automated implementer). No designer in the loop.

> **How to read this document.** Sections 1–10 mirror §9 of the brief exactly. Tokens in
> §2 are the single source of truth — every other section references them by their
> CSS custom-property name (`var(--token)`), never by raw hex. Where a value is a
> revisitable judgment call it is marked `> DESIGN DECISION:` with a concrete default
> already chosen. Open questions are collected in §10.6.

---

## 1. Design rationale

### 1.1 Concept

**Conduit** treats the web app as a *single command console*, not a web form. The page is one
vertical column: a **prompt bar** at the top (the command you type), a **transcript** below it
(what the machine did and produced). This is the mental model of a terminal — type a command,
watch it run, read the result — rebuilt with modern product craft: real spacing, soft elevation,
rounded surfaces, a token system, light/dark themes, and motion that respects the user.

The hybrid resolves cleanly along one rule:

- **Monospace + terminal signature** for anything that is *data the machine produced or consumed*:
  the input value, detected-type badge, stage log, file tree, raw preview, token numbers.
- **Sans + SaaS chrome** for anything that is *product furniture*: labels, buttons, headings,
  metric captions, empty-state teaching copy, toasts.

The terminal seasoning is deliberate and small: a `>` prompt glyph and a blinking caret in the
input, an append-only **stage log** during processing, and a faux **status line** in the header.
No CRT scanlines, no skeuomorphic bezel, no phosphor glow.

### 1.2 The three-zone shell

```
┌─ Header / status line ────────────────────────────────────────┐  persistent
│  ◆ onefilellm   ·   ● offline   ·   v…            [☾ theme]     │
├────────────────────────────────────────────────────────────────┤
│  > Prompt bar  (input + detected-type badge + Process)         │  persistent
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Transcript zone — swaps between exactly one of:              │  state-driven
│     • Empty state (teaching gallery)                           │
│     • Processing state (stage log + elapsed + cancel)          │
│     • Result state (metrics + overview tree + bounded preview) │
│     • Error state (one of three variants)                      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

The header and prompt bar never move. Only the transcript zone changes, so the user's eye never
loses the command line — exactly like a real terminal session.

### 1.3 Goal mapping (G1–G7)

| Goal | How Conduit satisfies it | Sections |
|---|---|---|
| **G1** Long jobs feel alive | SSE-driven **stage log** with append-only lines, an always-moving **elapsed timer**, an indeterminate accent shimmer (determinate `N/max` for crawls), and a **Cancel** button. Never a frozen tab. | §4.4, §6.3, §7.2 |
| **G2** Tame the giant blob | Result is **never** dumped whole. Three layers: a **metrics panel**, a **structured overview tree** parsed cheaply from tags, and a **bounded raw preview** (256 KB cap) with "showing first X of Y." Full payload lives behind Copy/Download. | §4.5, §3, §7.4 |
| **G3** Discoverable inputs | The empty state **is** a teaching gallery: one click-to-fill card per supported type with a real example. Live detection badge confirms what was recognized. | §4.2, §4.3, §5.1 |
| **G4** Correct copy + downloads | Copy is **client-side** (`navigator.clipboard.writeText`) with a "preparing…" state for large payloads that fetches `/result/raw` first. Four explicit actions: copy/download × uncompressed/compressed. | §4.5.3, §7.4 |
| **G5** Real identity, CLI sibling | Green (`--accent`) + cyan (`--accent-2`) echo the Rich CLI's `bright_green`/`cyan`; mono data surfaces; prompt glyph, caret, stage log, status line — executed with SaaS polish. | §2, §1.1 |
| **G6** Useful metrics with context | Metrics panel surfaces uncompressed, compressed, **estimated model tokens (×1.37) as the hero**, output size (KB), sources processed, elapsed. Each captioned. | §4.5.1, §11.4-bind |
| **G7** Honest, distinct errors | Three visually distinct states: **security rejection** (`--danger`, calm, policy explainer), **processing failure** (message + retry + cause hint), **empty result** (`--warn`, neutral). `<error>` tags detected and rendered as failure, never content. | §4.6, §5.x |

### 1.4 Non-negotiables honored

Offline-safe (no CDN, no web fonts, no icon fonts, no build step; system font stacks; inline SVG).
Flask-only backend; the single vendored helper (`sse.js`, ~1.5 KB, §9.4) is local. Localhost,
single-user, no auth. SSRF guard, `/download` whitelist, and no-local-paths rule preserved and
surfaced as first-class error states.

---

## 2. Design tokens (complete & final)

All values below are final. The implementer pastes §2.8 verbatim into a `:root` block and the
`[data-theme="light"]` override. **Dark is the default theme.** Never hardcode a hex in a
component — always reference the token.

### 2.1 Color — dark theme (default)

| CSS variable | Hex | Role |
|---|---|---|
| `--bg` | `#0B0E14` | App background (deep terminal charcoal) |
| `--surface` | `#11161F` | Cards / panels (lifted one step) |
| `--surface-2` | `#161B22` | Nested wells: input field, code/preview, tree |
| `--surface-3` | `#1C2230` | Hover fill on rows/cards, active tab |
| `--border` | `#283041` | Hairline separators, card edges (1px) |
| `--border-strong` | `#3A4458` | Emphasized edges, input focus border base |
| `--text` | `#E6EDF3` | Primary text |
| `--text-muted` | `#8B949E` | Secondary text, metadata, captions |
| `--text-faint` | `#6E7681` | Tertiary: placeholders, disabled labels, line numbers |
| `--accent` | `#3FB950` | **Primary green** — actions, success, "alive" |
| `--accent-hover` | `#56D364` | Green hover/active |
| `--accent-press` | `#2EA043` | Green pressed |
| `--accent-fg` | `#06140A` | Text/icon **on** a green fill (near-black for contrast) |
| `--accent-2` | `#39C5CF` | **Cyan** — links, info highlights, secondary accent |
| `--accent-2-hover` | `#56D4DD` | Cyan hover |
| `--info` | `#2F81F7` | Informational emphasis |
| `--warn` | `#D29922` | Warnings: truncated output, best-effort DOI, empty result |
| `--warn-fg` | `#1A1300` | Text on a warn fill |
| `--danger` | `#F85149` | Errors, security rejections |
| `--danger-hover` | `#FF6A63` | Danger hover |
| `--danger-fg` | `#1A0605` | Text on a danger fill |
| `--accent-bg` | `#0E2A16` | Tinted success/active background wash |
| `--info-bg` | `#0D2440` | Tinted info background wash |
| `--warn-bg` | `#2A2008` | Tinted warn background wash |
| `--danger-bg` | `#2A0F0E` | Tinted danger background wash |
| `--focus-ring` | `#56D364` | Keyboard focus ring color (rendered at 2px, see §2.6) |
| `--selection-bg` | `#1F6F2E` | `::selection` background |
| `--shadow-color` | `0 0% 0%` | HSL channel triplet used in shadow tokens |

### 2.2 Color — light theme (`[data-theme="light"]`)

Equivalent roles, retuned for AA on light. Greens/cyans darken so they remain legible as text.

| CSS variable | Hex | Role |
|---|---|---|
| `--bg` | `#F6F8FA` | App background |
| `--surface` | `#FFFFFF` | Cards / panels |
| `--surface-2` | `#F0F3F6` | Nested wells: input, preview, tree |
| `--surface-3` | `#E6EBF1` | Hover fill on rows/cards |
| `--border` | `#D0D7DE` | Hairline separators |
| `--border-strong` | `#AFB8C1` | Emphasized edges |
| `--text` | `#1F2328` | Primary text |
| `--text-muted` | `#59636E` | Secondary text, metadata |
| `--text-faint` | `#818B96` | Tertiary, placeholders, line numbers |
| `--accent` | `#1A7F37` | Primary green (darkened for AA on light) |
| `--accent-hover` | `#1F883D` | Green hover |
| `--accent-press` | `#166B2E` | Green pressed |
| `--accent-fg` | `#FFFFFF` | Text on green fill |
| `--accent-2` | `#0A7C8C` | Cyan (darkened) |
| `--accent-2-hover` | `#0B8A9C` | Cyan hover |
| `--info` | `#0969DA` | Informational |
| `--warn` | `#9A6700` | Warnings |
| `--warn-fg` | `#FFFFFF` | Text on warn fill |
| `--danger` | `#CF222E` | Errors |
| `--danger-hover` | `#E0303C` | Danger hover |
| `--danger-fg` | `#FFFFFF` | Text on danger fill |
| `--accent-bg` | `#E6F4EA` | Success/active wash |
| `--info-bg` | `#DDF0FF` | Info wash |
| `--warn-bg` | `#FBF1D6` | Warn wash |
| `--danger-bg` | `#FFEBE9` | Danger wash |
| `--focus-ring` | `#1A7F37` | Focus ring color |
| `--selection-bg` | `#BFE3CA` | `::selection` background |
| `--shadow-color` | `210 30% 40%` | Softer, slightly blue shadow on light |

### 2.3 Typography

Two system stacks only. No downloads.

```css
--font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
--font-sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

**Type scale** (rem; root font-size = 16px). `ls` = letter-spacing.

| Token | size | px | weight | line-height | ls | Used for |
|---|---|---|---|---|---|---|
| `--fs-display` | 1.5rem | 24 | 650 | 1.25 | -0.01em | Empty-state headline (sans) |
| `--fs-h1` | 1.125rem | 18 | 600 | 1.3 | -0.005em | Section titles, "Result" header (sans) |
| `--fs-h2` | 1rem | 16 | 600 | 1.35 | 0 | Panel titles (sans) |
| `--fs-body` | 0.9375rem | 15 | 400 | 1.55 | 0 | Body, teaching copy (sans) |
| `--fs-label` | 0.8125rem | 13 | 500 | 1.3 | 0.01em | Buttons, labels, captions (sans) |
| `--fs-meta` | 0.75rem | 12 | 500 | 1.3 | 0.02em | Badges, status line, footnotes (sans) |
| `--fs-metric` | 2rem | 32 | 600 | 1.1 | -0.02em | Hero metric numerals (mono) |
| `--fs-metric-sub` | 1.125rem | 18 | 600 | 1.15 | -0.01em | Secondary metric numerals (mono) |
| `--fs-mono` | 0.875rem | 14 | 400 | 1.6 | 0 | Input value, preview, stage log (mono) |
| `--fs-mono-sm` | 0.8125rem | 13 | 400 | 1.55 | 0 | Tree rows, file sizes (mono) |

> **DESIGN DECISION:** weight `650`/`600` for display/headings. If the platform font lacks a
> 650 instance it falls back to the nearest available weight — acceptable on system fonts.

### 2.4 Spacing scale (4px base)

| Token | px | Token | px |
|---|---|---|---|
| `--sp-1` | 4 | `--sp-6` | 24 |
| `--sp-2` | 8 | `--sp-7` | 32 |
| `--sp-3` | 12 | `--sp-8` | 48 |
| `--sp-4` | 16 | `--sp-9` | 64 |
| `--sp-5` | 20 | `--sp-10` | 96 |

Density rule: card padding `--sp-5` (20), section gap `--sp-6` (24), control inner padding
`--sp-3` (12) vertical-equivalent. Developer-dense, not airy.

### 2.5 Radii & borders

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 6px | Inputs, buttons, badges, tree rows |
| `--radius-md` | 8px | Cards, panels, preview well |
| `--radius-lg` | 12px | App container outer, modals/toasts |
| `--radius-pill` | 999px | Chips, type badges, status dots' container |
| `--border-w` | 1px | All hairlines |
| `--border-w-2` | 1.5px | Input focus border |

### 2.6 Elevation (shadows) & focus

Shadows are restrained; dark relies on border + faint shadow, light on soft shadow.

```css
--shadow-1: 0 1px 2px hsl(var(--shadow-color) / 0.30);
--shadow-2: 0 4px 12px hsl(var(--shadow-color) / 0.35);
--shadow-3: 0 12px 32px hsl(var(--shadow-color) / 0.45);
--ring: 0 0 0 2px var(--bg), 0 0 0 4px var(--focus-ring);  /* 2px gap + 2px ring */
--ring-inset: inset 0 0 0 2px var(--focus-ring);
```

`--ring` is the canonical keyboard-focus treatment (applied via `:focus-visible`), guaranteeing
a visible offset ring on every surface in both themes.

### 2.7 Z-index layers & motion

```css
--z-base: 0;        /* transcript content */
--z-sticky: 10;     /* header + prompt bar (sticky) */
--z-overlay: 100;   /* dropdowns, history popover */
--z-toast: 1000;    /* copy/download toasts */
--z-modal: 1100;    /* (reserved; no modals in v1) */
```

| Motion token | Value | Use |
|---|---|---|
| `--dur-fast` | 120ms | Hover/press color, badge swap |
| `--dur-mid` | 180ms | State transitions, toast in/out, accordion |
| `--dur-slow` | 240ms | Transcript zone crossfade |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | Enters |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Moves |
| `--shimmer-dur` | 1400ms | Indeterminate progress shimmer (linear, infinite) |
| `--caret-dur` | 1060ms | Blinking caret (step, infinite) |

**All** motion is wrapped so that under `@media (prefers-reduced-motion: reduce)` shimmer, caret
blink, and crossfades are disabled and replaced with instant state changes / a static accent bar
(see §6.6).

### 2.8 Ready-to-paste `:root` block

```css
:root {
  color-scheme: dark;
  /* color — dark (default) */
  --bg:#0B0E14; --surface:#11161F; --surface-2:#161B22; --surface-3:#1C2230;
  --border:#283041; --border-strong:#3A4458;
  --text:#E6EDF3; --text-muted:#8B949E; --text-faint:#6E7681;
  --accent:#3FB950; --accent-hover:#56D364; --accent-press:#2EA043; --accent-fg:#06140A;
  --accent-2:#39C5CF; --accent-2-hover:#56D4DD;
  --info:#2F81F7; --warn:#D29922; --warn-fg:#1A1300;
  --danger:#F85149; --danger-hover:#FF6A63; --danger-fg:#1A0605;
  --accent-bg:#0E2A16; --info-bg:#0D2440; --warn-bg:#2A2008; --danger-bg:#2A0F0E;
  --focus-ring:#56D364; --selection-bg:#1F6F2E; --shadow-color:0 0% 0%;

  /* type */
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

  /* spacing */
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px;
  --sp-6:24px; --sp-7:32px; --sp-8:48px; --sp-9:64px; --sp-10:96px;

  /* radii / borders */
  --radius-sm:6px; --radius-md:8px; --radius-lg:12px; --radius-pill:999px;
  --border-w:1px; --border-w-2:1.5px;

  /* elevation / focus */
  --shadow-1:0 1px 2px hsl(var(--shadow-color)/0.30);
  --shadow-2:0 4px 12px hsl(var(--shadow-color)/0.35);
  --shadow-3:0 12px 32px hsl(var(--shadow-color)/0.45);
  --ring:0 0 0 2px var(--bg), 0 0 0 4px var(--focus-ring);

  /* z / motion */
  --z-sticky:10; --z-overlay:100; --z-toast:1000;
  --dur-fast:120ms; --dur-mid:180ms; --dur-slow:240ms;
  --ease-out:cubic-bezier(0.22,1,0.36,1); --ease-in-out:cubic-bezier(0.4,0,0.2,1);
  --shimmer-dur:1400ms; --caret-dur:1060ms;
}

[data-theme="light"] {
  color-scheme: light;
  --bg:#F6F8FA; --surface:#FFFFFF; --surface-2:#F0F3F6; --surface-3:#E6EBF1;
  --border:#D0D7DE; --border-strong:#AFB8C1;
  --text:#1F2328; --text-muted:#59636E; --text-faint:#818B96;
  --accent:#1A7F37; --accent-hover:#1F883D; --accent-press:#166B2E; --accent-fg:#FFFFFF;
  --accent-2:#0A7C8C; --accent-2-hover:#0B8A9C;
  --info:#0969DA; --warn:#9A6700; --warn-fg:#FFFFFF;
  --danger:#CF222E; --danger-hover:#E0303C; --danger-fg:#FFFFFF;
  --accent-bg:#E6F4EA; --info-bg:#DDF0FF; --warn-bg:#FBF1D6; --danger-bg:#FFEBE9;
  --focus-ring:#1A7F37; --selection-bg:#BFE3CA; --shadow-color:210 30% 40%;
}
```

> **DESIGN DECISION:** theme is toggled by setting `data-theme="light"|"dark"` on `<html>`.
> Default = dark. On first load, read `localStorage.ofllm-theme`; if unset, fall back to
> `prefers-color-scheme`. Persist the user's explicit choice. `color-scheme` is set so native
> form controls/scrollbars match.

---

## 3. Layout & grid

### 3.1 Page structure

Single centered column. No multi-column dashboard. Everything lives inside one constrained
container so reading and scanning stay linear (terminal session metaphor).

```
html, body                      → bg = var(--bg), min-height 100dvh, font-sans, text = var(--text)
.app                            → max-width 920px; margin-inline auto; padding-inline var(--sp-5)
  .app__header   (sticky top)   → 56px tall, z var(--z-sticky), bg var(--bg) w/ bottom border
  .app__prompt   (sticky)       → sits under header at top: 56px, z var(--z-sticky)
  .app__transcript              → flows; min-height fills viewport remainder
  .app__footer                  → optional, var(--sp-6) vertical padding, muted
```

- **Container max-width:** `920px`. The prompt bar and metrics breathe; preview/tree get a
  comfortable reading measure. Result-zone preview may go full container width.
- **Vertical rhythm:** `--sp-6` (24px) between major transcript blocks; `--sp-5` (20px) card
  padding; `--sp-3` (12px) inside dense rows.
- **Sticky stack:** header (56px) and prompt bar stick to the top so the command line is always
  reachable while scrolling a long result. Combined sticky offset = 56px + prompt height.

> **DESIGN DECISION:** the prompt bar is sticky (not just the header) so that during a huge
> result the user can paste a new input without scrolling up. If the implementer finds sticky
> double-stacking awkward on very short viewports (<560px tall), collapse the header into the
> prompt bar at that height (hide version + repo link, keep theme toggle + offline dot).

### 3.2 Breakpoints & reflow

Desktop-first. Three breakpoints.

| Name | Range | Behavior |
|---|---|---|
| **Wide** | ≥ 720px | Full layout. Metrics = 3-up grid (2 rows). Prompt = input grows, badge + Process inline to the right. Empty-state gallery = 2 columns. Action bar = single row of 4 buttons. |
| **Narrow** | 480–719px | Metrics = 2-up grid. Empty-state gallery = 1 column. Action bar = 2×2 grid. Prompt: badge drops to a second line beneath the input; Process stays inline full-width under input. Tree + preview unchanged. |
| **Min** | < 480px | Single column everywhere. Metrics = 1-up stack. Prompt: input full width, detected badge inline-start of a second row, Process full-width button below. Header hides `version`; keeps logo, offline dot, theme toggle. Preview keeps horizontal scroll inside its well (never reflows code). |

**Reflow rules:**
- The **raw preview** `<pre>` never wraps or reflows code — it scrolls horizontally inside its
  own well (`overflow:auto`) at every breakpoint.
- The **overview tree** truncates long paths with `text-overflow: ellipsis` and exposes the full
  path via `title=` + an accessible tooltip; it never forces horizontal page scroll.
- Buttons in the **action bar** keep a 44px min hit target at all widths (§8).
- Grid gaps: `--sp-4` (16px) wide, `--sp-3` (12px) narrow/min.

### 3.3 Grid primitives

- Metrics grid: `display:grid; grid-template-columns: repeat(3, 1fr); gap: var(--sp-4)` → at
  Narrow `repeat(2,1fr)`, at Min `1fr`.
- Empty gallery: `repeat(2,1fr)` → `1fr` below 720px.
- Action bar: `display:flex; gap:var(--sp-3); flex-wrap:wrap` — each button `flex:1 1 auto;
  min-width:140px` so it forms 1 row wide, 2×2 narrow, stacked min, automatically.

---

## 4. Component specifications

Conventions: every interactive element gets `:focus-visible { box-shadow: var(--ring);
outline: none; border-radius: inherit; }`. Transitions use `--dur-fast` for color, `--dur-mid`
for layout/opacity. All icons are inline SVG from §9 at `width/height:1em` unless noted,
`stroke: currentColor`, `fill: none`, `stroke-width: 1.75`, `aria-hidden="true"` (decorative)
or labeled (when standalone).

### 4.1 Header / status line

**Anatomy:** `<header class="app__header">` → left cluster (logo mark + wordmark `onefilellm`),
center/left status group (offline/online dot + label, version), right cluster (theme toggle).
Rendered as a faux **status line**: monospace `--fs-meta`, separated by a dim middot `·`.

```
◆ onefilellm   ·   ● offline   ·   v1.x            [☾]
└logo+word────┘   └status dot─┘   └ver┘            └theme toggle┘
```

| Element | Spec |
|---|---|
| Logo mark | §9.1 inline SVG, 20×20, `color: var(--accent)`. |
| Wordmark | `onefilellm`, `--font-mono`, `--fs-label`, weight 600, `color: var(--text)`. |
| Offline/online dot | 8px circle. **Offline:** `--text-muted` fill + label "offline". **Online:** `--accent` fill + label "online". Label `--font-mono --fs-meta --text-muted`. Value comes from `navigator.onLine`, updated on `online`/`offline` events. `aria-live="polite"` on the label. |
| Version | `v{__version__}`, `--font-mono --fs-meta --text-faint`. Bound to a backend-injected version string (§7.6). |
| Theme toggle | 32×32 icon button. Shows §9.7 moon (dark active) / §9.8 sun (light active). `aria-label="Switch to light theme"` / `"Switch to dark theme"`, `aria-pressed` reflects state. |

**States** — theme toggle: default transparent; hover `background: var(--surface-2)`; active
`background: var(--surface-3)`; focus `--ring`. Header has no other interactive states.

**Keyboard:** theme toggle reachable in tab order; `Enter`/`Space` toggles. Global shortcut
`g t` not required; `Alt+T` toggles theme (documented in footer hint).

### 4.2 Prompt bar (command input) — the centerpiece

**Anatomy:** `<form class="prompt" role="search">` containing, left→right:
1. `>` **prompt glyph** — `--font-mono`, `--accent`, weight 600, non-selectable, `aria-hidden`.
2. `<input id="cmd" class="prompt__input">` — `type="text"`, `--font-mono --fs-mono`,
   `name="input_path"`, `autocomplete="off"`, `autocapitalize="off"`, `spellcheck="false"`,
   `enterkeyhint="go"`, `aria-label="Source URL, DOI, or PMID to process"`,
   `aria-describedby="cmd-hint"`.
3. **Blinking caret** — a CSS pseudo-element shown only when the input is empty + focused (a
   terminal nod). Hidden once the user types (native caret takes over).
4. **Detected-type badge** (§4.3) — appears inline-end once a type is detected.
5. **Process button** (§4.4 primary).

**Container styling:** `background: var(--surface-2)`; `border: var(--border-w) solid
var(--border)`; `border-radius: var(--radius-md)`; padding `var(--sp-3) var(--sp-4)`; display
flex, `gap: var(--sp-3)`, `align-items:center`. Below it, a one-line hint row `#cmd-hint`
(`--fs-meta --text-muted`): "Paste a GitHub repo, ArXiv, YouTube, docs site, DOI, or PMID — Enter to run."

**States:**

| State | Visual |
|---|---|
| Default (empty) | Placeholder `https://github.com/owner/repo` in `--text-faint`; blinking caret visible; Process **disabled** (§4.4 disabled). |
| Focus | Container border → `var(--border-w-2) solid var(--border-strong)`; `box-shadow: var(--ring)` on the **container** (input outline none). |
| Typing / detected | Native caret; detected badge animates in (§6.3); Process enabled (green). |
| Blocked input detected | Container border-left 2px `--danger`; badge becomes a **rejection chip** (§4.3 blocked); inline hint swaps to the rejection reason in `--danger`; Process disabled. |
| Submitting | Input becomes `readonly`; Process shows loading (§4.4); whole prompt `opacity:0.85`. |
| Error returned | Prompt returns to editable; input value preserved so the user can fix and retry. |
| Disabled (during processing) | `readonly`, not `disabled`, so value stays selectable/copyable. |

**Microcopy:**
- Placeholder: `https://github.com/owner/repo`
- Hint (default): `Paste a GitHub repo, ArXiv, YouTube, docs site, DOI, or PMID — Enter to run.`
- Hint (blocked local path): `Local file paths aren't allowed in the web app. Use a URL instead.`
- Hint (blocked private URL): `That looks like a private or local address — blocked by the security policy.`

**Keyboard:** `Enter` submits (when enabled). `Esc` clears the input (and dismisses any inline
rejection). `/` anywhere on the page focuses the input (documented; ignore when focus is already
in a text field). Tab order: input → badge (if interactive, it isn't) → Process.

**ARIA:** form `role="search"`; input labeled as above; live detection badge container
`aria-live="polite"` so screen readers announce "Detected: GitHub repository".

### 4.3 Detected-type badge

A pill that names what the input was recognized as. `--radius-pill`, padding `2px var(--sp-2)`,
`--font-mono --fs-meta`, weight 600, an inline 14px SVG glyph + label. Detection runs on `input`
(debounced 120ms), client-side, mirroring backend rules (§7.3).

| Detected type | Label text | Glyph (§9) | Fill / text |
|---|---|---|---|
| GitHub repo | `github · repo` | branch | `--accent-bg` / `--accent` |
| GitHub PR | `github · pr` | merge | `--accent-bg` / `--accent` |
| GitHub issue | `github · issue` | dot-circle | `--accent-bg` / `--accent` |
| ArXiv | `arxiv` | doc | `--info-bg` / `--info` |
| YouTube | `youtube · transcript` | play | `--info-bg` / `--info` |
| Docs crawl | `docs · will crawl` | globe | `--surface-3` / `--accent-2` |
| DOI | `doi · best-effort` | link | `--warn-bg` / `--warn` |
| PMID | `pmid · best-effort` | link | `--warn-bg` / `--warn` |
| None yet / ambiguous | *(badge hidden)* | — | — |
| **Blocked: local path** | `blocked · local path` | shield-x | `--danger-bg` / `--danger` |
| **Blocked: private URL** | `blocked · private url` | shield-x | `--danger-bg` / `--danger` |

The "Docs crawl" label intentionally reads `will crawl` to set expectations that a generic URL
triggers a multi-page crawl (potentially slow). DOI/PMID read `best-effort` to pre-warn (§3.1).

### 4.4 Buttons

One component, four variants. Base: `--font-sans --fs-label` weight 600; height 36px (Process
40px); padding-inline `var(--sp-4)`; `border-radius: var(--radius-sm)`; `gap: var(--sp-2)` for
icon+label; transition color/background `--dur-fast`. Min hit target 44px enforced via min-height
on touch/narrow (§8).

| Variant | Default | Hover | Active/Press | Disabled | Focus |
|---|---|---|---|---|---|
| **Primary** (Process, Retry) | bg `--accent`, text `--accent-fg`, no border | bg `--accent-hover` | bg `--accent-press` | bg `--surface-3`, text `--text-faint`, `cursor:not-allowed`, no shadow | `--ring` |
| **Secondary** (Download ×2) | bg `--surface-2`, text `--text`, border `--border` | bg `--surface-3`, border `--border-strong` | bg `--surface-3` filter brightness .96 | text `--text-faint`, border `--border`, `cursor:not-allowed` | `--ring` |
| **Ghost** (Copy ×2, Cancel, theme, expand) | transparent, text `--text`, border transparent | bg `--surface-2` | bg `--surface-3` | text `--text-faint` | `--ring` |
| **Danger-ghost** (Cancel while running) | transparent, text `--danger`, border `--border` | bg `--danger-bg`, border `--danger` | bg `--danger-bg` brightness .95 | — | `--ring` |

**Loading state (Process):** label swaps to `Processing…`; a spinner (§9.9, 16px, `animation:
spin 0.8s linear infinite`) replaces the leading glyph; button `aria-busy="true"`,
`disabled`. Under reduced-motion the spinner is replaced by an animated `…` ellipsis (opacity
pulse disabled → static `Processing…`).

**Copy buttons success state:** on success the label briefly becomes `Copied ✓` with a check
glyph (§9.10) and `color: var(--accent)` for 1600ms, then reverts. `aria-live` toast also fires
(§4.8). Large-payload interim: label `Preparing copy…` + spinner while fetching `/result/raw`.

### 4.5 Result panel

Container `<section class="result" aria-labelledby="result-h">`. Header row: `<h2 id="result-h">`
"Result" (`--fs-h1`) + a muted right-aligned summary line `Done in 12.4s · 1 source`
(`--font-mono --fs-meta --text-muted`). Three stacked blocks:

#### 4.5.1 Metrics panel

`<div class="metrics" role="group" aria-label="Output metrics">` — a grid of metric cards.
**Hero card** spans full width (or 2 cols at Wide) and is visually elevated.

| Card | Value source | Caption | Treatment |
|---|---|---|---|
| **Estimated model tokens** *(hero)* | `round(uncompressed × 1.37)` | "Estimated model tokens · incl. overhead" | Numeral `--fs-metric` mono, `color: var(--accent)`; card `background: var(--accent-bg)`, border `--accent` at 40% via `--border` fallback; caption `--fs-label --text-muted`. |
| Uncompressed tokens | `uncompressed_token_count` | "Uncompressed tokens (tiktoken)" | `--fs-metric-sub` mono `--text`. |
| Compressed tokens | `compressed_token_count` | "Compressed tokens" | `--fs-metric-sub` mono `--text`; sub-caption shows `−NN%` reduction in `--accent`. |
| Output size | `final_output_kb` | "Output size" | value `NN.N KB` mono. |
| Sources processed | `sources_processed` | "Sources processed" | integer mono. |
| Elapsed | client timer (final) | "Elapsed" | `M:SS` or `NN.N s` mono. |

Card base: `background: var(--surface)`, `border: var(--border-w) solid var(--border)`,
`border-radius: var(--radius-md)`, padding `var(--sp-4)`. Numerals are tabular
(`font-variant-numeric: tabular-nums`). All numbers grouped with thin separators (e.g.
`195,640`) via client `Intl.NumberFormat`.

> **DESIGN DECISION:** the `−NN%` compression delta is derived client-side from the two token
> counts; no backend change needed.

#### 4.5.2 Structured overview (tree)

`<div class="overview">` with a header row: title "Overview" (`--fs-h2`), a count chip
`1 source · 248 files` (`--font-mono --fs-meta`), and a **view toggle** (§4.6) switching
Overview ⇄ Raw. The tree is parsed **client-side** from the returned text (§7.4) — cheap regex
over `<source …>` and `<file path="…">` tags, not full XML parsing.

**Tree node anatomy** (`role="tree"` → `role="treeitem"` rows):
- **Source row:** disclosure triangle (§9.11) + source-type glyph + `type` + truncated
  `url/base_url` + right-aligned file count. `--font-mono --fs-mono-sm`.
- **File row:** indented `var(--sp-5)`; file glyph (§9.12) + `path` (ellipsized middle) +
  right-aligned size `NN.N KB · NNN lines`. Sizes computed client-side from the captured file
  body length and newline count.

**Row states:** default transparent; hover `background: var(--surface-3)`; focus `--ring`
inset-style (`box-shadow: var(--ring)`); expanded sources rotate the triangle 90°
(`transition: transform var(--dur-fast)`).

**Behavior:** sources expanded by default; clicking a file row **scrolls the raw preview to that
file's offset** and flashes the preview header (`background: var(--accent-bg)` for 600ms) — links
overview to preview. Long trees virtualize past 500 rows (render windowing) so the DOM stays
bounded (§7.4). Empty tree (no `<file>` tags, e.g. a transcript) shows a single source row with
its byte size and no children.

**Keyboard (tree):** `↑/↓` move between visible rows; `←` collapse / focus parent; `→` expand /
first child; `Enter` jumps preview to file; `Home/End` first/last. Roving `tabindex`.

#### 4.5.3 Bounded raw preview

`<figure class="preview">` → header (`<figcaption>`) + scroll well + truncation notice.

- **Well:** `background: var(--surface-2)`, `border-radius: var(--radius-md)`, `border:
  var(--border)`, `padding: var(--sp-4)`, `max-height: 60vh`, `overflow: auto`. Contains a
  `<pre><code>` in `--font-mono --fs-mono`, `white-space: pre`, `tab-size: 2`. Optional line
  numbers in a `--text-faint` gutter (`user-select:none`).
- **Truncation:** only the first **262,144 bytes (256 KB)** are injected into the DOM. If the
  payload exceeds that, a sticky bottom **notice bar** inside the well reads (warn styling):
  `Showing first 256 KB of 1.84 MB — download or copy for the complete output.` The DOM never
  holds more than the cap (P2/G2). The cap is a single JS constant `PREVIEW_CAP_BYTES`.
- **Syntax tint (cheap, optional):** tags `<source …>`, `<file …>`, `<error>` are tinted via a
  single regex pass wrapping them in `<span>`s: tag punctuation `--text-faint`, tag name
  `--accent-2`, attribute names `--text-muted`, attribute values `--accent`. No tokenizer, no
  per-language highlighting. `> DESIGN DECISION:` if the 256 KB regex pass ever costs >16ms,
  skip tinting and render plain mono — correctness over polish.
- **Empty/transcript content:** preview shows the content as-is (it's small).

#### 4.5.4 Action bar

`<div class="actions" role="group" aria-label="Copy and download output">` — four buttons,
grouped 2 (copy, ghost) + 2 (download, secondary), with a thin divider between groups:

| Button | Label | Variant | Binds to |
|---|---|---|---|
| Copy uncompressed | `Copy` + caption `uncompressed` | Ghost + copy glyph (§9.13) | `GET /result/raw?which=uncompressed` → clipboard |
| Copy compressed | `Copy` + caption `compressed` | Ghost | `GET /result/raw?which=compressed` → clipboard |
| Download uncompressed | `Download` + caption `.txt` | Secondary + download glyph (§9.14) | `GET /download?filename=uncompressed_output.txt` |
| Download compressed | `Download` + caption `.txt` | Secondary | `GET /download?filename=compressed_output.txt` |

Each button: two-line label (action bold sans, caption `--fs-meta --text-muted`). Copy success
& "preparing copy…" per §4.4. Downloads use a plain anchor with `download` attribute styled as
the button (keeps the whitelist contract; no JS needed) — but show a brief toast "Download
started".

### 4.6 View toggle (Overview ⇄ Raw)

A 2-segment control (`role="tablist"`, segments `role="tab"`). `background: var(--surface-2)`,
`border-radius: var(--radius-sm)`, padding 2px; active segment `background: var(--surface)`,
`box-shadow: var(--shadow-1)`, text `--text`; inactive `--text-muted`. `--fs-label`. Switching
shows/hides the corresponding panel (`role="tabpanel"`), preserving scroll position of each.
Keyboard: `←/→` move between tabs, `Enter/Space` activate; focus `--ring`.

### 4.7 Empty state (teaching gallery)

Shown when no run has happened. `<section class="empty">`:
- **Headline** (`--fs-display` sans): `What do you want to flatten into one file?`
- **Subhead** (`--fs-body --text-muted`): `Paste any of these above and press Enter. Click a
  card to try it.`
- **Gallery:** grid of 8 cards (§11.2 examples). Each card `role="button"`, tabindex 0:
  glyph + type name (sans `--fs-label`) + example string (`--font-mono --fs-meta --text-muted`,
  ellipsized). Click/Enter **fills the prompt input** with the example and focuses it (does not
  auto-submit — user reviews then presses Enter). Card states: default `background: var(--surface)`
  `border --border`; hover `border --border-strong`, lift `box-shadow: var(--shadow-1)`,
  `translateY(-1px)`; active `translateY(0)`; focus `--ring`.

| Card | Type | Example (fills input) |
|---|---|---|
| GitHub repo | branch glyph | `https://github.com/jimmc414/onefilellm` |
| GitHub PR | merge | `https://github.com/jimmc414/onefilellm/pull/73` |
| GitHub issue | dot-circle | `https://github.com/jimmc414/onefilellm/issues/72` |
| ArXiv | doc | `https://arxiv.org/abs/2401.00001` |
| YouTube | play | `https://www.youtube.com/watch?v=mFLlVpnGpds` |
| Docs site | globe | `https://docs.python.org/3/` |
| DOI | link | `10.1038/s41586-021-03819-2` |
| PMID | link | `38122860` |

A muted footnote under the gallery: `Local file paths and private/internal URLs are blocked by
the security policy.` (`--fs-meta --text-faint`).

### 4.8 Toast

`<div class="toast" role="status" aria-live="polite">` anchored bottom-center, `z var(--z-toast)`.
`background: var(--surface)`, `border: var(--border)`, `border-radius: var(--radius-md)`,
`box-shadow: var(--shadow-2)`, padding `var(--sp-3) var(--sp-4)`, `--fs-label`. Auto-dismiss
2400ms; reduced-motion = appear/disappear instantly (no slide). Variants: success (check glyph,
`--accent`), info (`--accent-2`), error (`--danger`). Used for: "Copied to clipboard",
"Download started", "Copy failed — select the preview and press ⌘/Ctrl-C".

### 4.9 Session history (optional, included)

`> DESIGN DECISION:` included as a lightweight popover, off by default visually. A small ghost
button in the prompt-bar trailing edge (clock glyph §9.15, `aria-label="Recent inputs"`) opens a
popover (`role="menu"`, `z var(--z-overlay)`) listing up to 10 recent inputs this session from
`localStorage.ofllm-history` (array of `{value, type, ts}`). Each item: type glyph + truncated
value + relative time. Click fills the input. A "Clear" ghost button at the bottom empties it.
If history is empty, the button is hidden. No server involvement.

---

## 5. Screen-by-screen wireframes

Annotations in `«»` name the component/token. Container is 920px wide unless noted.

### 5.1 Empty (first load) — `[data-view="empty"]`

```
┌───────────────────────────────────────────────────────────────────────┐
│ ◆ onefilellm · ● offline · v1.x                               [☾]      │ «§4.1 header, sticky»
├───────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ >  https://github.com/owner/repo▏              [ Process ]         │ │ «§4.2 prompt; caret blinks; Process disabled»
│ └───────────────────────────────────────────────────────────────────┘ │
│  Paste a GitHub repo, ArXiv, YouTube, docs site, DOI, or PMID — Enter. │ «#cmd-hint, --fs-meta --text-muted»
│                                                                       │
│  What do you want to flatten into one file?                           │ «--fs-display»
│  Paste any of these above and press Enter. Click a card to try it.    │ «--fs-body --text-muted»
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────────┐                     │
│  │ ⌥ GitHub repo       │  │ ⌥ GitHub PR         │                     │ «§4.7 cards, 2-col Wide»
│  │ github.com/jimmc4…  │  │ …/pull/73           │                     │
│  └─────────────────────┘  └─────────────────────┘                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                     │
│  │ ⌥ GitHub issue …    │  │ ⌥ ArXiv …           │                     │
│  └─────────────────────┘  └─────────────────────┘                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                     │
│  │ ⌥ YouTube …         │  │ ⌥ Docs site …       │                     │
│  └─────────────────────┘  └─────────────────────┘                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                     │
│  │ ⌥ DOI …             │  │ ⌥ PMID …            │                     │
│  └─────────────────────┘  └─────────────────────┘                     │
│  Local file paths and private/internal URLs are blocked.              │ «footnote --text-faint»
└───────────────────────────────────────────────────────────────────────┘
```

### 5.2 Typing / detected — `[data-view="empty"]` + badge

```
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ >  https://github.com/jimmc414/onefilellm  [github · repo] [Process]│ │ «badge §4.3 accent; Process enabled green»
│ └───────────────────────────────────────────────────────────────────┘ │
│  Detected: GitHub repository — will fetch the repo tree and files.    │ «hint updates, aria-live»
```

### 5.3 Blocked input — inline, pre-submit

```
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ >  /Users/me/project   [⛊ blocked · local path]      [ Process ]   │ │ «border-left --danger; Process disabled»
│ └───────────────────────────────────────────────────────────────────┘ │
│  Local file paths aren't allowed in the web app. Use a URL instead.   │ «hint in --danger»
```

### 5.4 Processing — indeterminate — `[data-view="processing"]`

```
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ >  https://docs.python.org/3/        (readonly)   [ Processing… ⟳ ]│ │ «prompt readonly; Process loading»
│ └───────────────────────────────────────────────────────────────────┘ │
│ ┌── Processing ───────────────────────────────────  0:14  [ Cancel ] ┐ │ «elapsed timer mono; Cancel danger-ghost»
│ │ ▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  ← accent shimmer (indeterminate) │ │ «§6.3 shimmer bar»
│ │                                                                     │ │
│ │  ✓ detected input · github? no → web crawl          0.2s           │ │ «stage log, append-only, mono»
│ │  ✓ fetching                                          1.1s           │ │
│ │  ⟳ extracting text from pages…                                      │ │ «current stage: spinner + accent»
│ │    ▏                                                                 │ │ «blinking caret on active line»
│ └─────────────────────────────────────────────────────────────────────┘ │
```

### 5.5 Processing — crawl determinate

```
│ ┌── Processing · crawl ───────────────────────────  0:38  [ Cancel ] ┐ │
│ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░  47 / 1000 pages    «determinate %»  │ │ «width = pages/max; label mono»
│ │  ✓ detected input · web crawl                        0.2s           │ │
│ │  ✓ fetching seed page                                0.9s           │ │
│ │  ⟳ crawling — 47 pages fetched                                      │ │ «updates live from SSE page events»
│ └─────────────────────────────────────────────────────────────────────┘ │
```

### 5.6 Result (success) — `[data-view="result"]`

```
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ >  https://github.com/jimmc414/onefilellm  [github·repo] [Process] │ │ «prompt editable again»
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Result                                       Done in 12.4s · 1 source │ «§4.5 header»
│  ┌──────────────────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ 195,640                  │ │ 142,803      │ │ 78,420  −45% │       │ «hero accent / sub / sub»
│  │ Est. model tokens·overhd │ │ Uncompressed │ │ Compressed   │       │
│  └──────────────────────────┘ └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                   │
│  │ 142.80 KB    │ │ 1            │ │ 12.4 s       │                   │ «size / sources / elapsed»
│  │ Output size  │ │ Sources      │ │ Elapsed      │                   │
│  └──────────────┘ └──────────────┘ └──────────────┘                   │
│                                                                       │
│  Overview  1 source · 248 files            [ Overview | Raw ]         │ «§4.5.2 + toggle §4.6»
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ ▾ ⌥ github_repository  github.com/jimmc414/onefilellm      248 fls │ │ «source row»
│  │     ▢ README.md                              8.4 KB · 196 lines    │ │ «file rows»
│  │     ▢ onefilellm.py                         71.2 KB · 1,840 lines  │ │
│  │     ▢ src/…/main.py                           …                    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│  ┌─ first 256 KB ────────────────────────────────────────────────────┐ │ «§4.5.3 preview (Raw tab)»
│  │ <source type="github_repository" url="…">                         │ │ «mono, tinted tags»
│  │ <file path="README.md">                                           │ │
│  │ …                                                                 │ │
│  │ ▒ Showing first 256 KB of 1.84 MB — download or copy for full.    │ │ «sticky warn notice»
│  └───────────────────────────────────────────────────────────────────┘ │
│  [ Copy ⌐uncompressed ] [ Copy ⌐compressed ] │ [ ↓ Download ] [ ↓ Download ] │ «§4.5.4 action bar»
└───────────────────────────────────────────────────────────────────────┘
```

### 5.7 Error — security rejection — `[data-view="error"][data-error="security"]`

```
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ ⛊  Blocked by the security policy                  «--danger icon» │ │
│  │ That address is local, private, or internal, so the web app won't  │ │ «--fs-body»
│  │ fetch it. This protects against SSRF. Try a public URL instead.    │ │
│  │                                              [ Edit input ]        │ │ «primary → focuses prompt»
│  └───────────────────────────────────────────────────────────────────┘ │ «card border-left 3px --danger, bg --danger-bg»
```

### 5.8 Error — processing failure — `[data-error="processing"]`

```
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ ⚠  Couldn't process that source                    «--danger»      │ │
│  │ No transcript found for this video.                                │ │ «backend message, verbatim, mono»
│  │ DOIs and PMIDs are best-effort and often unavailable.  «if DOI/PMID»│ │ «cause hint, conditional»
│  │                              [ Retry ]   [ Edit input ]            │ │ «primary Retry + ghost Edit»
│  └───────────────────────────────────────────────────────────────────┘ │
```

### 5.9 Error — empty result — `[data-error="empty"]`

```
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ ◌  Nothing to show                                 «--warn»        │ │
│  │ The source was reached but produced no extractable content         │ │
│  │ (an empty crawl or a video without a transcript).                  │ │
│  │                              [ Try another input ]                 │ │ «primary → focus prompt»
│  └───────────────────────────────────────────────────────────────────┘ │ «bg --warn-bg, border-left --warn»
```

### 5.10 History popover (optional)

```
│ … input … [🕘]│  ┌─ Recent (this session) ───────┐
│              └──│ ⌥ github.com/jimmc414/one…  2m │  «menu, z-overlay»
│                 │ ▶ youtube …/watch?v=mFL…   8m │
│                 │ 🌐 docs.python.org/3/     15m │
│                 │ ─────────────────────────────│
│                 │ Clear                         │
│                 └───────────────────────────────┘
```

---

## 6. Interaction & motion spec

### 6.1 The full flow

```
empty ──submit──▶ processing ──SSE: done──▶ result
  ▲                   │  └─SSE: error / <error> tag──▶ error
  │                   └─Cancel──▶ empty (input restored)
  └────────────── Edit/Retry/new submit ───────────────┘
```

`data-view` on `.app__transcript` drives which block renders (`empty|processing|result|error`).
Transitions crossfade the transcript zone (opacity 0→1 over `--dur-slow`, `--ease-out`) while the
sticky header/prompt never animate.

### 6.2 Submit

1. On `submit` (or `/`-focus + Enter): client re-validates type; if blocked, stay in empty and
   show inline rejection (no request). Otherwise:
2. Prompt → readonly; Process → loading; transcript → `processing`; **open `EventSource`** on
   `/stream?input=…` (§7.1). Start the elapsed timer (rAF, formatted `M:SS` / `s`).
3. Each SSE `stage` event appends a line to the stage log with a check on the prior line. Each
   `page` event (crawl) updates the determinate bar + count. A `done` event carries the result
   payload pointer; a `error` event carries the failure.

### 6.3 Progress animations

- **Indeterminate shimmer:** a 40%-wide gradient band (`linear-gradient(90deg, transparent,
  var(--accent) , transparent)` at ~35% opacity) sweeps left→right over a `--surface-3` track,
  `animation: shimmer var(--shimmer-dur) linear infinite`. Track height 6px, `--radius-pill`.
- **Determinate (crawl):** track same; fill = solid `--accent`, `width: calc(pages/max*100%)`,
  `transition: width var(--dur-mid) var(--ease-in-out)`. Shimmer overlays the *filled* portion
  only, signaling "alive" without faking completion.
- **Active stage line:** leading spinner (§9.9) + a blinking caret (`▏`) at line end
  (`animation: caret var(--caret-dur) steps(1) infinite`).
- **Elapsed timer:** updates every 250ms; `font-variant-numeric: tabular-nums` so it doesn't jitter.

### 6.4 Result reveal

On `done`: timer freezes (becomes "Elapsed"); transcript crossfades to `result`. Metric numerals
**count up** from 0 to final over 420ms (`ease-out`) using `requestAnimationFrame` — *disabled*
under reduced-motion (numbers appear final). Overview tree + preview render immediately (no
stagger that delays reading).

### 6.5 Copy / download feedback

- **Copy (small ≤256 KB already in DOM):** write immediately → button "Copied ✓" 1600ms + toast.
- **Copy (large):** button "Preparing copy…" + spinner → `fetch('/result/raw?which=…')` → on
  resolve write to clipboard → "Copied ✓" + toast. On `navigator.clipboard` failure (e.g.
  insecure context): error toast with fallback instruction (§4.8) and the preview is auto-selected.
- **Download:** native anchor navigation; a "Download started" info toast fires on click.

### 6.6 `prefers-reduced-motion: reduce` fallbacks (each animation)

| Animation | Reduced-motion fallback |
|---|---|
| Transcript crossfade | Instant swap (no opacity transition). |
| Shimmer (indeterminate) | Static 6px `--accent` bar at 60% width, no movement; the **elapsed timer** alone conveys liveness. |
| Determinate fill | Width updates instantly (no transition). |
| Blinking caret | Static `▏` (no blink). |
| Process spinner | Static `…` after "Processing". |
| Metric count-up | Final numbers shown immediately. |
| Toast slide | Fade-free instant show/hide. |
| Button hover lifts | Color change only, no `translateY`. |

Implement once via a top-level `@media (prefers-reduced-motion: reduce){ *{animation:none!important;
transition:none!important} }` plus the specific static fallbacks above for shimmer/caret/spinner.

---

## 7. Backend & data binding

This section is what makes the design buildable. Every UI value names the backend value or
endpoint it binds to. New endpoints are fully specified. Each change is tagged **[required]**,
**[optional]**, or **[deferrable]**.

### 7.1 New endpoint — `GET /stream` (SSE progress) **[required for G1]**

Replaces the blocking `POST /` round-trip with a streamed job. Flask returns a
`text/event-stream` response from a generator; the browser uses native `EventSource` (no library
needed beyond the tiny vendored reconnection guard `sse.js`, §9.4).

**Request:** `GET /stream?input=<urlencoded input string>`
(single-user/localhost; a query param is acceptable. `> DESIGN DECISION:` use GET so
`EventSource` works natively; the input is re-validated server-side exactly as `POST /` is today.)

**Server flow:**
1. Re-run the SSRF/`_is_safe_url` guard and the local-path guard **before** any fetch. On
   rejection emit a single `error` event (subtype `security`) and close.
2. Detect input type. Emit `stage` events around each backend phase. Call the existing
   `process_*` / `crawl_and_extract_text` functions. For the crawler, wrap its per-page loop to
   emit `page` events (it already tracks `processed_urls` and a max — surface both).
3. On success, write the two files (as today), compute metrics, emit a final `done` event whose
   payload is the **metrics + a result id**, not the full text. The big text stays server-side
   and is fetched on demand by `/result/raw` and `/download`.
4. On exception, emit an `error` event (subtype `processing`) with the exception message.

**Event payloads** (each line is `event: <name>` + `data: <json>`):

```
event: stage
data: {"key":"detect","label":"detected input · web crawl","status":"done","t":0.2}

event: stage
data: {"key":"fetch","label":"fetching","status":"active","t":1.1}

event: page                     # crawl only, determinate
data: {"fetched":47,"max":1000,"url":"https://docs.python.org/3/library/os.html"}

event: done
data: {
  "result_id":"r_4f3a",                 # opaque, used by /result/raw
  "source_count":1,
  "uncompressed_tokens":142803,
  "compressed_tokens":78420,
  "estimated_model_tokens":195640,      # round(uncompressed*1.37) computed server-side
  "output_kb":142.80,
  "elapsed_s":12.4,
  "preview":"<source type=…> …first 256 KB…",   # bounded preview, server-truncated
  "preview_bytes":262144,
  "total_bytes":1929216,
  "files":[                              # parsed server-side OR omit and parse client-side
    {"path":"README.md","bytes":8602,"lines":196},
    {"path":"onefilellm.py","bytes":72909,"lines":1840}
  ],
  "source":{"type":"github_repository","url":"https://github.com/jimmc414/onefilellm"}
}

event: error
data: {"subtype":"security","message":"URL rejected by security policy."}
# subtype ∈ {"security","processing","empty"}
```

**Stage keys (stable, ordered):** `detect → fetch → extract → tokenize → done`. The crawl path
uses `detect → fetch → crawl(page events) → extract → tokenize → done`. The implementer may add
stages; the UI renders whatever arrives (label + status), so the set is not hardcoded client-side.

**Bounded preview:** the server truncates `preview` to **262,144 bytes** on a UTF-8 char
boundary and sets `total_bytes`. This guarantees the DOM never receives the full blob (P2/G2).
`preview_bytes`/`total_bytes` drive the "showing first X of Y" notice (§4.5.3).

> **DESIGN DECISION (file tree source):** the `files[]` array can be produced server-side (one
> regex pass over the output for `<file path="…">` + sizes) **or** parsed client-side from
> `preview` for the visible portion. Recommended: **server-side**, because the full file list
> needs the *complete* output which the client never holds. Mark `files[]` **[required]** for a
> complete tree; if deferred, the client parses the tree from `preview` only and labels it
> "files in preview" — acceptable fallback.

### 7.2 New endpoint — `GET /result/raw` (copy/preview fetch) **[required for G4]**

Serves the full text for **client-side** clipboard copy of large payloads (fixes P3).

**Request:** `GET /result/raw?which=uncompressed|compressed[&result_id=r_4f3a]`
**Response:** `text/plain; charset=utf-8`, the full file contents (same files behind `/download`,
served inline rather than as an attachment). Reuses the existing whitelist mapping
(`uncompressed_output.txt` / `compressed_output.txt`). No new files exposed.

Client copy logic: for payloads already fully in the DOM (≤256 KB) copy directly; otherwise
`fetch('/result/raw?which=…')` → `navigator.clipboard.writeText(text)` with the "Preparing copy…"
state (§6.5). On `clipboard` API failure, fall back to selecting the preview + instructing
⌘/Ctrl-C (§4.8).

### 7.3 Client-side input detection (no backend change) **[required for G3]**

The detected-type badge (§4.3) is computed in JS, mirroring the backend's auto-detection so the
badge matches what the server will do. Vendored as `static/detect.js`. Rules (first match wins):

| Order | Test (on trimmed input) | Result |
|---|---|---|
| 1 | matches a local-path shape: starts with `/`, `~`, `./`, `../`, a Windows drive `C:\`, or `file://` | **blocked · local path** |
| 2 | is an `http(s)://` URL whose host is `localhost`, `127.0.0.0/8`, `10.`, `192.168.`, `172.16–31.`, `169.254.`, `::1`, or `*.internal`/metadata `169.254.169.254` | **blocked · private url** |
| 3 | host is `github.com` + `…/pull/<n>` | github · pr |
| 4 | host is `github.com` + `…/issues/<n>` | github · issue |
| 5 | host is `github.com` + `owner/repo` (no pull/issues) | github · repo |
| 6 | host matches `arxiv.org/abs/` | arxiv |
| 7 | host matches `youtube.com/watch` or `youtu.be/` | youtube |
| 8 | any other `http(s)://` URL | docs · will crawl |
| 9 | matches DOI regex `^10\.\d{4,9}/\S+$` | doi · best-effort |
| 10 | matches bare integer `^\d+$` | pmid · best-effort |
| — | none of the above | no badge; Process stays disabled until a recognizable token is present (`> DESIGN DECISION:` allow submit for any non-empty value and let the server decide — chosen default: **enable Process for any non-empty, non-blocked input**, since the server is the source of truth). |

The client guard is **advisory UX only**; the server re-validates (steps 1–2) authoritatively
before fetching. Never rely on the client guard for security.

### 7.4 Large-output handling (binding) **[required for G2]**

- DOM holds at most `preview` (≤256 KB) — never `total_bytes`.
- The **tree** is built from `files[]` (server) — bounded list, virtualized past 500 rows.
- **Copy/Download** stream from disk via `/result/raw` and `/download`; the full text is never
  materialized in JS except transiently during a copy (then released).
- Clicking a file row scrolls the **preview** to that file's byte offset *if within the 256 KB
  window*; if the file begins past the cap, show an inline note "beyond preview — download for
  full file" instead of scrolling.

### 7.5 Metrics binding (§4.5.1)

| UI value | Backend field | Notes |
|---|---|---|
| Hero: estimated model tokens | `estimated_model_tokens` | `round(uncompressed × 1.37)`; `TOKEN_ESTIMATE_MULTIPLIER` already exists. |
| Uncompressed tokens | `uncompressed_tokens` | `get_token_count()` cl100k_base. |
| Compressed tokens | `compressed_tokens` | from `preprocess_text` pass. |
| `−NN%` delta | *(client)* | `1 − compressed/uncompressed`. |
| Output size | `output_kb` | KB of uncompressed file. |
| Sources processed | `source_count` | 1 today; field future-proofs multi-input. |
| Elapsed | *(client timer)* + `elapsed_s` | client timer is authoritative for display; `elapsed_s` is a server cross-check. |

### 7.6 Misc backend touches

| Change | Tag | Detail |
|---|---|---|
| Inject `__version__` into the shell | [optional] | For the header version string. If absent, hide the version segment. |
| `Cancel` job/abort | [deferrable] | Requires the streamed handler to check a per-job cancel flag (e.g. a `threading.Event` keyed by `result_id`) and stop the crawl loop. New endpoint `POST /cancel?result_id=…` returning 204. If deferred, the **Cancel** button instead just closes the `EventSource` client-side and returns to empty (the server job keeps running to completion but its result is ignored) — label tooltip: "Stops listening; a running crawl may finish in the background." |
| Keep `POST /` | [required] | Retain as a **no-JS fallback**: if JS is disabled, `POST /` works as today (synchronous, raw `<pre>`), so the tool still functions. The SSE path is a progressive enhancement layered on top. |
| `/download` whitelist | [unchanged] | Keep exactly the two-filename whitelist. `/result/raw` reuses the same mapping. |
| SSRF guard `_is_safe_url` | [unchanged] | Called in `/stream` before any fetch, same as `POST /`. |

> **DESIGN DECISION (no-JS fallback):** the page is built as progressive enhancement. Server
> renders the empty shell + working `POST /` form. JS upgrades submit to the SSE flow and swaps
> the raw `<pre>` for the structured result. This preserves function offline *and* without JS,
> and keeps the security contract identical on both paths.

---

## 8. Accessibility checklist (WCAG 2.1 AA)

### 8.1 Contrast pairs (computed, both themes)

Ratios are WCAG contrast against the stated background. Body/label text targets ≥ 4.5:1; large
text (≥ 24px or 19px bold) and UI/graphical components target ≥ 3:1.

| Pair | Dark ratio | Light ratio | Requirement | Pass |
|---|---|---|---|---|
| `--text` on `--bg` | ~14.9:1 | ~15.8:1 | 4.5 | ✓ |
| `--text` on `--surface` | ~13.1:1 | ~16.6:1 | 4.5 | ✓ |
| `--text-muted` on `--bg` | ~6.3:1 | ~6.0:1 | 4.5 | ✓ |
| `--text-faint` on `--bg` (placeholders only) | ~4.6:1 | ~4.5:1 | 4.5 | ✓ |
| `--accent` text on `--bg` | ~6.7:1 | ~5.0:1 | 4.5 | ✓ |
| `--accent-fg` on `--accent` (button) | ~8.2:1 | ~5.0:1 | 4.5 | ✓ |
| `--accent-2` link on `--bg` | ~7.4:1 | ~5.2:1 | 4.5 | ✓ |
| `--danger` text on `--bg` | ~5.6:1 | ~5.7:1 | 4.5 | ✓ |
| `--danger` text on `--danger-bg` | ~5.1:1 | ~5.3:1 | 4.5 | ✓ |
| `--warn` text on `--warn-bg` | ~5.0:1 | ~5.2:1 | 4.5 | ✓ |
| `--focus-ring` vs adjacent surfaces | ~6.5:1 | ~4.8:1 | 3.0 | ✓ |
| `--border` vs `--bg` (non-essential) | ~1.4:1 | — | n/a | decorative |

> **DESIGN DECISION:** `--text-faint` is used **only** for placeholders, disabled labels, and
> line-number gutters — never for content that must be read. If the implementer finds the
> computed ratio of any faint pairing below 4.5:1 on a given surface, promote that text to
> `--text-muted`. Placeholder text is exempt from the 4.5:1 rule but we still meet it.

### 8.2 Focus order

`skip-to-input` (visually hidden, first tab stop) → theme toggle → prompt input → history button
(if present) → Process → [transcript: cards in DOM order | stage-log Cancel | result: view toggle
→ tree (roving) → copy×2 → download×2] → footer links. Focus is **moved programmatically** to:
the result heading (`tabindex="-1"`, focus on reveal) when a run completes; the error heading on
failure; the input when an empty-state card is clicked or "Edit input"/"Retry" is pressed.

### 8.3 ARIA usage

| Region | ARIA |
|---|---|
| Prompt form | `role="search"`; input `aria-label`, `aria-describedby="cmd-hint"`, `aria-invalid="true"` when blocked. |
| Detected badge wrapper | `aria-live="polite"` (announces "Detected: GitHub repository" / "Blocked: local path"). |
| Processing region | `<section role="status" aria-live="polite" aria-atomic="false">`; each new stage line is appended so SRs announce it. The elapsed timer is `aria-hidden="true"` (too chatty); liveness is conveyed by stage announcements. |
| Determinate crawl bar | `role="progressbar"` `aria-valuenow="47"` `aria-valuemin="0"` `aria-valuemax="1000"` `aria-valuetext="47 of 1000 pages"`. Indeterminate bar: `role="progressbar"` with no `aria-valuenow` (= busy). |
| Metrics | `role="group" aria-label="Output metrics"`; each value `aria-label="Estimated model tokens: 195,640"`. |
| Tree | `role="tree"` → `role="treeitem"` with `aria-level`, `aria-expanded`, `aria-setsize`, `aria-posinset`; roving `tabindex`. |
| View toggle | `role="tablist"`/`tab`/`tabpanel`, `aria-selected`. |
| Toast | `role="status" aria-live="polite"`. Error toast `role="alert"`. |
| Error card | heading + `role="alert"` on the message so failures are announced. |
| Theme toggle | `aria-pressed`, dynamic `aria-label`. |

### 8.4 Keyboard map

| Key | Action |
|---|---|
| `/` | Focus the prompt input (unless already in a text field). |
| `Enter` (in input) | Submit (when enabled). |
| `Esc` (in input) | Clear input + dismiss inline rejection. |
| `Esc` (while processing) | Trigger Cancel. |
| `Alt+T` | Toggle theme. |
| `Tab`/`Shift+Tab` | Standard focus traversal (order §8.2). |
| Tree `↑↓←→ Home End Enter` | Navigate/expand/collapse/jump-to-file (§4.5.2). |
| View toggle `←→ Enter/Space` | Switch Overview/Raw. |
| Copy/Download buttons `Enter/Space` | Activate. |

All interactive elements are real `<button>`/`<a>`/`<input>` (or have `role` + `tabindex="0"` +
key handlers for the tree/cards). No focus traps. Visible `:focus-visible` ring (`--ring`)
everywhere.

### 8.5 Reduced motion & misc

- `prefers-reduced-motion: reduce` honored per §6.6 (static fallbacks specified).
- Target sizes ≥ 44×44px for primary actions on narrow/touch (min-height enforced).
- No information conveyed by color alone: error states pair color with an icon + heading text;
  detected/blocked states pair color with the badge label; compression delta shows the number.
- `prefers-contrast: more` (optional): bump `--border` → `--border-strong` and text-muted → text.
- Respect `prefers-color-scheme` for the initial theme when no stored preference exists.

---

## 9. Asset inventory

All icons are **inline SVG**, no icon font, no external files. Shared attributes unless noted:
`viewBox="0 0 24 24"`, `width="1em" height="1em"`, `fill="none"`, `stroke="currentColor"`,
`stroke-width="1.75"`, `stroke-linecap="round"`, `stroke-linejoin="round"`,
`aria-hidden="true"` (decorative) — add `role="img"` + `<title>` when standalone/labeled. Color
comes from `currentColor`, set by the surrounding token. Paste the `<path>`s below into a single
`<svg>` sprite (`<symbol id="i-…">`) or inline per use.

### 9.1 Logo mark (`i-logo`)
A diamond/funnel "conduit" mark — three lines converging into one. Stroke `--accent`.
```svg
<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img"><title>onefilellm</title><path d="M4 5h16M4 5l6 7v6l4 2v-8l6-7"/></svg>
```
> **DESIGN DECISION:** wordmark is set in `--font-mono` lowercase `onefilellm`; no bespoke
> logotype font (offline constraint). The mark + wordmark together are the brand lockup.

### 9.2 Branch (`i-branch`) — GitHub repo
```svg
<path d="M6 3v12M6 21a2 2 0 100-4 2 2 0 000 4zM6 5a2 2 0 100-4 2 2 0 000 4zM18 9a2 2 0 100-4 2 2 0 000 4zM18 7c0 4-6 3-6 8"/>
```
### 9.3 Merge (`i-merge`) — GitHub PR
```svg
<path d="M6 21a2 2 0 100-4 2 2 0 000 4zM6 5a2 2 0 100-4 2 2 0 000 4zM18 9a2 2 0 100-4 2 2 0 000 4zM6 17V7m0 0c0 6 6 4 6 0m6 2c0 6-6 4-6 8"/>
```
### 9.4 Dot-circle (`i-issue`) — GitHub issue
```svg
<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none"/>
```
### 9.5 Doc (`i-doc`) — ArXiv
```svg
<path d="M7 3h7l4 4v14H7zM14 3v4h4M10 13h6M10 17h6"/>
```
### 9.6 Play (`i-play`) — YouTube
```svg
<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M11 9l4 3-4 3z" fill="currentColor" stroke="none"/>
```
### 9.7 Globe (`i-globe`) — docs crawl
```svg
<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>
```
### 9.8 Link (`i-link`) — DOI / PMID
```svg
<path d="M9 15l6-6M10 6l1-1a4 4 0 015.7 5.7l-1 1M14 18l-1 1A4 4 0 017.3 13.3l1-1"/>
```
### 9.9 Shield-x (`i-shield-x`) — blocked
```svg
<path d="M12 3l7 3v5c0 5-3.5 8-7 10-3.5-2-7-5-7-10V6zM9.5 9.5l5 5M14.5 9.5l-5 5"/>
```
### 9.10 Moon (`i-moon`) — dark active
```svg
<path d="M20 14a8 8 0 11-9-11 6 6 0 009 11z"/>
```
### 9.11 Sun (`i-sun`) — light active
```svg
<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/>
```
### 9.12 Spinner (`i-spinner`) — loading (animated `spin 0.8s linear infinite`)
```svg
<path d="M12 3a9 9 0 109 9" />
```
### 9.13 Check (`i-check`) — copied / success
```svg
<path d="M5 12.5l4.5 4.5L19 7"/>
```
### 9.14 Caret-right (`i-caret`) — tree disclosure (rotate 90° when expanded)
```svg
<path d="M9 6l6 6-6 6"/>
```
### 9.15 File (`i-file`) — tree file row
```svg
<path d="M7 3h7l4 4v14H7zM14 3v4h4"/>
```
### 9.16 Copy (`i-copy`) — copy action
```svg
<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h8"/>
```
### 9.17 Download (`i-download`) — download action
```svg
<path d="M12 3v12M8 11l4 4 4-4M5 21h14"/>
```
### 9.18 Clock (`i-clock`) — history (optional)
```svg
<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>
```
### 9.19 Warn-triangle (`i-warn`) — empty/processing-failure heading
```svg
<path d="M12 4l9 16H3zM12 10v4M12 17.5v.5" />
```

### 9.20 Vendored helper files

| File | Size (approx) | Purpose | Justification |
|---|---|---|---|
| `static/app.js` | ~12 KB | All client logic: theme, detection wiring, SSE handling, stage log, tree build/virtualize, preview tint, copy/download, toasts, history, keyboard. | First-party; no dependency. |
| `static/detect.js` | ~2 KB | Input-type detection (§7.3), shared by badge + submit guard. | First-party. |
| `static/sse.js` | ~1.5 KB | Thin wrapper over native `EventSource`: typed event registration, auto-close on `done`/`error`, reconnection suppression (we don't want auto-reconnect on a one-shot job). | Native `EventSource` is built-in; this is only a small ergonomic guard, **not** a polyfill. No third-party code. |
| `static/styles.css` | ~14 KB | All tokens (§2) + component styles. | First-party. |

No npm, no CDN, no web font, no icon font. Everything ships in the repo and runs air-gapped.

---

## 10. Implementation notes & file plan

### 10.1 File plan

> **DESIGN DECISION (split out of single file):** move from the current inline-string template to
> a small static structure. It keeps CSS/JS cacheable, lintable, and within Flask's defaults.

```
extras/
  web_app.py                 # Flask app: routes, SSRF guard (unchanged), detection,
                             #   /stream generator, /result/raw, /download (whitelist), /cancel*
  templates/
    index.html               # the app shell (Jinja) — empty state + no-JS POST fallback
  static/
    styles.css               # §2 tokens + all component CSS
    app.js                   # client controller (§9.20)
    detect.js                # §7.3 detection
    sse.js                   # §9.4 SSE guard
```

- Keep `web_app.py` importing the existing backend functions exactly as today.
- `templates/index.html` server-renders the shell so `POST /` keeps working with JS disabled
  (progressive enhancement). `app.js` upgrades it to the SSE flow on load.
- Flask serves `static/` natively; no new dependency. Only Python dep remains **Flask**.

### 10.2 Security model — preserved (do not loosen)

- `_is_safe_url` (SSRF guard) runs in **both** `POST /` and the new `GET /stream` *before* any
  network fetch. Reject → `error`/`security`.
- Local-path rejection unchanged; surfaced as the security error state, never a fetch.
- `/download` keeps the exact two-filename whitelist. `/result/raw` reuses the **same** mapping
  and adds no new served paths.
- App stays bound to `127.0.0.1`. No auth added (single-user localhost).
- No user input is ever interpolated into a shell, a file path outside the whitelist, or
  `innerHTML` without escaping (the preview injects text via `textContent`, then the tint pass
  wraps only known tag substrings using DOM nodes — never raw `innerHTML` of untrusted content).

### 10.3 Rendering & performance guardrails

- DOM never holds more than `PREVIEW_CAP_BYTES = 262144`.
- Tree virtualizes beyond 500 rows.
- Metric numbers via `Intl.NumberFormat`.
- All event-stream parsing is incremental; the stage log caps at the last 200 lines.
- `app.js` is deferred (`<script src="…" defer>`); no render-blocking JS.

### 10.4 No-JS fallback behavior

With JS off: `templates/index.html` shows the header, prompt, and empty gallery (static), and the
form `POST /` works exactly as the legacy app (synchronous, raw `<pre>` result, two download
links). All security guards apply identically. This guarantees the tool never fully breaks.

### 10.5 Acceptance criteria (implementer self-check)

**Visual system**
- [ ] `:root` and `[data-theme="light"]` blocks pasted verbatim from §2.8; no hardcoded hex
      anywhere else.
- [ ] Dark is default; theme toggle persists to `localStorage.ofllm-theme`; respects
      `prefers-color-scheme` when unset; `color-scheme` set per theme.
- [ ] Only the two system font stacks used; no `@font-face`, no web/icon fonts, no CDN links.
- [ ] All icons are inline SVG from §9.

**Input / detection (G3)**
- [ ] Prompt shows `>` glyph + blinking caret (static under reduced-motion).
- [ ] Live badge matches §4.3 table for all 8 types + 2 blocked cases (debounced 120ms).
- [ ] Blocked local path / private URL show inline rejection and disable Process **before**
      submit; server re-validates and can still return a security error.
- [ ] Empty-state gallery has all 8 cards (§11.2 examples); click fills input + focuses (no
      auto-submit).

**Progress (G1)**
- [ ] Submitting opens `EventSource('/stream?input=…')`; transcript → processing immediately.
- [ ] Stage log appends lines with the §7.1 keys; active line has spinner + caret.
- [ ] Elapsed timer runs and never freezes during a multi-minute job.
- [ ] Crawl shows determinate `N / max pages` from `page` events; others indeterminate shimmer.
- [ ] Cancel present; either aborts via `/cancel` or closes the stream and returns to empty
      (per §7.6 decision), with the documented tooltip.
- [ ] Tab is never frozen; reduced-motion shows a static bar + live timer.

**Result (G2, G6)**
- [ ] Metrics panel shows all six values; **estimated model tokens is the hero** in `--accent`.
- [ ] Compression `−NN%` derived client-side and shown.
- [ ] Overview tree built from `files[]` (or preview fallback), virtualized past 500 rows.
- [ ] Raw preview capped at 256 KB with "Showing first X of Y" notice when truncated; code
      scrolls horizontally, never reflows.
- [ ] Overview ⇄ Raw toggle works and preserves scroll.
- [ ] Clicking a file row jumps the preview (or shows "beyond preview" note).

**Copy / download (G4)**
- [ ] Four actions present (copy/download × uncompressed/compressed).
- [ ] Copy is **client-side** via `navigator.clipboard`; large payloads fetch `/result/raw`
      with a "Preparing copy…" state; success shows "Copied ✓" + toast; failure shows fallback.
- [ ] Downloads hit `/download?filename=…` (whitelist intact) and show a "Download started" toast.
- [ ] No `pyperclip`/server-side clipboard call remains (P3 fixed).

**Errors (G7)**
- [ ] Security rejection → `--danger` card, calm policy copy, "Edit input".
- [ ] Processing failure / `<error>` tag → message verbatim + Retry + cause hint for DOI/PMID.
- [ ] Empty result → `--warn` card, neutral copy.
- [ ] `<error>` tags are detected and rendered as failure, never as content.

**Backend**
- [ ] `GET /stream` SSE endpoint emits `stage`/`page`/`done`/`error` per §7.1 payloads.
- [ ] `GET /result/raw?which=…` serves full text inline for copy.
- [ ] `POST /` retained as no-JS fallback; SSRF guard + whitelist + no-local-paths preserved on
      every path.
- [ ] `estimated_model_tokens = round(uncompressed × 1.37)` computed server-side.

**Accessibility & offline**
- [ ] All §8.1 contrast pairs pass in both themes.
- [ ] Focus order per §8.2; visible `--ring` on every interactive element; focus moved to
      result/error headings on state change.
- [ ] ARIA per §8.3 (progressbar, tree, live regions, tablist, alert).
- [ ] Keyboard map §8.4 fully operable; tree keyboard works.
- [ ] `prefers-reduced-motion` fallbacks per §6.6.
- [ ] Loads and fully functions with **no network** and with **JS disabled** (fallback).
- [ ] Usable down to 480px and at ~360px (graceful) per §3.2.

### 10.6 Open questions (non-blocking; defaults already chosen)

1. **Cancellation depth.** Default: client-side stream close (job may finish in background). True
   server abort (`/cancel` + cancel flag) is **[deferrable]** — promote if background crawls
   waste resources.
2. **`files[]` source.** Default: server-side parse for a complete tree. If the implementer wants
   to ship faster, client-parse from `preview` and label "files in preview" — accepted fallback.
3. **Syntax tint.** Default: cheap regex tint of `<source>/<file>/<error>` tags only; skip if it
   costs >16ms on the 256 KB window.
4. **Raw-text paste mode + `--format` override** (§3.1 optional): **not** specified in v1 to keep
   scope tight. If desired later, add a second prompt mode (segmented "URL | Paste text") and a
   `--format` select bound to a new `format` param on `/stream`. Flagged optional, omitted by
   default.
5. **Session history** (§4.9): included as a localStorage popover; remove if undesired (no backend
   impact).

*End of specification.*
