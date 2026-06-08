/*
 * Conduit — app.js
 * The client controller. Targets the EXACT DOM ids/classes in BUILD CONTRACT §8
 * and consumes the EXACT event JSON in §4. Visual/UX detail per DESIGN SPEC
 * §4 (components), §6 (motion + reduced-motion), §8 (a11y).
 *
 * Offline-safe: vanilla JS, no deps. Depends only on detect.js + sse.js
 * (window.Conduit.detect / window.Conduit.openStream), loaded before it.
 */
(function () {
  "use strict";

  // Idempotent: the inline <head> script already swaps no-js→js; ensure it.
  document.documentElement.classList.add("js");
  document.documentElement.classList.remove("no-js");

  var Conduit = (window.Conduit = window.Conduit || {});

  // ------------------------------------------------------------------ const
  var THEME_KEY = "ofllm-theme";
  var HISTORY_KEY = "ofllm-history";
  var HISTORY_MAX = 10;
  var PREVIEW_CAP_BYTES = 262144; // 256 KB — mirrors server cap (contract §7.2)
  var DETECT_DEBOUNCE_MS = 120;
  var STAGE_LOG_CAP = 200;
  var TREE_VIRTUALIZE_AT = 500;
  var COUNT_UP_MS = 420;
  var COPIED_REVERT_MS = 1600;
  var TOAST_MS = 2400;
  var FLASH_MS = 600;
  var TINT_BUDGET_MS = 16;

  var nf = new Intl.NumberFormat();

  // ----------------------------------------------------------------- helpers
  function $(id) {
    return document.getElementById(id);
  }
  function on(el, ev, fn, opts) {
    if (el) el.addEventListener(ev, fn, opts);
  }
  function reducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }
  function setText(el, t) {
    if (el) el.textContent = t == null ? "" : String(t);
  }
  function show(el) {
    if (el) el.hidden = false;
  }
  function hide(el) {
    if (el) el.hidden = true;
  }
  function isTextField(el) {
    if (!el) return false;
    var tag = el.tagName;
    return (
      tag === "INPUT" ||
      tag === "TEXTAREA" ||
      tag === "SELECT" ||
      el.isContentEditable
    );
  }
  function byteLen(s) {
    // Count UTF-8 bytes without allocating a TextEncoder per call when cheap.
    return enc.encode(s).length;
  }
  var enc = new TextEncoder();

  function svgUse(symbolId, cls) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    if (cls) svg.setAttribute("class", cls);
    var use = document.createElementNS(ns, "use");
    // Both attrs for max compatibility (href + legacy xlink:href).
    use.setAttribute("href", "#" + symbolId);
    use.setAttributeNS(
      "http://www.w3.org/1999/xlink",
      "xlink:href",
      "#" + symbolId
    );
    svg.appendChild(use);
    return svg;
  }

  function fmtElapsed(seconds) {
    // M:SS for ≥60s, else "NN.N s" (spec §4.5.1 Elapsed).
    if (seconds >= 60) {
      var m = Math.floor(seconds / 60);
      var s = Math.floor(seconds % 60);
      return m + ":" + (s < 10 ? "0" + s : s);
    }
    return seconds.toFixed(1) + " s";
  }
  function fmtRelTime(ts) {
    var d = Math.max(0, Date.now() - ts);
    var min = Math.floor(d / 60000);
    if (min < 1) return "now";
    if (min < 60) return min + "m";
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + "h";
    return Math.floor(hr / 24) + "d";
  }

  // ===================================================================== DOM
  var els = {
    html: document.documentElement,
    themeToggle: $("theme-toggle"),
    netStatus: $("net-status"),
    appVersion: $("app-version"),
    form: $("prompt-form"),
    cmd: $("cmd"),
    cmdHint: $("cmd-hint"),
    badge: $("detected-badge"),
    processBtn: $("process-btn"),
    historyBtn: $("history-btn"),
    historyPopover: $("history-popover"),
    transcript: $("transcript"),
    emptyGallery: $("empty-gallery"),
    // processing
    procTitle: $("proc-title"),
    elapsed: $("elapsed"),
    cancelBtn: $("cancel-btn"),
    progressBar: $("progress-bar"),
    progressFill: $("progress-fill"),
    progressLabel: $("progress-label"),
    stageLog: $("stage-log"),
    // result
    resultH: $("result-h"),
    resultSummary: $("result-summary"),
    metrics: $("metrics"),
    mEstimated: $("m-estimated"),
    mUncompressed: $("m-uncompressed"),
    mCompressed: $("m-compressed"),
    mCompressedDelta: $("m-compressed-delta"),
    mSize: $("m-size"),
    mSources: $("m-sources"),
    mElapsed: $("m-elapsed"),
    overviewCount: $("overview-count"),
    viewToggle: $("view-toggle"),
    tabOverview: $("tab-overview"),
    tabRaw: $("tab-raw"),
    panelOverview: $("panel-overview"),
    panelRaw: $("panel-raw"),
    tree: $("tree"),
    preview: $("preview"),
    previewCode: $("preview-code"),
    previewNotice: $("preview-notice"),
    actions: $("actions"),
    copyUncompressed: $("copy-uncompressed"),
    copyCompressed: $("copy-compressed"),
    downloadUncompressed: $("download-uncompressed"),
    downloadCompressed: $("download-compressed"),
    // error
    errorState: $("error-state"),
    errorIcon: $("error-icon"),
    errorHeading: $("error-heading"),
    errorMessage: $("error-message"),
    errorHint: $("error-hint"),
    errorRetry: $("error-retry"),
    errorEdit: $("error-edit"),
    // toast
    toast: $("toast")
  };

  // ============================================================ runtime state
  var state = {
    detected: null, // last Conduit.detect() result
    controller: null, // sse.js controller
    timer: null, // elapsed interval id
    startTs: 0,
    lastInput: "", // input value of the in-flight / last job
    stageKeys: {}, // key -> <li> element (for marking prior done)
    stageCount: 0,
    result: null, // last `done` payload
    treeRows: [], // flat virtualized tree model
    fileOffsets: {}, // file name -> byte offset into preview
    previewTruncated: false,
    activeTab: "overview",
    copyBusy: { uncompressed: false, compressed: false }
  };

  // ================================================================== THEME
  function applyTheme(theme) {
    els.html.setAttribute("data-theme", theme);
    if (els.themeToggle) {
      var toLight = theme === "dark"; // pressing goes to the *other* theme
      // aria-pressed reflects "is a non-default (light) theme active?"
      els.themeToggle.setAttribute(
        "aria-pressed",
        theme === "light" ? "true" : "false"
      );
      els.themeToggle.setAttribute(
        "aria-label",
        toLight ? "Switch to light theme" : "Switch to dark theme"
      );
    }
  }
  function currentTheme() {
    return els.html.getAttribute("data-theme") === "light" ? "light" : "dark";
  }
  function toggleTheme() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (e) {
      /* storage may be unavailable */
    }
    applyTheme(next);
  }
  function initTheme() {
    // The inline head script set data-theme already; just sync ARIA labels.
    applyTheme(currentTheme());
    on(els.themeToggle, "click", toggleTheme);
  }

  // ============================================================== NET STATUS
  function renderNet() {
    if (!els.netStatus) return;
    var online = navigator.onLine;
    els.netStatus.setAttribute("data-online", online ? "true" : "false");
    var label = els.netStatus.querySelector("[data-net-label]");
    if (label) {
      setText(label, online ? "online" : "offline");
    } else {
      setText(els.netStatus, online ? "online" : "offline");
    }
  }
  function initNet() {
    renderNet();
    on(window, "online", renderNet);
    on(window, "offline", renderNet);
  }

  // =============================================================== DETECTION
  // Map detect.js stable types -> the CSS color-group key (.badge[data-kind=…]).
  var BADGE_KIND = {
    github_repo: "repo",
    github_pr: "pr",
    github_issue: "issue",
    arxiv: "arxiv",
    youtube: "youtube",
    docs: "docs",
    doi: "doi",
    pmid: "pmid",
    blocked_local: "blocked",
    blocked_private: "blocked"
  };

  function renderBadge(det) {
    if (!els.badge) return;
    els.badge.textContent = "";
    els.badge.classList.remove("is-in");
    if (!det || !det.type || (!det.label && !det.blocked)) {
      els.badge.removeAttribute("data-type");
      els.badge.removeAttribute("data-kind");
      els.badge.removeAttribute("data-blocked");
      return;
    }
    els.badge.setAttribute("data-type", det.type);
    // data-kind is the CSS styling hook; data-type is kept as a JS hook.
    els.badge.setAttribute("data-kind", BADGE_KIND[det.type] || "docs");
    if (det.blocked) els.badge.setAttribute("data-blocked", "true");
    else els.badge.removeAttribute("data-blocked");

    if (det.glyph) {
      // "icon" class so the CSS `.badge .icon` sizing rule applies.
      els.badge.appendChild(svgUse(det.glyph, "icon badge__glyph"));
    }
    var span = document.createElement("span");
    span.className = "badge__label";
    span.textContent = det.label;
    els.badge.appendChild(span);
    // entry animation (gated by reduced-motion in CSS via the keyframes).
    els.badge.classList.add("is-in");
  }

  function applyDetection() {
    var value = els.cmd ? els.cmd.value : "";
    var det = Conduit.detect ? Conduit.detect(value) : null;
    state.detected = det;
    renderBadge(det);

    var trimmed = (value || "").trim();
    var blocked = !!(det && det.blocked);
    var empty = trimmed === "";

    // hint + aria-invalid
    if (els.cmd) {
      if (blocked) els.cmd.setAttribute("aria-invalid", "true");
      else els.cmd.removeAttribute("aria-invalid");
    }
    if (els.cmdHint) {
      // .is-blocked is the CSS danger hook (.prompt__hint.is-blocked).
      els.cmdHint.classList.remove("is-blocked");
      if (blocked && det.reason === "local") {
        els.cmdHint.classList.add("is-blocked");
        setText(
          els.cmdHint,
          "Local file paths aren't allowed in the web app. Use a URL instead."
        );
      } else if (blocked && det.reason === "private") {
        els.cmdHint.classList.add("is-blocked");
        setText(
          els.cmdHint,
          "That looks like a private or local address — blocked by the security policy."
        );
      } else if (det && det.type === "doi") {
        setText(
          els.cmdHint,
          "Detected: DOI — best-effort; the record may be unavailable."
        );
      } else if (det && det.type === "pmid") {
        setText(
          els.cmdHint,
          "Detected: PMID — best-effort; the record may be unavailable."
        );
      } else if (det && det.type) {
        setText(els.cmdHint, "Detected: " + det.label + " — Enter to run.");
      } else {
        setText(
          els.cmdHint,
          "Paste a GitHub repo, ArXiv, YouTube, docs site, DOI, or PMID — Enter to run."
        );
      }
    }

    // prompt blocked border accent (spec §4.2) — .prompt.is-blocked is the CSS hook
    if (els.form) {
      if (blocked) els.form.classList.add("is-blocked");
      else els.form.classList.remove("is-blocked");
    }

    // Process enabled for any non-empty, non-blocked input (server authoritative).
    if (els.processBtn) els.processBtn.disabled = empty || blocked;
  }

  var detectTimer = null;
  function onCmdInput() {
    if (detectTimer) clearTimeout(detectTimer);
    detectTimer = setTimeout(applyDetection, DETECT_DEBOUNCE_MS);
  }

  // =========================================================== EMPTY GALLERY
  function fillFromCard(value) {
    if (!els.cmd) return;
    els.cmd.value = value;
    applyDetection(); // immediate (no debounce) so badge/hint update at once
    els.cmd.focus();
    var len = els.cmd.value.length;
    try {
      els.cmd.setSelectionRange(len, len);
    } catch (e) {
      /* some input types disallow */
    }
  }
  function initGallery() {
    if (!els.emptyGallery) return;
    var cards = els.emptyGallery.querySelectorAll(".empty__card[data-fill]");
    Array.prototype.forEach.call(cards, function (card) {
      var value = card.getAttribute("data-fill") || "";
      on(card, "click", function () {
        fillFromCard(value);
      });
      on(card, "keydown", function (e) {
        if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          fillFromCard(value);
        }
      });
    });
  }

  // ================================================================== VIEWS
  function setView(view) {
    if (els.transcript) els.transcript.setAttribute("data-view", view);
  }

  // =============================================================== ELAPSED
  function startTimer() {
    state.startTs = Date.now();
    stopTimer();
    var tick = function () {
      var s = (Date.now() - state.startTs) / 1000;
      setText(els.elapsed, fmtElapsed(s));
    };
    tick();
    state.timer = window.setInterval(tick, 250);
  }
  function stopTimer() {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
    }
  }
  function finalElapsedSeconds(fallback) {
    if (state.startTs) return (Date.now() - state.startTs) / 1000;
    return fallback || 0;
  }

  // ================================================================ STAGE LOG
  function resetStageLog() {
    state.stageKeys = {};
    state.stageCount = 0;
    if (els.stageLog) els.stageLog.textContent = "";
  }

  // Class names below mirror the CSS hooks in styles.css (.stage-log__line /
  // __icon / __label / __t and the .spin animation on the active icon).
  function stageLine(label, active) {
    var li = document.createElement("li");
    li.className = "stage-log__line";
    li.setAttribute("data-status", active ? "active" : "done");

    // spinner (active) gets the shared .spin animation class; check when done
    li.appendChild(
      svgUse(active ? "i-spinner" : "i-check", "stage-log__icon" + (active ? " spin" : ""))
    );

    var text = document.createElement("span");
    text.className = "stage-log__label";
    text.textContent = label;
    li.appendChild(text);

    var time = document.createElement("span");
    time.className = "stage-log__t";
    li.appendChild(time);
    return li;
  }

  function markLineDone(li, t) {
    if (!li) return;
    li.setAttribute("data-status", "done");
    var icon = li.querySelector(".stage-log__icon");
    if (icon && icon.parentNode) {
      icon.parentNode.replaceChild(svgUse("i-check", "stage-log__icon"), icon);
    }
    if (t != null) {
      var time = li.querySelector(".stage-log__t");
      if (time) time.textContent = Number(t).toFixed(1) + "s";
    }
  }

  function handleStage(d) {
    if (!els.stageLog) return;
    var key = d.key;
    var status = d.status;
    var existing = key != null ? state.stageKeys[key] : null;

    if (status === "done") {
      if (existing) {
        markLineDone(existing, d.t);
      } else {
        // 'done' without a preceding 'active' — render a completed line.
        var li = stageLine(d.label || key || "", false);
        if (d.t != null) {
          var time = li.querySelector(".stage-log__t");
          if (time) time.textContent = Number(d.t).toFixed(1) + "s";
        }
        els.stageLog.appendChild(li);
        if (key != null) state.stageKeys[key] = li;
        state.stageCount++;
      }
    } else {
      // active
      if (existing) {
        // update label text of the existing active line
        var tx = existing.querySelector(".stage-log__label");
        if (tx && d.label != null) tx.textContent = d.label;
      } else {
        var line = stageLine(d.label || key || "", true);
        els.stageLog.appendChild(line);
        if (key != null) state.stageKeys[key] = line;
        state.stageCount++;
      }
    }

    // Cap at last STAGE_LOG_CAP lines.
    while (els.stageLog.children.length > STAGE_LOG_CAP) {
      var first = els.stageLog.firstChild;
      // keep the key map honest
      for (var k in state.stageKeys) {
        if (state.stageKeys[k] === first) delete state.stageKeys[k];
      }
      els.stageLog.removeChild(first);
    }
  }

  // ============================================================ PAGE PROGRESS
  function setIndeterminate() {
    if (els.progressBar) {
      // CSS shows the shimmer when data-determinate is NOT "true".
      els.progressBar.removeAttribute("data-determinate");
      els.progressBar.setAttribute("data-mode", "indeterminate");
      els.progressBar.removeAttribute("aria-valuenow");
      els.progressBar.removeAttribute("aria-valuemax");
      els.progressBar.removeAttribute("aria-valuetext");
    }
    if (els.progressFill) els.progressFill.style.width = "";
    hide(els.progressLabel);
  }
  function handlePage(d) {
    var fetched = +d.fetched || 0;
    var max = +d.max || 0;
    if (els.progressBar) {
      // CSS switches to the determinate fill on data-determinate="true".
      els.progressBar.setAttribute("data-determinate", "true");
      els.progressBar.setAttribute("data-mode", "determinate");
      els.progressBar.setAttribute("aria-valuenow", String(fetched));
      els.progressBar.setAttribute("aria-valuemin", "0");
      els.progressBar.setAttribute("aria-valuemax", String(max));
      els.progressBar.setAttribute(
        "aria-valuetext",
        fetched + " of " + max + " pages"
      );
    }
    if (els.progressFill) {
      var pct = max > 0 ? Math.min(100, (fetched / max) * 100) : 0;
      els.progressFill.style.width = pct.toFixed(2) + "%";
    }
    if (els.progressLabel) {
      show(els.progressLabel);
      setText(els.progressLabel, fetched + " / " + max + " pages");
    }
    if (els.procTitle) setText(els.procTitle, "Processing · crawl");
  }

  // ============================================================ COUNT-UP
  function countUp(el, target, decimals, suffix) {
    if (!el) return;
    suffix = suffix || "";
    var final = decimals
      ? nf.format(target) // delta handled separately; tokens are integers
      : nf.format(Math.round(target));
    if (reducedMotion()) {
      el.textContent = final + suffix;
      return;
    }
    var start = performance.now();
    function frame(now) {
      var p = Math.min(1, (now - start) / COUNT_UP_MS);
      // ease-out cubic
      var e = 1 - Math.pow(1 - p, 3);
      var v = Math.round(target * e);
      el.textContent = nf.format(v) + suffix;
      if (p < 1) requestAnimationFrame(frame);
      else el.textContent = final + suffix;
    }
    requestAnimationFrame(frame);
  }

  // ============================================================ TREE BUILD
  function ellipsizeMiddle(s, max) {
    if (s.length <= max) return s;
    var keep = max - 1;
    var head = Math.ceil(keep / 2);
    var tail = Math.floor(keep / 2);
    return s.slice(0, head) + "…" + s.slice(s.length - tail);
  }

  function buildTreeModel(result) {
    // Flat model: a source header row + node rows; supports virtualization.
    var rows = [];
    var src = result.source || {};
    var nodes = result.nodes || [];
    var setsize = nodes.length + (result.nodes_truncated ? 1 : 0);

    rows.push({
      kind: "source",
      level: 1,
      type: src.type || "source",
      url: src.url || "",
      count: typeof result.node_count === "number" ? result.node_count : nodes.length,
      posinset: 1,
      setsize: 1
    });

    nodes.forEach(function (n, i) {
      rows.push({
        kind: n.kind === "page" ? "page" : "file",
        level: 2,
        name: n.name || "",
        bytes: n.bytes || 0,
        lines: n.lines || 0,
        posinset: i + 1,
        setsize: setsize
      });
    });

    if (result.nodes_truncated) {
      rows.push({
        kind: "more",
        level: 2,
        more: Math.max(0, (result.node_count || 0) - nodes.length),
        posinset: nodes.length + 1,
        setsize: setsize
      });
    }
    return rows;
  }

  function rowEl(row, index) {
    var div = document.createElement("div");
    div.setAttribute("role", "treeitem");
    div.setAttribute("aria-level", String(row.level));
    div.setAttribute("aria-posinset", String(row.posinset));
    div.setAttribute("aria-setsize", String(row.setsize));
    div.setAttribute("tabindex", index === 0 ? "0" : "-1");
    div.className = "tree__row tree__row--" + row.kind;
    div.setAttribute("data-row-index", String(index));

    if (row.kind === "source") {
      div.setAttribute("aria-expanded", "true");
      var caret = svgUse("i-caret", "tree__caret");
      div.appendChild(caret);
      div.appendChild(svgUse("i-globe", "tree__glyph"));
      var t = document.createElement("span");
      t.className = "tree__type";
      t.textContent = row.type;
      div.appendChild(t);
      var u = document.createElement("span");
      u.className = "tree__url";
      u.textContent = ellipsizeMiddle(row.url, 48);
      if (row.url) u.title = row.url;
      div.appendChild(u);
      var c = document.createElement("span");
      c.className = "tree__count";
      c.textContent = row.count + (row.count === 1 ? " file" : " files");
      div.appendChild(c);
    } else if (row.kind === "more") {
      div.setAttribute("aria-disabled", "true");
      var m = document.createElement("span");
      m.className = "tree__more";
      m.textContent =
        "… " + row.more + " more — download for full list";
      div.appendChild(m);
    } else {
      // file / page
      div.appendChild(
        svgUse(row.kind === "page" ? "i-globe" : "i-file", "tree__glyph")
      );
      var name = document.createElement("span");
      name.className = "tree__name";
      name.textContent = ellipsizeMiddle(row.name, 60);
      name.title = row.name;
      div.appendChild(name);
      var size = document.createElement("span");
      size.className = "tree__size";
      var kb = (row.bytes / 1024).toFixed(1);
      size.textContent = kb + " KB · " + nf.format(row.lines) + " lines";
      div.appendChild(size);
      div.setAttribute("data-file-name", row.name);
      on(div, "click", function () {
        jumpToFile(row.name);
      });
    }
    return div;
  }

  var treeRender = { start: 0, rowH: 28, pad: 8 };
  function renderTree() {
    if (!els.tree) return;
    els.tree.textContent = "";
    var rows = state.treeRows;
    if (rows.length <= TREE_VIRTUALIZE_AT) {
      rows.forEach(function (r, i) {
        els.tree.appendChild(rowEl(r, i));
      });
      els.tree.removeAttribute("data-virtual");
      return;
    }
    // Virtualized: a spacer-based window so the DOM stays bounded.
    els.tree.setAttribute("data-virtual", "true");
    els.tree.style.position = "relative";
    var total = rows.length * treeRender.rowH;
    var spacer = document.createElement("div");
    spacer.style.height = total + "px";
    spacer.style.position = "relative";
    els.tree.appendChild(spacer);

    function paint() {
      var scrollTop = els.tree.scrollTop;
      var viewport = els.tree.clientHeight || 400;
      var first = Math.max(
        0,
        Math.floor(scrollTop / treeRender.rowH) - 5
      );
      var last = Math.min(
        rows.length,
        Math.ceil((scrollTop + viewport) / treeRender.rowH) + 5
      );
      // clear painted rows (keep spacer)
      while (spacer.firstChild) spacer.removeChild(spacer.firstChild);
      for (var i = first; i < last; i++) {
        var el = rowEl(rows[i], i);
        el.style.position = "absolute";
        el.style.top = i * treeRender.rowH + "px";
        el.style.left = "0";
        el.style.right = "0";
        spacer.appendChild(el);
      }
    }
    paint();
    on(els.tree, "scroll", paint);
  }

  // Tree keyboard (spec §4.5.2 / §8.4): roving tabindex over visible rows.
  function focusableRows() {
    if (!els.tree) return [];
    return Array.prototype.slice.call(
      els.tree.querySelectorAll('[role="treeitem"]')
    );
  }
  function moveTreeFocus(current, delta) {
    var rows = focusableRows();
    if (!rows.length) return;
    var idx = rows.indexOf(current);
    var next = idx + delta;
    if (next < 0) next = 0;
    if (next >= rows.length) next = rows.length - 1;
    rows.forEach(function (r) {
      r.setAttribute("tabindex", "-1");
    });
    var target = rows[next];
    target.setAttribute("tabindex", "0");
    target.focus();
  }
  function initTreeKeyboard() {
    if (!els.tree) return;
    on(els.tree, "keydown", function (e) {
      var row = e.target.closest
        ? e.target.closest('[role="treeitem"]')
        : null;
      if (!row) return;
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          moveTreeFocus(row, 1);
          break;
        case "ArrowUp":
          e.preventDefault();
          moveTreeFocus(row, -1);
          break;
        case "Home":
          e.preventDefault();
          moveTreeFocus(row, -9999);
          break;
        case "End":
          e.preventDefault();
          moveTreeFocus(row, 9999);
          break;
        case "ArrowLeft":
          // collapse/parent — flat model: move to source row (top)
          e.preventDefault();
          moveTreeFocus(row, -9999);
          break;
        case "ArrowRight":
          e.preventDefault();
          moveTreeFocus(row, 1);
          break;
        case "Enter":
        case " ":
        case "Spacebar":
          var fn = row.getAttribute("data-file-name");
          if (fn) {
            e.preventDefault();
            jumpToFile(fn);
          }
          break;
      }
    });
  }

  // =========================================================== PREVIEW + TINT
  function setPreview(text, truncated) {
    if (!els.previewCode) return;
    // SECURITY: untrusted text reaches the DOM ONLY via textContent.
    els.previewCode.textContent = text;
    state.previewTruncated = !!truncated;
    // compute byte offsets of each <file .../> & <page .../> opening for jumps
    computeFileOffsets(text);
    // Optional cheap tag tint (spec §4.5.3); skip if it would exceed budget.
    tryTint(text);
  }

  function computeFileOffsets(text) {
    state.fileOffsets = {};
    // Find opening <file path="..."> / <page url="..."> tags, record byte offset.
    var re = /<(file|page)\b[^>]*\b(?:path|url)="([^"]*)"[^>]*>/gi;
    var m;
    while ((m = re.exec(text)) !== null) {
      var name = m[2];
      if (!(name in state.fileOffsets)) {
        // byte offset = utf-8 length of the prefix up to this match
        state.fileOffsets[name] = byteLen(text.slice(0, m.index));
      }
    }
  }

  function tryTint(text) {
    if (!els.previewCode) return;
    if (reducedMotion()) return; // keep it plain; correctness over polish
    var t0 = performance.now();
    // Operate on a detached clone via DOM nodes only (never innerHTML of text).
    // Strategy: walk the single text node, split on known tag substrings, wrap
    // matched tags in tinted spans. Bail if over budget.
    var frag = document.createDocumentFragment();
    var re = /<\/?(?:source|file|page|error)\b[^>]*>/gi;
    var last = 0;
    var m;
    var count = 0;
    while ((m = re.exec(text)) !== null) {
      if (performance.now() - t0 > TINT_BUDGET_MS) {
        return; // abort tint; plain textContent already set — leave as-is
      }
      if (m.index > last) {
        frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      }
      var span = document.createElement("span");
      span.className = "tok-tag";
      span.textContent = m[0];
      frag.appendChild(span);
      last = m.index + m[0].length;
      count++;
      if (count > 4000) return; // safety: too many tags, keep plain
    }
    if (last === 0) return; // no tags matched; leave plain text
    if (last < text.length) {
      frag.appendChild(document.createTextNode(text.slice(last)));
    }
    if (performance.now() - t0 > TINT_BUDGET_MS) return;
    els.previewCode.textContent = "";
    els.previewCode.appendChild(frag);
  }

  function flashPreview() {
    if (!els.preview) return;
    // CSS highlight hook lives on the inner well (.preview__well.is-flash).
    var well = els.preview.querySelector(".preview__well") || els.preview;
    well.classList.add("is-flash");
    setTimeout(function () {
      well.classList.remove("is-flash");
    }, FLASH_MS);
  }

  function jumpToFile(name) {
    // Switch to Raw tab first so the preview is visible.
    setActiveTab("raw");
    var offset = state.fileOffsets[name];
    if (offset == null || offset >= PREVIEW_CAP_BYTES || !els.previewCode) {
      // beyond the cap — inline note instead of scrolling (spec §7.4)
      toast("Beyond preview — download for the full file.", "info");
      return;
    }
    // Approximate scroll: locate the substring offset in characters.
    // We re-find by name to get a character index for scrolling.
    var text = els.previewCode.textContent || "";
    var charIdx = text.indexOf('"' + name + '"');
    if (charIdx < 0) charIdx = 0;
    // Build a measuring range to find vertical offset of that character.
    try {
      var well = els.preview.querySelector(".preview__well") || els.preview;
      // crude line-based scroll: count newlines before charIdx
      var linesBefore = text.slice(0, charIdx).split("\n").length - 1;
      var lineH = parseFloat(getComputedStyle(els.previewCode).lineHeight) || 22;
      well.scrollTop = Math.max(0, linesBefore * lineH - 8);
    } catch (e) {
      /* scrolling is best-effort */
    }
    flashPreview();
  }

  // ============================================================== DONE / RESULT
  function renderResult(d) {
    state.result = d;
    stopTimer();

    var elapsed =
      typeof d.elapsed_s === "number"
        ? d.elapsed_s
        : finalElapsedSeconds(0);

    // summary line
    var srcCount = d.source_count || 1;
    setText(
      els.resultSummary,
      "Done in " +
        fmtElapsed(elapsed) +
        " · " +
        srcCount +
        (srcCount === 1 ? " source" : " sources")
    );

    // metrics
    countUp(els.mEstimated, d.estimated_model_tokens || 0, false);
    countUp(els.mUncompressed, d.uncompressed_tokens || 0, false);
    countUp(els.mCompressed, d.compressed_tokens || 0, false);

    // compression delta (client-derived): −NN%
    var unc = d.uncompressed_tokens || 0;
    var comp = d.compressed_tokens || 0;
    if (els.mCompressedDelta) {
      if (unc > 0) {
        var pct = Math.round((1 - comp / unc) * 100);
        // negative = reduction; show "−NN%". If compressed is larger, "+NN%".
        var sign = pct >= 0 ? "−" : "+";
        els.mCompressedDelta.textContent = sign + Math.abs(pct) + "%";
        els.mCompressedDelta.hidden = false;
      } else {
        els.mCompressedDelta.hidden = true;
      }
    }

    setText(els.mSize, (d.output_kb != null ? d.output_kb.toFixed(2) : "0.00") + " KB");
    setText(els.mSources, nf.format(srcCount));
    setText(els.mElapsed, fmtElapsed(elapsed));

    // aria-labels on metric values (spec §8.3)
    if (els.mEstimated)
      els.mEstimated.setAttribute(
        "aria-label",
        "Estimated model tokens: " + nf.format(d.estimated_model_tokens || 0)
      );

    // overview count chip
    var nodeCount = typeof d.node_count === "number" ? d.node_count : (d.nodes || []).length;
    setText(
      els.overviewCount,
      srcCount +
        (srcCount === 1 ? " source · " : " sources · ") +
        nf.format(nodeCount) +
        (nodeCount === 1 ? " file" : " files")
    );

    // tree
    state.treeRows = buildTreeModel(d);
    renderTree();

    // preview
    setPreview(d.preview || "", !!d.truncated);

    // truncation notice
    if (els.previewNotice) {
      if (d.truncated) {
        var totalKb = ((d.total_bytes || 0) / 1024).toFixed(2);
        var totalMb = (d.total_bytes || 0) / (1024 * 1024);
        var totalLabel =
          totalMb >= 1 ? totalMb.toFixed(2) + " MB" : totalKb + " KB";
        setText(
          els.previewNotice,
          "Showing first 256 KB of " +
            totalLabel +
            " — download or copy for the complete output."
        );
        show(els.previewNotice);
      } else {
        hide(els.previewNotice);
      }
    }

    // default to Overview tab
    setActiveTab("overview", true);

    setView("result");

    // move focus to result heading (spec §8.2)
    if (els.resultH) {
      els.resultH.focus();
    }
  }

  // ================================================================== ERROR
  var ERROR_PRESETS = {
    security: {
      dataError: "security",
      icon: "i-shield-x",
      heading: "Blocked by the security policy",
      retry: false
    },
    processing: {
      dataError: "processing",
      icon: "i-warn",
      heading: "Couldn't process that source",
      retry: true
    },
    empty: {
      dataError: "empty",
      icon: "i-warn",
      heading: "Nothing to show",
      retry: false
    }
  };

  function renderError(d) {
    stopTimer();
    var subtype = d && d.subtype ? d.subtype : "processing";

    // busy → toast only, no card (contract §4.4). Transcript stays put.
    if (subtype === "busy") {
      toast(
        d.message || "A job is already running — wait for it to finish.",
        "error"
      );
      restorePrompt();
      return;
    }

    // internal → render as a processing card (contract §4.4).
    var key = subtype === "internal" ? "processing" : subtype;
    var preset = ERROR_PRESETS[key] || ERROR_PRESETS.processing;

    if (els.errorState) els.errorState.setAttribute("data-error", preset.dataError);

    if (els.errorIcon) {
      els.errorIcon.textContent = "";
      els.errorIcon.appendChild(svgUse(preset.icon, "error__glyph"));
    }
    setText(els.errorHeading, preset.heading);

    // security/empty use calm canned copy; processing/internal show verbatim msg.
    if (key === "security") {
      setText(
        els.errorMessage,
        d && d.message
          ? d.message
          : "That address is local, private, or internal, so the web app won't fetch it. This protects against SSRF. Try a public URL instead."
      );
    } else if (key === "empty") {
      setText(
        els.errorMessage,
        d && d.message
          ? d.message
          : "The source was reached but produced no extractable content (an empty crawl or a video without a transcript)."
      );
    } else {
      // processing / internal — backend message verbatim, mono
      setText(els.errorMessage, d && d.message ? d.message : "An unexpected error occurred.");
    }

    // DOI/PMID cause hint (best-effort) — only for processing failures.
    if (els.errorHint) {
      var det = state.detected;
      var isDoiPmid =
        det && (det.type === "doi" || det.type === "pmid");
      if (key === "processing" && isDoiPmid) {
        setText(
          els.errorHint,
          "DOIs and PMIDs are best-effort and often unavailable."
        );
        show(els.errorHint);
      } else {
        hide(els.errorHint);
        setText(els.errorHint, "");
      }
    }

    // Retry hidden for security/empty (spec §5.7/§5.9).
    if (els.errorRetry) els.errorRetry.hidden = !preset.retry;

    restorePrompt();
    setView("error");

    // move focus to error heading (spec §8.2)
    if (els.errorHeading) {
      if (!els.errorHeading.hasAttribute("tabindex"))
        els.errorHeading.setAttribute("tabindex", "-1");
      els.errorHeading.focus();
    }
  }

  // ============================================================ SUBMIT / RUN
  function restorePrompt() {
    if (els.cmd) els.cmd.removeAttribute("readonly");
    if (els.form) els.form.removeAttribute("data-submitting");
    setProcessLoading(false);
  }

  function setProcessLoading(loading) {
    if (!els.processBtn) return;
    if (loading) {
      els.processBtn.setAttribute("aria-busy", "true");
      els.processBtn.disabled = true;
      els.processBtn.setAttribute("data-loading", "true");
    } else {
      els.processBtn.removeAttribute("aria-busy");
      els.processBtn.removeAttribute("data-loading");
      // re-enable per detection state
      applyDetection();
    }
  }

  function startJob(value) {
    state.lastInput = value;
    pushHistory(value);

    // prep processing view
    setProcessLoading(true);
    if (els.cmd) els.cmd.setAttribute("readonly", "readonly");
    if (els.form) els.form.setAttribute("data-submitting", "true");
    if (els.procTitle) setText(els.procTitle, "Processing");
    resetStageLog();
    setIndeterminate();
    setView("processing");
    startTimer();

    if (state.controller) {
      state.controller.close();
      state.controller = null;
    }

    var url = "/stream?input=" + encodeURIComponent(value);
    state.controller = Conduit.openStream(url, {
      stage: handleStage,
      page: handlePage,
      done: function (d) {
        state.controller = null;
        renderResult(d);
        restorePrompt();
      },
      error: function (d) {
        state.controller = null;
        renderError(d);
      },
      connectError: function () {
        state.controller = null;
        renderError({
          subtype: "internal",
          message:
            "Lost connection to the server while processing. Please retry."
        });
      }
    });
  }

  function onSubmit(e) {
    if (e) e.preventDefault();
    if (!els.cmd) return;
    var value = els.cmd.value.trim();
    if (value === "") return;
    // re-validate; if blocked, stay (no request)
    var det = Conduit.detect ? Conduit.detect(value) : null;
    state.detected = det;
    if (det && det.blocked) {
      applyDetection();
      if (els.cmd) els.cmd.focus();
      return;
    }
    startJob(value);
  }

  function cancelJob() {
    if (state.controller) {
      state.controller.close();
      state.controller = null;
    }
    stopTimer();
    restorePrompt();
    setView("empty");
    if (els.cmd) {
      els.cmd.focus();
    }
  }

  // ================================================================== COPY
  function copyFromText(text) {
    if (
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function"
    ) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("clipboard unavailable"));
  }

  function selectPreview() {
    if (!els.previewCode) return;
    try {
      var range = document.createRange();
      range.selectNodeContents(els.previewCode);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    } catch (e) {
      /* best-effort */
    }
  }

  function copiedFeedback(btn) {
    if (!btn) return;
    // Swap only the action word ("Copy" -> "Copied ✓") so the icon + caption
    // survive; .btn__action is the template/CSS hook (`.btn.is-copied .btn__action`).
    var labelEl = btn.querySelector(".btn__action") || btn;
    var prev = labelEl.textContent;
    btn.setAttribute("data-copied", "true");
    btn.classList.add("is-copied");
    labelEl.textContent = "Copied ✓";
    setTimeout(function () {
      btn.removeAttribute("data-copied");
      btn.classList.remove("is-copied");
      labelEl.textContent = prev;
    }, COPIED_REVERT_MS);
  }
  function preparingFeedback(btn, on) {
    if (!btn) return;
    if (on) btn.setAttribute("data-preparing", "true");
    else btn.removeAttribute("data-preparing");
  }

  function doCopy(which, btn) {
    if (state.copyBusy[which]) return;
    var r = state.result;
    // If the preview already holds the FULL uncompressed output (not truncated),
    // and we're copying uncompressed, copy straight from the DOM (spec §6.5).
    if (which === "uncompressed" && r && !r.truncated && els.previewCode) {
      copyFromText(els.previewCode.textContent || "").then(
        function () {
          copiedFeedback(btn);
          toast("Copied to clipboard", "success");
        },
        function () {
          toast(
            "Copy failed — select the preview and press ⌘/Ctrl-C",
            "error"
          );
          selectPreview();
        }
      );
      return;
    }

    // Otherwise fetch the full text from /result/raw, then copy.
    state.copyBusy[which] = true;
    preparingFeedback(btn, true);
    fetch("/result/raw?which=" + encodeURIComponent(which))
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.text();
      })
      .then(function (text) {
        return copyFromText(text);
      })
      .then(function () {
        copiedFeedback(btn);
        toast("Copied to clipboard", "success");
      })
      .catch(function () {
        toast(
          "Copy failed — select the preview and press ⌘/Ctrl-C",
          "error"
        );
        selectPreview();
      })
      .then(function () {
        state.copyBusy[which] = false;
        preparingFeedback(btn, false);
      });
  }

  // ============================================================== DOWNLOADS
  function initDownloads() {
    on(els.downloadUncompressed, "click", function () {
      toast("Download started", "info");
    });
    on(els.downloadCompressed, "click", function () {
      toast("Download started", "info");
    });
  }

  // ============================================================== VIEW TOGGLE
  function setActiveTab(tab, skipScrollPreserve) {
    var prev = state.activeTab;
    // preserve scroll positions per panel
    var scrolls = {};
    if (!skipScrollPreserve) {
      if (els.panelOverview) scrolls.overview = els.panelOverview.scrollTop;
      if (els.panelRaw) scrolls.raw = els.panelRaw.scrollTop;
    }
    state.activeTab = tab;
    var isOverview = tab === "overview";
    if (els.tabOverview) {
      els.tabOverview.setAttribute("aria-selected", isOverview ? "true" : "false");
      els.tabOverview.setAttribute("tabindex", isOverview ? "0" : "-1");
    }
    if (els.tabRaw) {
      els.tabRaw.setAttribute("aria-selected", !isOverview ? "true" : "false");
      els.tabRaw.setAttribute("tabindex", !isOverview ? "0" : "-1");
    }
    if (els.panelOverview) els.panelOverview.hidden = !isOverview;
    if (els.panelRaw) els.panelRaw.hidden = isOverview;
    // restore the scroll for the now-visible panel
    if (!skipScrollPreserve) {
      if (isOverview && els.panelOverview && scrolls.overview != null)
        els.panelOverview.scrollTop = scrolls.overview;
      if (!isOverview && els.panelRaw && scrolls.raw != null)
        els.panelRaw.scrollTop = scrolls.raw;
    }
  }
  function initViewToggle() {
    on(els.tabOverview, "click", function () {
      setActiveTab("overview");
    });
    on(els.tabRaw, "click", function () {
      setActiveTab("raw");
    });
    var tabs = [els.tabOverview, els.tabRaw];
    tabs.forEach(function (tab) {
      on(tab, "keydown", function (e) {
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
          e.preventDefault();
          var next = state.activeTab === "overview" ? "raw" : "overview";
          setActiveTab(next);
          var target = next === "overview" ? els.tabOverview : els.tabRaw;
          if (target) target.focus();
        } else if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          // already activated on focus move; ensure state matches the focused tab
          if (e.target === els.tabOverview) setActiveTab("overview");
          else if (e.target === els.tabRaw) setActiveTab("raw");
        }
      });
    });
  }

  // ================================================================== TOAST
  var toastTimer = null;
  function toast(message, variant) {
    if (!els.toast) return;
    variant = variant || "info";
    els.toast.setAttribute("data-variant", variant);
    els.toast.setAttribute("role", variant === "error" ? "alert" : "status");
    els.toast.textContent = "";
    var glyph =
      variant === "success" ? "i-check" : variant === "error" ? "i-warn" : "i-clock";
    // "icon" class so the CSS `.toast .icon` color rule applies.
    els.toast.appendChild(svgUse(glyph, "icon toast__glyph"));
    var span = document.createElement("span");
    span.className = "toast__msg";
    span.textContent = message;
    els.toast.appendChild(span);
    // Visibility is driven by [hidden] in the CSS; .is-in plays the entry anim.
    els.toast.setAttribute("data-show", "true");
    els.toast.hidden = false;
    els.toast.classList.add("is-in");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      els.toast.removeAttribute("data-show");
      els.toast.classList.remove("is-in");
      els.toast.hidden = true;
    }, TOAST_MS);
  }

  // ================================================================ HISTORY
  function readHistory() {
    try {
      var raw = localStorage.getItem(HISTORY_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }
  function writeHistory(arr) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(arr.slice(0, HISTORY_MAX)));
    } catch (e) {
      /* ignore */
    }
  }
  function pushHistory(value) {
    var arr = readHistory().filter(function (it) {
      return it && it.value !== value;
    });
    var det = Conduit.detect ? Conduit.detect(value) : null;
    arr.unshift({
      value: value,
      type: det && det.type ? det.type : null,
      ts: Date.now()
    });
    writeHistory(arr);
    renderHistoryButton();
  }
  function renderHistoryButton() {
    if (!els.historyBtn) return;
    var arr = readHistory();
    els.historyBtn.hidden = arr.length === 0;
  }
  function glyphForType(type) {
    switch (type) {
      case "github_repo":
        return "i-branch";
      case "github_pr":
        return "i-merge";
      case "github_issue":
        return "i-issue";
      case "arxiv":
        return "i-doc";
      case "youtube":
        return "i-play";
      case "docs":
        return "i-globe";
      case "doi":
      case "pmid":
        return "i-link";
      default:
        return "i-clock";
    }
  }
  function renderHistoryPopover() {
    if (!els.historyPopover) return;
    var arr = readHistory();
    els.historyPopover.textContent = "";
    arr.forEach(function (it) {
      var item = document.createElement("button");
      item.type = "button";
      // popover__* are the CSS styling hooks; history__* kept as JS hooks.
      item.className = "popover__item history__item";
      item.setAttribute("role", "menuitem");
      item.appendChild(svgUse(glyphForType(it.type), "icon history__glyph"));
      var v = document.createElement("span");
      v.className = "popover__value history__value";
      v.textContent = ellipsizeMiddle(it.value, 40);
      v.title = it.value;
      item.appendChild(v);
      var t = document.createElement("span");
      t.className = "popover__time history__time";
      t.textContent = fmtRelTime(it.ts);
      item.appendChild(t);
      on(item, "click", function () {
        fillFromCard(it.value);
        closeHistory();
      });
      els.historyPopover.appendChild(item);
    });
    var clear = document.createElement("button");
    clear.type = "button";
    clear.className = "history__clear";
    clear.textContent = "Clear";
    on(clear, "click", function () {
      writeHistory([]);
      renderHistoryButton();
      closeHistory();
    });
    els.historyPopover.appendChild(clear);
  }
  function openHistory() {
    if (!els.historyPopover) return;
    renderHistoryPopover();
    els.historyPopover.hidden = false;
    if (els.historyBtn) els.historyBtn.setAttribute("aria-expanded", "true");
  }
  function closeHistory() {
    if (!els.historyPopover) return;
    els.historyPopover.hidden = true;
    if (els.historyBtn) els.historyBtn.setAttribute("aria-expanded", "false");
  }
  function initHistory() {
    renderHistoryButton();
    on(els.historyBtn, "click", function () {
      if (els.historyPopover && els.historyPopover.hidden) openHistory();
      else closeHistory();
    });
    on(document, "click", function (e) {
      if (
        els.historyPopover &&
        !els.historyPopover.hidden &&
        !els.historyPopover.contains(e.target) &&
        e.target !== els.historyBtn &&
        (!els.historyBtn || !els.historyBtn.contains(e.target))
      ) {
        closeHistory();
      }
    });
  }

  // ============================================================ KEYBOARD MAP
  function initKeyboard() {
    // '/' focuses #cmd unless already in a text field (spec §8.4).
    on(document, "keydown", function (e) {
      if (e.key === "/" && !isTextField(document.activeElement)) {
        if (els.cmd) {
          e.preventDefault();
          els.cmd.focus();
        }
        return;
      }
      // Alt+T toggles theme.
      if ((e.key === "t" || e.key === "T") && e.altKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        toggleTheme();
        return;
      }
      // Esc while processing → cancel.
      if (e.key === "Escape") {
        var view = els.transcript
          ? els.transcript.getAttribute("data-view")
          : "";
        if (view === "processing") {
          e.preventDefault();
          cancelJob();
          return;
        }
        // Esc in the input clears it + dismisses inline rejection.
        if (document.activeElement === els.cmd && els.cmd) {
          els.cmd.value = "";
          applyDetection();
        }
        // close history popover if open
        if (els.historyPopover && !els.historyPopover.hidden) closeHistory();
      }
    });
  }

  // ============================================================ INIT / WIRE
  function init() {
    initTheme();
    initNet();
    initGallery();
    initViewToggle();
    initTreeKeyboard();
    initDownloads();
    initHistory();
    initKeyboard();

    // Prompt detection wiring.
    on(els.cmd, "input", onCmdInput);
    applyDetection(); // initial state (disables Process when empty)

    // Submit handler.
    on(els.form, "submit", onSubmit);

    // Cancel.
    on(els.cancelBtn, "click", cancelJob);

    // Error card buttons.
    on(els.errorRetry, "click", function () {
      if (state.lastInput) {
        // re-validate then run
        var det = Conduit.detect ? Conduit.detect(state.lastInput) : null;
        if (det && det.blocked) {
          setView("empty");
          if (els.cmd) {
            els.cmd.value = state.lastInput;
            applyDetection();
            els.cmd.focus();
          }
          return;
        }
        startJob(state.lastInput);
      }
    });
    on(els.errorEdit, "click", function () {
      setView("empty");
      if (els.cmd) {
        if (state.lastInput) els.cmd.value = state.lastInput;
        applyDetection();
        els.cmd.focus();
      }
    });

    // Copy buttons.
    on(els.copyUncompressed, "click", function () {
      doCopy("uncompressed", els.copyUncompressed);
    });
    on(els.copyCompressed, "click", function () {
      doCopy("compressed", els.copyCompressed);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose a tiny surface for debugging / template hooks (non-essential).
  Conduit.app = {
    setView: setView,
    toast: toast,
    renderResult: renderResult,
    renderError: renderError
  };
})();
