"""PR comment templates — reuses the action.yml Drift Report format."""

from __future__ import annotations

COMMENT_MARKER = "## 🏗️ Drift Report"

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

SCORE_THRESHOLDS = [
    (0.8, "critical"),
    (0.6, "orange"),
    (0.4, "yellow"),
    (0.2, "yellowgreen"),
    (0.0, "brightgreen"),
]


def _badge_color(score: float) -> str:
    for threshold, color in SCORE_THRESHOLDS:
        if score >= threshold:
            return color
    return "brightgreen"


def _trend_text(trend: dict | None) -> str:
    if not trend or trend.get("delta") is None:
        return "N/A"
    delta = trend["delta"]
    if delta > 0.005:
        return f"🔴 {delta:+.3f} ▲ degrading"
    if delta < -0.005:
        return f"🟢 {delta:+.3f} ▼ improving"
    return f"⚪ {delta:+.3f} → stable"


def _severity_distribution(findings: list[dict]) -> str:
    from collections import Counter

    counts = Counter(f.get("severity", "info") for f in findings)
    parts = [
        f"{s.upper()}: {counts[s]}" for s in SEVERITY_ORDER if counts.get(s, 0) > 0
    ]
    return " · ".join(parts) if parts else "No findings"


def _top_findings_table(findings: list[dict], limit: int = 3) -> str:
    ranked = sorted(
        findings,
        key=lambda f: f.get("impact", f.get("score", 0)),
        reverse=True,
    )[:limit]
    if not ranked:
        return "| — | No findings | — | — |"
    rows = []
    for f in ranked:
        sig = f.get("signal", "?")
        title = f.get("title", "")[:80]
        loc = f.get("file", "?")
        line = f.get("start_line", "")
        loc_str = f"`{loc}:{line}`" if line else f"`{loc}`"
        fix = (f.get("fix") or "")[:100]
        rows.append(f"| {sig} | {title} | {loc_str} | {fix} |")
    return "\n".join(rows)


def format_pr_comment(result: dict) -> str:
    """Format drift analysis result into a Markdown PR comment.

    Args:
        result: Parsed JSON output from ``drift check --format json``.

    Returns:
        Full Markdown comment body.
    """
    score = result.get("drift_score", 0.0)
    severity = result.get("severity", "unknown").upper()
    findings = result.get("findings", [])
    trend = result.get("trend")

    color = _badge_color(score)
    badge = (
        f"![Drift Score](https://img.shields.io/badge/"
        f"drift%20score-{score:.2f}-{color}?style=flat-square)"
    )

    lines = [
        COMMENT_MARKER,
        "",
        badge,
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Score** | `{score:.2f}` |",
        f"| **Trend** | {_trend_text(trend)} |",
        f"| **Severity** | {severity} |",
        f"| **Findings** | {len(findings)} |",
        f"| **Distribution** | {_severity_distribution(findings)} |",
        "",
    ]

    if findings:
        lines += [
            "### Top Findings",
            "",
            "| Signal | Finding | Location | Fix |",
            "|--------|---------|----------|-----|",
            _top_findings_table(findings),
            "",
        ]

    lines.append(
        '<sub>Posted by <a href="https://github.com/mick-gsk/drift">Drift Bot</a>'
        " · report-only mode — no code was changed</sub>"
    )
    return "\n".join(lines)
