/*
 * Conduit — detect.js
 * Pure input-type detection (no DOM). Mirrors the BUILD CONTRACT §7.4 dispatch
 * order (first match wins) and the DESIGN SPEC §4.3 badge table. The SERVER is
 * authoritative; this is advisory UX only and must never be relied on for
 * security.
 *
 * window.Conduit.detect(value) -> { type, label, glyph, blocked }
 *   type    : stable key — one of
 *             "github_repo" | "github_pr" | "github_issue" | "arxiv" |
 *             "youtube" | "docs" | "doi" | "pmid" |
 *             "blocked_local" | "blocked_private" | null
 *   label   : badge text, e.g. "github · repo"  (null when no badge)
 *   glyph   : icon <symbol> id, e.g. "i-branch" (null when no badge)
 *   blocked : true for the two blocked cases, else false
 *             (blocked cases also carry `reason`: "local" | "private")
 */
(function () {
  "use strict";

  window.Conduit = window.Conduit || {};

  // ---- helpers ------------------------------------------------------------

  // Local/relative path shapes (contract §7.4 step 1, spec §7.3 row 1):
  //   leading "/", "~", "./", "../", a Windows drive "C:\", or "file://".
  // NOTE: a leading "//" (protocol-relative) also reads as a path here, which
  // is harmless advisory behavior — the server re-validates authoritatively.
  function isLocalPathShape(s) {
    if (s.indexOf("file://") === 0) return true;
    if (s[0] === "/" || s[0] === "~") return true;
    if (s.indexOf("./") === 0 || s.indexOf("../") === 0) return true;
    // Windows drive letter: C:\  or  C:/
    if (/^[A-Za-z]:[\\/]/.test(s)) return true;
    return false;
  }

  // Private / internal / metadata host (contract §7.4 step 2, spec §7.3 row 2).
  // Mirrors the server's _is_safe_url intent for the badge. Operates on the
  // already-lowercased hostname (host part only; ports/userinfo stripped by URL).
  function isPrivateHost(host) {
    if (!host) return true; // no resolvable host → treat as blocked (advisory)

    // Strip an IPv6 bracket wrapper: "[::1]" -> "::1"
    if (host[0] === "[" && host[host.length - 1] === "]") {
      host = host.slice(1, -1);
    }

    // Named hosts the server rejects outright.
    if (host === "localhost") return true;
    if (host === "metadata.google.internal") return true;
    // *.internal and the GCP/AWS metadata names.
    if (host === "internal" || host.endsWith(".internal")) return true;

    // IPv6 loopback / link-local / unique-local.
    if (host === "::1") return true;
    if (host === "::") return true;
    if (host.indexOf("fe80:") === 0) return true; // link-local
    if (host.indexOf("fc") === 0 || host.indexOf("fd") === 0) {
      // unique-local fc00::/7 — only when it parses as IPv6 (has a colon)
      if (host.indexOf(":") !== -1) return true;
    }

    // IPv4 dotted-quad ranges the server's ipaddress checks would reject:
    //   127.0.0.0/8 (loopback), 10.0.0.0/8, 192.168.0.0/16,
    //   172.16.0.0–172.31.255.255, 169.254.0.0/16 (link-local incl. metadata),
    //   0.0.0.0/8 (reserved).
    var m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (m) {
      var a = +m[1], b = +m[2];
      if (a === 127) return true;
      if (a === 10) return true;
      if (a === 0) return true;
      if (a === 192 && b === 168) return true;
      if (a === 172 && b >= 16 && b <= 31) return true;
      if (a === 169 && b === 254) return true;
    }
    return false;
  }

  // Parse with the native URL parser; fall back to null on failure.
  function tryUrl(s) {
    try {
      return new URL(s);
    } catch (e) {
      return null;
    }
  }

  // Badge descriptor factory (keeps the table compact + consistent).
  function badge(type, label, glyph) {
    return { type: type, label: label, glyph: glyph, blocked: false };
  }
  function block(reason, label) {
    return {
      type: reason === "local" ? "blocked_local" : "blocked_private",
      label: label,
      glyph: "i-shield-x",
      blocked: true,
      reason: reason
    };
  }

  // ---- the detector -------------------------------------------------------

  function detect(value) {
    var none = { type: null, label: null, glyph: null, blocked: false };
    if (value == null) return none;
    var s = String(value).trim();
    if (s === "") return none;

    // 1) local-path shape → blocked (local path)
    if (isLocalPathShape(s)) {
      return block("local", "blocked · local path");
    }

    var lower = s.toLowerCase();
    var isHttp = lower.indexOf("http://") === 0 || lower.indexOf("https://") === 0;

    if (isHttp) {
      var u = tryUrl(s);
      var host = u ? u.hostname.toLowerCase() : "";

      // 2) http(s) whose host is private/internal/metadata → blocked (private url)
      if (isPrivateHost(host)) {
        return block("private", "blocked · private url");
      }

      var path = u ? u.pathname : "";

      // host-suffix test so "www.github.com" / "github.com" both match,
      // but "evilgithub.com.attacker.net" does not.
      function hostIs(domain) {
        return host === domain || host.endsWith("." + domain);
      }

      // 3) github.com + /pull/<n>
      if (hostIs("github.com")) {
        if (/\/pull\/\d+/.test(path)) {
          return badge("github_pr", "github · pr", "i-merge");
        }
        // 4) github.com + /issues/<n>
        if (/\/issues\/\d+/.test(path)) {
          return badge("github_issue", "github · issue", "i-issue");
        }
        // 5) github.com (other) → repo
        return badge("github_repo", "github · repo", "i-branch");
      }

      // 6) arxiv.org
      if (hostIs("arxiv.org")) {
        return badge("arxiv", "arxiv", "i-doc");
      }

      // 7) youtube.com/watch | youtu.be/
      if (hostIs("youtube.com") && /\/watch/.test(path)) {
        return badge("youtube", "youtube · transcript", "i-play");
      }
      if (hostIs("youtu.be")) {
        return badge("youtube", "youtube · transcript", "i-play");
      }

      // 8) any other http(s) → docs crawl
      return badge("docs", "docs · will crawl", "i-globe");
    }

    // 9) DOI  ^10\.\d{4,9}/\S+$
    if (/^10\.\d{4,9}\/\S+$/.test(s)) {
      return badge("doi", "doi · best-effort", "i-link");
    }

    // 10) bare integer ^\d+$  → PMID
    if (/^\d+$/.test(s)) {
      return badge("pmid", "pmid · best-effort", "i-link");
    }

    // none of the above — no badge; Process still enabled for non-empty,
    // non-blocked input (server is the source of truth — contract §7.4).
    return none;
  }

  window.Conduit.detect = detect;
})();
