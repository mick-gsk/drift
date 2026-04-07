/**
 * Drift "Prove It Yourself" — Client-side JSON Results Viewer.
 *
 * Renders drift compact-JSON output as interactive findings cards.
 * Runs entirely in the browser — no data leaves the client.
 *
 * Usage: include this script on pages that contain a drop-zone
 * element with class "drift-prove-drop" and a sibling results
 * container with class "drift-prove-results".
 *
 * @license MIT
 */
(function () {
  "use strict";

  /* ── Constants ───────────────────────────────── */

  var SEVERITY_COLORS = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#eab308",
    low: "#3b82f6",
    info: "#6b7280",
  };

  var SEVERITY_LABELS = {
    critical: "Critical",
    high: "High",
    medium: "Medium",
    low: "Low",
    info: "Info",
  };

  /* ── Helpers ─────────────────────────────────── */

  /** Create an element with optional class + text. */
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /** Sanitize score to at most 3 decimals. */
  function fmtScore(n) {
    return typeof n === "number" ? n.toFixed(3) : "—";
  }

  /** Validate the dropped JSON against the drift compact schema. */
  function validate(data) {
    if (typeof data !== "object" || data === null) return "Invalid JSON: not an object.";
    if (!data.drift_score && data.drift_score !== 0) return 'Missing required field: "drift_score".';
    if (!data.compact_summary) return 'Missing required field: "compact_summary".';
    if (!Array.isArray(data.fix_first) && !Array.isArray(data.findings_compact))
      return 'Missing required field: "fix_first" or "findings_compact".';
    return null;
  }

  /** Pick the most relevant findings array (fix_first preferred). */
  function getFindings(data, max) {
    var items = Array.isArray(data.fix_first) && data.fix_first.length > 0
      ? data.fix_first
      : data.findings_compact || [];
    return items.slice(0, max);
  }

  /* ── Renderers ───────────────────────────────── */

  /** Build the score badge element. */
  function renderScore(data) {
    var severity = (data.severity || "info").toLowerCase();
    var color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;

    var badge = el("div", "drift-prove-score");
    badge.style.borderColor = color;

    var num = el("span", "drift-prove-score-num", fmtScore(data.drift_score));
    num.style.color = color;
    badge.appendChild(num);

    var label = el("span", "drift-prove-score-label");
    label.textContent = (SEVERITY_LABELS[severity] || severity) + " severity";
    badge.appendChild(label);

    // Trend arrow if available
    if (data.trend && typeof data.trend.delta === "number") {
      var arrow = data.trend.delta <= 0 ? " \u25BC " : " \u25B2 ";
      var dir = data.trend.direction || (data.trend.delta <= 0 ? "improving" : "degrading");
      var trend = el("span", "drift-prove-score-trend");
      trend.textContent = arrow + Math.abs(data.trend.delta).toFixed(3) + " " + dir;
      trend.style.color = data.trend.delta <= 0 ? "#22c55e" : "#ef4444";
      badge.appendChild(trend);
    }

    return badge;
  }

  /** Build the summary line. */
  function renderSummary(data) {
    var s = data.summary || {};
    var cs = data.compact_summary || {};
    var parts = [];
    if (s.total_files) parts.push(s.total_files + " files");
    if (s.total_functions) parts.push(s.total_functions + " functions");
    if (cs.findings_deduplicated != null) parts.push(cs.findings_deduplicated + " findings");
    else if (cs.findings_total != null) parts.push(cs.findings_total + " findings");
    if (cs.high_count) parts.push(cs.high_count + " high");
    if (cs.critical_count) parts.push(cs.critical_count + " critical");

    var line = el("div", "drift-prove-summary", parts.join(" \u00B7 "));
    return line;
  }

  /** Build a single finding card. */
  function renderFinding(item, index) {
    var card = el("div", "drift-prove-finding");

    // Severity pill
    var sev = (item.severity || "info").toLowerCase();
    var pill = el("span", "drift-prove-severity", SEVERITY_LABELS[sev] || sev);
    pill.style.background = SEVERITY_COLORS[sev] || SEVERITY_COLORS.info;
    card.appendChild(pill);

    // Signal abbrev
    var abbr = el("span", "drift-prove-signal", item.signal_abbrev || "");
    card.appendChild(abbr);

    // Title
    var title = el("div", "drift-prove-finding-title", item.title || "(untitled)");
    card.appendChild(title);

    // File + line
    if (item.file) {
      var loc = item.file;
      if (item.start_line) loc += ":" + item.start_line;
      var fileLine = el("div", "drift-prove-finding-file", loc);
      card.appendChild(fileLine);
    }

    // Next step
    var step = item.next_step || item.description;
    if (step) {
      var ns = el("div", "drift-prove-finding-next", step);
      card.appendChild(ns);
    }

    return card;
  }

  /** Render the full results into a container. */
  function renderResults(container, data, maxFindings) {
    container.innerHTML = "";

    // Header row: score + summary
    var header = el("div", "drift-prove-header");
    header.appendChild(renderScore(data));
    header.appendChild(renderSummary(data));
    container.appendChild(header);

    // Findings
    var findings = getFindings(data, maxFindings);
    if (findings.length > 0) {
      var listLabel = el("div", "drift-prove-list-label", "Fix first — highest-impact findings:");
      container.appendChild(listLabel);

      var list = el("div", "drift-prove-list");
      for (var i = 0; i < findings.length; i++) {
        list.appendChild(renderFinding(findings[i], i));
      }
      container.appendChild(list);
    } else {
      var empty = el("div", "drift-prove-empty");
      empty.textContent = "No findings with fix-first priority. Your codebase may be in good shape \u2014 or the repo is small. ";
      container.appendChild(empty);
    }

    // Analysis metadata
    if (data.version || data.analyzed_at) {
      var meta = el("div", "drift-prove-meta");
      var parts = [];
      if (data.version) parts.push("drift v" + data.version);
      if (data.analyzed_at) {
        try { parts.push(new Date(data.analyzed_at).toLocaleString()); } catch (e) { /* skip */ }
      }
      if (data.summary && data.summary.analysis_duration_seconds) {
        parts.push(data.summary.analysis_duration_seconds.toFixed(1) + "s");
      }
      meta.textContent = parts.join(" \u00B7 ");
      container.appendChild(meta);
    }

    // Reset button
    var resetBtn = el("button", "drift-prove-reset", "\u21BB Reset");
    container.appendChild(resetBtn);

    container.hidden = false;
    return resetBtn;
  }

  /** Render an error message. */
  function renderError(container, msg) {
    container.innerHTML = "";
    var err = el("div", "drift-prove-error", msg);
    container.appendChild(err);
    container.hidden = false;
  }

  /* ── Controller ──────────────────────────────── */

  /** Process raw text: parse JSON, validate, render. */
  function processInput(text, resultsEl, dropEl, maxFindings) {
    var data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      renderError(resultsEl, "Could not parse JSON. Make sure you drop the drift output file.");
      return;
    }

    var err = validate(data);
    if (err) {
      renderError(resultsEl, err);
      return;
    }

    var resetBtn = renderResults(resultsEl, data, maxFindings);
    dropEl.hidden = true;

    resetBtn.addEventListener("click", function () {
      resultsEl.innerHTML = "";
      resultsEl.hidden = true;
      dropEl.hidden = false;
    });
  }

  /** Wire up drag-and-drop + paste for a drop zone. */
  function initDropZone(dropEl, resultsEl, maxFindings) {
    // Drag & drop
    dropEl.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropEl.classList.add("drag-active");
    });

    dropEl.addEventListener("dragleave", function (e) {
      e.preventDefault();
      dropEl.classList.remove("drag-active");
    });

    dropEl.addEventListener("drop", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropEl.classList.remove("drag-active");

      var files = e.dataTransfer && e.dataTransfer.files;
      if (!files || files.length === 0) return;

      var file = files[0];
      if (file.size > 10 * 1024 * 1024) {
        renderError(resultsEl, "File too large (>10 MB). Use --compact flag for smaller output.");
        return;
      }

      var reader = new FileReader();
      reader.onload = function (ev) {
        processInput(ev.target.result, resultsEl, dropEl, maxFindings);
      };
      reader.readAsText(file);
    });

    // Paste from clipboard button
    var pasteBtn = dropEl.querySelector("[data-prove-paste]");
    if (pasteBtn && navigator.clipboard && navigator.clipboard.readText) {
      pasteBtn.addEventListener("click", function () {
        navigator.clipboard.readText().then(function (text) {
          if (text && text.trim()) {
            processInput(text.trim(), resultsEl, dropEl, maxFindings);
          }
        }).catch(function () {
          renderError(resultsEl, "Could not read clipboard. Try dropping the file instead.");
        });
      });
    } else if (pasteBtn) {
      // Hide paste button if clipboard API unavailable
      pasteBtn.style.display = "none";
    }

    // File input fallback
    var fileInput = dropEl.querySelector("[data-prove-file]");
    if (fileInput) {
      fileInput.addEventListener("change", function () {
        var file = fileInput.files && fileInput.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function (ev) {
          processInput(ev.target.result, resultsEl, dropEl, maxFindings);
        };
        reader.readAsText(file);
      });
    }
  }

  /* ── Initialization ──────────────────────────── */

  function init() {
    // Find all drop zones on the page
    var dropZones = document.querySelectorAll(".drift-prove-drop");
    for (var i = 0; i < dropZones.length; i++) {
      var drop = dropZones[i];
      var maxAttr = drop.getAttribute("data-max-findings");
      var max = maxAttr ? parseInt(maxAttr, 10) : 5;

      // Find the sibling results container
      var target = drop.getAttribute("data-results-target");
      var results = target
        ? document.getElementById(target)
        : drop.parentElement.querySelector(".drift-prove-results");

      if (results) {
        initDropZone(drop, results, max);
      }
    }
  }

  // Run on DOMContentLoaded or immediately if already loaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
