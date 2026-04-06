"""
Generate four terminal-recording-style demo GIFs for Drift.

Curated hardcoded output — deterministic, no live drift execution required.

Requirements: Pillow
Run from repo root:  python scripts/make_demo_gifs.py

Generates:
  demos/onboarding.gif      — drift explain PFS  |  patterns  |  init --dry-run
  demos/agent-workflow.gif  — drift scan (JSON)  |  fix-plan (JSON)
  demos/trend.gif           — drift trend        |  score history
  demos/ci-gate.gif         — drift analyze      |  check --fail-on high  |  SARIF
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Terminal colour palette — Catppuccin Mocha
# ---------------------------------------------------------------------------
BG         = (30, 30, 46)
FG         = (205, 214, 244)
CYAN       = (137, 220, 235)
BLUE       = (137, 180, 250)
RED        = (243, 139, 168)
YELLOW     = (249, 226, 175)
GREEN      = (166, 227, 161)
MAUVE      = (203, 166, 247)
PINK       = (245, 194, 231)
DIM        = (108, 112, 134)
BORDER     = (88, 91, 112)
SURFACE0   = (49, 50, 68)
CHR_BG     = (24, 24, 37)
WIN_RED    = (235, 80, 80)
WIN_YEL    = (255, 189, 46)
WIN_GRN    = (40, 200, 80)

# ---------------------------------------------------------------------------
# Canvas parameters
# ---------------------------------------------------------------------------
W        = 960
H        = 600
PADDING  = 24
FONT_SZ  = 15
LINE_H   = 22
TITLE_H  = 36

PROMPT = "$ "


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def _load_font(size: int):
    from PIL import ImageFont
    candidates = [
        "C:/Windows/Fonts/cascadiacode.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/courbd.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


_FONT_CACHE: dict = {}


def _font(size: int = FONT_SZ):
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = _load_font(size)
    return _FONT_CACHE[size]


def _colourize(line: str, schema: str) -> tuple:
    """Return display colour based on content and the active schema."""
    s = line.strip()

    # Universal rules
    if s.startswith(PROMPT.strip()) or s.startswith("$ drift ") or s.startswith("drift "):
        return GREEN
    if s.startswith("#"):
        return DIM

    if schema == "explain":
        if "╭" in s or "╰" in s or "├" in s:
            return BORDER
        if "│" in s:
            if "Pattern Fragmentation" in line or "PFS" in line:
                return CYAN
            if "What it detects" in line or "How to fix" in line or "Example" in line:
                return MAUVE
            return FG
        if s.startswith("─") or s == "":
            return DIM

    elif schema == "patterns":
        if "╭" in s or "╰" in s or "├" in s or "─" in s:
            return BORDER
        if "│" in s:
            if "File" in line and "Function" in line:
                return DIM
            if "services/" in line or "utils/" in line or "api/" in line:
                return BLUE
            if "error_handling" in line or "Pattern:" in line:
                return YELLOW
            return FG

    elif schema == "init":
        if "Dry run" in line:
            return CYAN
        if "create" in s:
            return GREEN
        if "drift.yaml" in line:
            return BLUE
        if "new," in line or "overwrite" in line:
            return DIM

    elif schema == "scan":
        if '"type": "progress"' in line:
            return DIM
        if '"accept_change": false' in line:
            return RED
        if '"accept_change": true' in line:
            return GREEN
        if '"blocking_reasons"' in line:
            return RED
        if '"drift_score"' in line:
            return CYAN
        if '"finding_count"' in line:
            return YELLOW
        if '"severity"' in line:
            if '"high"' in line:
                return RED
            if '"medium"' in line:
                return YELLOW
        if '"next_step"' in line:
            return GREEN
        if '"signal_abbrev"' in line:
            return MAUVE
        if line.strip().startswith('"') and '":' in line:
            return BLUE
        if line.strip() in ("{", "}", "[", "]", "},", "],"):
            return BORDER

    elif schema == "fixplan":
        if '"title"' in line:
            return CYAN
        if '"priority"' in line:
            if '"high"' in line:
                return RED
            if '"medium"' in line:
                return YELLOW
        if '"automation_fit"' in line or '"automation_fitness"' in line:
            if '"high"' in line:
                return GREEN
        if '"file"' in line:
            return BLUE
        if '"description"' in line:
            return FG
        if line.strip() in ("{", "}", "[", "]", "},", "],", '"tasks": ['):
            return BORDER
        if '"accept_change"' in line:
            if "false" in line:
                return RED
            return GREEN

    elif schema == "trend":
        if "trend" in s.lower() and ("Drift" in line or "Score" in line):
            return CYAN
        if "Score History" in line:
            return MAUVE
        if "╭" in s or "╰" in s or ("─" in s and "│" not in s):
            return BORDER
        if "│" in s:
            if "Timestamp" in line or "Score" in line and "Δ" in line:
                return DIM
            if "202" in line:
                parts = [p.strip() for p in line.split("│") if p.strip()]
                if any("-0." in p for p in parts):
                    return GREEN
                if any("+0." in p for p in parts):
                    return RED
                return FG
        if "Overall trend" in line:
            if "decreasing" in line:
                return GREEN
            if "increasing" in line:
                return RED
            return CYAN
        if "Current drift score" in line:
            return CYAN
        if "AI-attributed" in line:
            return MAUVE
        if "■" in line or "□" in line or "▪" in line:
            return BLUE

    elif schema == "analyze":
        if "DRIFT SCORE" in line:
            return CYAN
        if "╭" in s or "╰" in s:
            return BORDER
        if "│" in s and "DRIFT SCORE" not in line:
            return DIM
        if "Module" in line and "Score" in line:
            return DIM
        if "utils/" in line or "services/" in line or "api/" in line or "db/" in line:
            return FG
        if "■" in line or "□" in line:
            return BLUE
        if "Findings" in line and "─" not in line:
            return MAUVE
        if "✖" in line or "HIGH" in line:
            return RED
        if "dead_code" in line or "pattern_frag" in line:
            return YELLOW
        if "→" in line and "Next" in line:
            return GREEN
        if "→" in line and ".py:" in line:
            return DIM
        if "Trend:" in line:
            return CYAN

    elif schema == "check":
        if "EXIT" in line or "exit code" in line.lower():
            if "1" in line or "FAIL" in line or "BLOCK" in line:
                return RED
            return GREEN
        if "HIGH" in line and ("finding" in line or "block" in line):
            return RED
        if "PASS" in line or "no findings" in line.lower():
            return GREEN
        if "--fail-on" in line:
            return YELLOW
        if "sarif" in line.lower() or ".sarif" in line:
            return CYAN
        if "check" in s and "drift" in s:
            return GREEN
        if "→" in line:
            return MAUVE

    return FG


def _make_frame(
    lines: list[str],
    title: str,
    schema: str = "generic",
    cursor_line: str | None = None,
) -> object:
    from PIL import Image, ImageDraw

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = _font()

    # ── Window chrome ──────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, TITLE_H], fill=CHR_BG)
    for i, col in enumerate([WIN_RED, WIN_YEL, WIN_GRN]):
        cx = 18 + i * 22
        cy = TITLE_H // 2
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=col)
    tw = draw.textlength(title, font=font)
    draw.text(((W - tw) / 2, (TITLE_H - FONT_SZ) / 2), title, fill=DIM, font=font)

    # ── Terminal body ──────────────────────────────────────────────────────
    y = TITLE_H + PADDING
    max_lines = (H - TITLE_H - PADDING * 2) // LINE_H
    render_lines = list(lines)
    if cursor_line is not None:
        render_lines = render_lines + [cursor_line]
    visible = render_lines[-max_lines:] if len(render_lines) > max_lines else render_lines

    for raw_line in visible:
        line = _strip_ansi(raw_line)
        colour = _colourize(line, schema)

        # Score box accent
        is_accent = "DRIFT SCORE" in line and "│" in line
        if is_accent:
            draw.rectangle(
                [PADDING - 6, y - 2, W - PADDING + 6, y + LINE_H - 3],
                fill=SURFACE0,
            )
        draw.text((PADDING, y), line[:112], fill=colour, font=font)
        y += LINE_H
        if y > H - PADDING:
            break

    return img


# ---------------------------------------------------------------------------
# Typing animation helper
# ---------------------------------------------------------------------------

def _typing_frames(
    cmd: str,
    base_lines: list[str],
    title: str,
    schema: str,
    step: int = 3,
    per_char_ms: int = 55,
    blink_count: int = 3,
    hold_ms: int = 300,
) -> list:
    frames = []
    prompt_line = PROMPT + cmd
    # Initial prompt
    frames.append((_make_frame(base_lines, title, schema, PROMPT + "_"), hold_ms))
    for i in range(len(PROMPT), len(prompt_line) + 1, step):
        frames.append((_make_frame(base_lines, title, schema, prompt_line[:i] + "_"), per_char_ms))
    for blink in range(blink_count):
        cursor = "_" if blink % 2 == 0 else ""
        frames.append((_make_frame(base_lines, title, schema, prompt_line + cursor), 220))
    return frames


# ===========================================================================
# GIF 1: onboarding.gif
# ===========================================================================

EXPLAIN_OUTPUT = [
    "╭────────────────────────── Signal: PFS ──────────────────────────╮",
    "│  Pattern Fragmentation Score  (PFS)                             │",
    "│  Default weight: 0.16                                           │",
    "│                                                                 │",
    "│  What it detects                                                │",
    "│  Copy-paste-modify patterns from multi-session AI generation.   │",
    "│  E.g. three different error-handling strategies in one module:  │",
    "│  custom exceptions, return codes, bare try/except logging.      │",
    "│                                                                 │",
    "│  Example                                                        │",
    "│    # Variant A ─ custom exception                               │",
    "│    raise ValidationError(msg)                                   │",
    "│    # Variant B ─ return code                                    │",
    "│    return None, error_msg                                       │",
    "│    # Variant C ─ bare except                                    │",
    "│    try: ... except: log(e)                                      │",
    "│                                                                 │",
    "│  How to fix                                                     │",
    "│  Consolidate to one canonical pattern per category per module.  │",
    "╰─────────────────────────────────────────────────────────────────╯",
]

PATTERNS_OUTPUT = [
    "  Pattern: error_handling  (6 instances)",
    "  ╭──────────────────────────────┬──────────────────────────┬───────╮",
    "  │ File                         │ Function                 │ Lines │",
    "  ├──────────────────────────────┼──────────────────────────┼───────┤",
    "  │ services/email_service.py    │ send_welcome_email       │  9-14 │",
    "  │ services/email_service.py    │ send_order_confirmation  │ 18-22 │",
    "  │ services/order_service.py    │ place_order              │ 13-21 │",
    "  │ services/order_service.py    │ cancel_order             │ 27-32 │",
    "  │ services/user_service.py     │ create_user              │  9-17 │",
    "  │ services/user_service.py     │ delete_user              │ 23-28 │",
    "  ╰──────────────────────────────┴──────────────────────────┴───────╯",
]

INIT_OUTPUT = [
    "  Dry run — profile default: Balanced defaults for Python/TS projects.",
    "",
    "    create  drift.yaml  (1214 bytes)",
    "",
    "  1 new, 0 would overwrite",
]


def _build_onboarding() -> list:
    frames = []

    # ── Scene 1: drift explain PFS ────────────────────────────────────────
    title = "drift explain"
    frames += _typing_frames("drift explain PFS", [], title, "explain", hold_ms=400)
    base = [PROMPT + "drift explain PFS", ""]
    # Reveal explain output line by line
    for i in range(1, len(EXPLAIN_OUTPUT) + 1):
        hold = 60 if i < len(EXPLAIN_OUTPUT) else 800
        frames.append((_make_frame(base + EXPLAIN_OUTPUT[:i], title, "explain"), hold))
    # Hold final explain output
    full_explain = base + EXPLAIN_OUTPUT
    for _ in range(20):
        frames.append((_make_frame(full_explain, title, "explain"), 120))

    # ── Scene 2: drift patterns ───────────────────────────────────────────
    title = "drift patterns"
    frames += _typing_frames(
        "drift patterns --repo myproject/",
        full_explain,
        title,
        "patterns",
        hold_ms=300,
    )
    base2 = full_explain + [PROMPT + "drift patterns --repo myproject/", ""]
    for i in range(1, len(PATTERNS_OUTPUT) + 1):
        hold = 80 if i < len(PATTERNS_OUTPUT) else 900
        frames.append((_make_frame(base2 + PATTERNS_OUTPUT[:i], title, "patterns"), hold))
    full_patterns = base2 + PATTERNS_OUTPUT
    for _ in range(20):
        frames.append((_make_frame(full_patterns, title, "patterns"), 130))

    # ── Scene 3: drift init --dry-run ─────────────────────────────────────
    title = "drift init"
    frames += _typing_frames(
        "drift init --profile default --dry-run",
        full_patterns,
        title,
        "init",
        hold_ms=300,
    )
    base3 = full_patterns + [PROMPT + "drift init --profile default --dry-run", ""]
    for i in range(1, len(INIT_OUTPUT) + 1):
        hold = 100 if i < len(INIT_OUTPUT) else 1200
        frames.append((_make_frame(base3 + INIT_OUTPUT[:i], title, "init"), hold))
    full_init = base3 + INIT_OUTPUT
    for _ in range(32):
        frames.append((_make_frame(full_init, title, "init"), 150))

    return frames


# ===========================================================================
# GIF 2: agent-workflow.gif
# ===========================================================================

SCAN_PROGRESS = [
    '{"type": "progress", "step": 0,  "signal": "Discovering files",           "elapsed_s": 0.0}',
    '{"type": "progress", "step": 5,  "signal": "Parsing files",               "elapsed_s": 0.1}',
    '{"type": "progress", "step": 10, "signal": "Parsing files",               "elapsed_s": 0.2}',
    '{"type": "progress", "step": 0,  "signal": "Analyzing git history",        "elapsed_s": 1.1}',
    '{"type": "progress", "step": 1,  "signal": "Signal: Broad Exception …",  "elapsed_s": 1.1}',
    '{"type": "progress", "step": 2,  "signal": "Signal: Explainability Def…", "elapsed_s": 1.2}',
    '{"type": "progress", "step": 3,  "signal": "Signal: Pattern Fragmnttn",  "elapsed_s": 1.2}',
]

SCAN_RESULT = [
    "{",
    '  "accept_change": false,',
    '  "blocking_reasons": ["existing_high_or_critical_findings"],',
    '  "drift_score": 0.39,',
    '  "finding_count": 3,',
    '  "findings": [',
    "    {",
    '      "signal_abbrev": "PFS",',
    '      "severity": "high",',
    '      "score": 0.71,',
    '      "file": "services/",',
    '      "next_step": "Consolidate 3 error-handling variants in services/"',
    "    },",
    "    {",
    '      "signal_abbrev": "BEM",',
    '      "severity": "medium",',
    '      "score": 0.58,',
    '      "file": "utils/validators.py",',
    '      "next_step": "Replace bare except with specific exception types"',
    "    },",
    "    {",
    '      "signal_abbrev": "EDS",',
    '      "severity": "medium",',
    '      "score": 0.44,',
    '      "file": "api/routes.py",',
    '      "next_step": "Add docstrings to 4 public functions"',
    "    }",
    "  ]",
    "}",
]

FIXPLAN_RESULT = [
    "{",
    '  "accept_change": false,',
    '  "tasks": [',
    "    {",
    '      "title":           "Consolidate error-handling in services/",',
    '      "file":            "services/order_service.py",',
    '      "priority":        "high",',
    '      "automation_fit":  "high",',
    '      "description":     "3 variants → choose ValidationError, remove rest"',
    "    },",
    "    {",
    '      "title":           "Replace bare except in utils/validators.py",',
    '      "file":            "utils/validators.py",',
    '      "priority":        "medium",',
    '      "automation_fit":  "high",',
    '      "description":     "except: → except (ValueError, TypeError):"',
    "    },",
    "    {",
    '      "title":           "Add docstrings to api/routes.py public fns",',
    '      "file":            "api/routes.py",',
    '      "priority":        "medium",',
    '      "automation_fit":  "medium",',
    '      "description":     "4 missing docstrings on exported endpoints"',
    "    }",
    "  ]",
    "}",
]


def _build_agent_workflow() -> list:
    frames = []
    title = "drift  agent workflow"

    # ── Scene 1: drift scan ──────────────────────────────────────────────
    frames += _typing_frames(
        "drift scan --select PFS,BEM,EDS --repo myproject/",
        [],
        title,
        "scan",
        hold_ms=350,
    )
    base = [PROMPT + "drift scan --select PFS,BEM,EDS --repo myproject/", ""]
    # Show progress lines animating
    for i in range(1, len(SCAN_PROGRESS) + 1):
        frames.append((_make_frame(base + SCAN_PROGRESS[:i], title, "scan"), 80))
    progress_done = base + SCAN_PROGRESS

    # Show JSON result
    for i in range(1, len(SCAN_RESULT) + 1):
        hold = 45 if i < len(SCAN_RESULT) else 900
        frames.append((_make_frame(progress_done + SCAN_RESULT[:i], title, "scan"), hold))
    full_scan = progress_done + SCAN_RESULT
    for _ in range(16):
        frames.append((_make_frame(full_scan, title, "scan"), 120))

    # ── Scene 2: drift fix-plan ───────────────────────────────────────────
    title = "drift  fix-plan"
    frames += _typing_frames(
        "drift fix-plan --max-tasks 3 --repo myproject/",
        full_scan,
        title,
        "fixplan",
        hold_ms=300,
    )
    base2 = full_scan + [PROMPT + "drift fix-plan --max-tasks 3 --repo myproject/", ""]
    for i in range(1, len(FIXPLAN_RESULT) + 1):
        hold = 45 if i < len(FIXPLAN_RESULT) else 1000
        frames.append((_make_frame(base2 + FIXPLAN_RESULT[:i], title, "fixplan"), hold))
    full_fp = base2 + FIXPLAN_RESULT
    for _ in range(36):
        frames.append((_make_frame(full_fp, title, "fixplan"), 150))

    return frames


# ===========================================================================
# GIF 3: trend.gif
# ===========================================================================

TREND_TABLE = [
    "  Drift — trend  (30-day history)",
    "",
    "                   Score History (last 30)",
    "  ╭──────────────────────┬───────┬──────────┬──────────╮",
    "  │ Timestamp            │ Score │       Δ  │ Findings │",
    "  ├──────────────────────┼───────┼──────────┼──────────┤",
    "  │ 2026-03-07 09:00     │ 0.621 │        — │      512 │",
    "  │ 2026-03-14 09:00     │ 0.588 │  -0.033  │      487 │",
    "  │ 2026-03-21 09:00     │ 0.541 │  -0.047  │      441 │",
    "  │ 2026-03-28 09:00     │ 0.502 │  -0.039  │      405 │",
    "  │ 2026-04-04 09:00     │ 0.479 │  -0.023  │      393 │",
    "  ╰──────────────────────┴───────┴──────────┴──────────╯",
    "",
    "  Overall trend (5 snapshots): ↓ decreasing  (-0.142)",
    "  Current drift score:  0.479",
    "  Files analyzed:         129",
    "  Total findings:         393",
    "  AI-attributed commits:   76%",
]

TREND_CHART = [
    "",
    "  Drift Score Trend",
    "",
    "  0.62 │■",
    "  0.59 │  ■",
    "  0.54 │     ■",
    "  0.50 │        ■",
    "  0.48 │           ■",
    "       └────────────────────",
    "         Mar 7  14  21  28  Apr 4",
]


def _build_trend() -> list:
    frames = []
    title = "drift trend"

    frames += _typing_frames(
        "drift trend --repo . --last 30",
        [],
        title,
        "trend",
        hold_ms=350,
    )
    base = [PROMPT + "drift trend --repo . --last 30", ""]
    for i in range(1, len(TREND_TABLE) + 1):
        hold = 70 if i < len(TREND_TABLE) else 600
        frames.append((_make_frame(base + TREND_TABLE[:i], title, "trend"), hold))
    full_table = base + TREND_TABLE
    for _ in range(12):
        frames.append((_make_frame(full_table, title, "trend"), 120))

    # Reveal chart
    for i in range(1, len(TREND_CHART) + 1):
        hold = 80 if i < len(TREND_CHART) else 900
        frames.append((_make_frame(full_table + TREND_CHART[:i], title, "trend"), hold))
    full_trend = full_table + TREND_CHART
    for _ in range(36):
        frames.append((_make_frame(full_trend, title, "trend"), 150))

    return frames


# ===========================================================================
# GIF 4: ci-gate.gif
# ===========================================================================

ANALYZE_HEADER = [
    "  ╭────────────── drift analyze  myproject/ ───────────────────────╮",
    "  │  DRIFT SCORE  0.39  Δ +0.388 ↑ degrading  │ 10 files │ 18 fns │",
    "  ╰────────────────────────────────────────────────────────────────╯",
    "",
    "  Module Drift Ranking",
    "  ╭──────────────────────────────┬───────┬─────────────────╮",
    "  │ Module                       │ Score │ Findings        │",
    "  ├──────────────────────────────┼───────┼─────────────────┤",
    "  │ utils/                       │  0.43 │ 2               │",
    "  │ services/                    │  0.21 │ 1               │",
    "  │ api/                         │  0.00 │ 0               │",
    "  ╰──────────────────────────────┴───────┴─────────────────╯",
    "",
    "  Findings",
    "  ✖ HIGH  dead_code_accumulation  0.90  5 unused exports in validators.py",
    "    →  utils/validators.py:6  |  Next: remove or export dead functions",
    "  ✖ HIGH  pattern_fragmentation   0.71  error-handling split 3 ways",
    "    →  services/                  |  Next: consolidate to ValidationError",
]

CHECK_FAIL_OUTPUT = [
    "",
    "  $ drift check --fail-on high --repo myproject/",
    "",
    "  Checking for findings at severity: high",
    "  2 HIGH findings found — threshold exceeded",
    "",
    "  EXIT 1  ✖  Pipeline blocked by HIGH drift findings",
    "",
]

CHECK_SARIF_OUTPUT = [
    "  $ drift check --fail-on none --format sarif -o findings.sarif",
    "",
    "  2 findings exported → findings.sarif",
    "  Upload to GitHub Code Scanning or any SARIF-compatible tool.",
    "",
    "  EXIT 0  ✔  SARIF export complete",
]


def _build_ci_gate() -> list:
    frames = []
    title = "drift ci gate"

    # ── Scene 1: drift analyze ────────────────────────────────────────────
    frames += _typing_frames(
        "drift analyze --repo myproject/",
        [],
        title,
        "analyze",
        hold_ms=350,
    )
    base = [PROMPT + "drift analyze --repo myproject/", ""]
    for i in range(1, len(ANALYZE_HEADER) + 1):
        hold = 60 if i < len(ANALYZE_HEADER) else 800
        frames.append((_make_frame(base + ANALYZE_HEADER[:i], title, "analyze"), hold))
    full_analyze = base + ANALYZE_HEADER
    for _ in range(16):
        frames.append((_make_frame(full_analyze, title, "analyze"), 120))

    # ── Scene 2: drift check --fail-on high ───────────────────────────────
    title = "drift check"
    for i in range(1, len(CHECK_FAIL_OUTPUT) + 1):
        hold = 70 if i < len(CHECK_FAIL_OUTPUT) else 800
        frames.append((_make_frame(full_analyze + CHECK_FAIL_OUTPUT[:i], title, "check"), hold))
    full_check = full_analyze + CHECK_FAIL_OUTPUT
    for _ in range(14):
        frames.append((_make_frame(full_check, title, "check"), 120))

    # ── Scene 3: SARIF export ─────────────────────────────────────────────
    title = "drift check  sarif"
    for i in range(1, len(CHECK_SARIF_OUTPUT) + 1):
        hold = 80 if i < len(CHECK_SARIF_OUTPUT) else 1000
        frames.append((_make_frame(full_check + CHECK_SARIF_OUTPUT[:i], title, "check"), hold))
    full_sarif = full_check + CHECK_SARIF_OUTPUT
    for _ in range(36):
        frames.append((_make_frame(full_sarif, title, "check"), 150))

    return frames


# ===========================================================================
# GIF saver
# ===========================================================================

def _save_gif(frames: list, output: Path) -> None:
    from PIL import Image

    print(f"  {len(frames)} frames → quantising …")

    def _q(img):
        return img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=0)

    imgs   = [f for f, _ in frames]
    delays = [d for _, d in frames]
    q0     = _q(imgs[0])
    q_rest = [_q(im) for im in imgs[1:]]

    print(f"  Saving {output} …")
    q0.save(
        output,
        save_all=True,
        append_images=q_rest,
        optimize=True,
        loop=0,
        duration=delays,
    )
    print(f"  Saved  {output}  ({output.stat().st_size // 1024} KB)")


# ===========================================================================
# Main
# ===========================================================================

GIFS = [
    ("onboarding.gif",     _build_onboarding,     "drift explain / patterns / init"),
    ("agent-workflow.gif", _build_agent_workflow,  "drift scan / fix-plan"),
    ("trend.gif",          _build_trend,           "drift trend"),
    ("ci-gate.gif",        _build_ci_gate,         "drift analyze / check / sarif"),
]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate Drift demo GIFs")
    parser.add_argument(
        "--only",
        choices=[g[0].replace(".gif", "") for g in GIFS],
        help="Render only one GIF by name (without .gif extension)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    demos_dir = repo_root / "demos"
    demos_dir.mkdir(exist_ok=True)

    for name, builder, description in GIFS:
        if args.only and args.only != name.replace(".gif", ""):
            continue
        print(f"\nBuilding {name}  ({description})")
        frames = builder()
        _save_gif(frames, demos_dir / name)

    print("\nDone.")


if __name__ == "__main__":
    main()
