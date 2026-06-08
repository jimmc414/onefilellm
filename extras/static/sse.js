/*
 * Conduit — sse.js
 * A thin, one-shot guard over the native EventSource (NOT a polyfill).
 *
 * window.Conduit.openStream(url, handlers) -> { close() }
 *   handlers = {
 *     stage(data),         // parsed JSON of an `event: stage` message
 *     page(data),          // parsed JSON of an `event: page` message
 *     done(data),          // parsed JSON of an `event: done` message (terminal)
 *     error(data),         // parsed JSON of an `event: error` message (terminal)
 *     connectError(err)    // native transport error after open (terminal here)
 *   }
 *
 * Contract §4 / §9.20: typed listeners via addEventListener('stage'|'page'|
 * 'done'|'error'), each parsing JSON.parse(e.data). AUTO-CLOSE on `done` and
 * `error` (one-shot job — never auto-reconnect). A native `onerror` after the
 * stream is open is treated as TERMINAL (close + connectError) because this is
 * a one-shot job and EventSource would otherwise keep retrying.
 */
(function () {
  "use strict";

  window.Conduit = window.Conduit || {};

  function openStream(url, handlers) {
    handlers = handlers || {};
    var es = new EventSource(url);
    var closed = false;

    function close() {
      if (closed) return;
      closed = true;
      try {
        es.close();
      } catch (e) {
        /* ignore */
      }
    }

    // Safely invoke a handler; swallow handler-side throws so one bad render
    // can't leave the stream un-closed.
    function call(fn, arg) {
      if (typeof fn !== "function") return;
      try {
        fn(arg);
      } catch (e) {
        if (window.console && console.error) {
          console.error("Conduit.openStream handler error:", e);
        }
      }
    }

    // Parse data; on malformed JSON, surface nothing rather than throwing.
    function parse(e) {
      try {
        return JSON.parse(e.data);
      } catch (err) {
        return null;
      }
    }

    es.addEventListener("stage", function (e) {
      if (closed) return;
      var d = parse(e);
      if (d) call(handlers.stage, d);
    });

    es.addEventListener("page", function (e) {
      if (closed) return;
      var d = parse(e);
      if (d) call(handlers.page, d);
    });

    es.addEventListener("done", function (e) {
      if (closed) return;
      var d = parse(e);
      // Terminal: close BEFORE invoking so no reconnect can fire.
      close();
      call(handlers.done, d || {});
    });

    es.addEventListener("error", function (e) {
      // This fires for BOTH a typed `event: error` message (e.data present)
      // and a native transport error (e.data undefined). Distinguish them.
      if (closed) return;
      if (e && typeof e.data === "string" && e.data.length) {
        // Application-level terminal error event (contract §4.4).
        var d = parse(e);
        close();
        call(handlers.error, d || { subtype: "internal", message: "Stream error." });
        return;
      }
      // Native transport error. For a one-shot job a post-open drop is terminal;
      // do NOT let EventSource auto-reconnect.
      close();
      call(handlers.connectError, e);
    });

    return { close: close };
  }

  window.Conduit.openStream = openStream;
})();
