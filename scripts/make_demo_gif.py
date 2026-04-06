"""
Generate a beautiful terminal-recording-style demo GIF for Drift.

Curated hardcoded output — deterministic, no live drift execution required.

Requirements: Pillow
Run from repo root: python scripts/make_demo_gif.py
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Terminal colour palette — Catppuccin Mocha
# ---------------------------------------------------------------------------
BG           = (30, 30, 46)          # #1e1e2e  Base
FG           = (205, 214, 244)       # #cdd6f4  Text
ACCENT_CYAN  = (137, 220, 235)       # #89dceb  Sky
ACCENT_BLUE  = (137, 180, 250)       # #89b4fa  Blue
ACCENT_RED   = (243, 139, 168)       # #f38ba8  Red
ACCENT_YEL   = (249, 226, 175)       # #f9e2af  Yellow
ACCENT_GRN   = (166, 227, 161)       # #a6e3a1  Green
ACCENT_MAV   = (203, 166, 247)       # #cba6f7  Mauve
DIM          = (108, 112, 134)       # #6c7086  Overlay0
BORDER       = (88, 91, 112)         # #585b70  Surface1
SURFACE0     = (49, 50, 68)          # #313244  Surface0  (subtle highlight bg)
CHR_BG       = (24, 24, 37)          # window chrome
WIN_RED      = (235,  80,  80)
WIN_YEL      = (255, 189,  46)
WIN_GRN      = ( 40, 200,  80)

# ---------------------------------------------------------------------------
# Curated demo output — focused single story, shows Drift at its best
# ---------------------------------------------------------------------------
PROMPT = "$ "
TYPING_CMD = "drift analyze --repo ./myproject"

SCAN_FRAMES = [
    "Analyzing 87 Python files",
    "Analyzing 87 Python files.",
    "Analyzing 87 Python files..",
    "Analyzing 87 Python files...",
]

SCORE_BOX = [
    "╭─ drift analyze  myproject/ ─────────────────────────────────────────╮",
    "│  DRIFT SCORE  0.52   Δ -0.031 ↓ improving  │  87 files  │  2.3s   │",
    "╰─────────────────────────────────────────────────────────────────────╯",
]

MODULE_TABLE = [
    "",
    "  Module                     Score   Findings   Top Signal",
    "  ──────────────────────────────────────────────────────",
    "  src/api/routes/             0.71        12    PFS  0.85",
    "  src/services/auth/          0.58         7    AVS  0.72",
    "  src/db/models/              0.41         4    NBV  0.61",
]

FINDING_1 = [
    "",
    "  ◉ HIGH  PFS  0.85   Error handling split 4 ways",
    "           → src/api/routes.py:42",
    "           → Next: consolidate into shared error handler",
]

FINDING_2 = [
    "  ◉ HIGH  AVS  0.72   DB import in API layer",
    "           → src/api/auth.py:18",
    "           → Next: move DB access behind service interface",
]

FINDING_3 = [
    "  ◉  MED  NBV  0.61   6 near-identical utility functions",
    "           → src/utils/helpers.py:33",
    "           → Next: extract shared function, remove duplicates",
]

FOOTER = [
    "",
    "  3 findings  ·  drift fix-plan --repo .  for repair tasks",
]

# ---------------------------------------------------------------------------
# Canvas parameters
# ---------------------------------------------------------------------------
W        = 960
H        = 580
PADDING  = 24
FONT_SZ  = 16
LINE_H   = 23
TITLE_H  = 36

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def _load_font(size: int):
    from PIL import ImageFont  # type: ignore[import-untyped]
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


def _line_colour(line: str) -> tuple:
    """Assign a display colour based on line content."""
    s = line.strip()
    # Score box border
    if s.startswith("╭") or s.startswith("╰"):
        return BORDER
    # Score box content
    if s.startswith("│") and "DRIFT SCORE" in line:
        return ACCENT_CYAN
    # Table separator
    if s.startswith("──") or s.startswith("─ ─"):
        return SURFACE0
    # Column header
    if "Module" in line and ("Score" in line or "Signal" in line):
        return DIM
    # Module rows
    if s.startswith("src/"):
        return FG
    # Scanning progress
    if s.startswith("Analyzing"):
        return ACCENT_BLUE
    # Severity tags
    if "◉ HIGH" in line or "◉  HIGH" in line:
        return ACCENT_RED
    if "◉  MED" in line or "◉ MED" in line:
        return ACCENT_YEL
    # Next-action lines
    if "→ Next:" in line:
        return ACCENT_GRN
    # File location lines
    if "→ src/" in line:
        return DIM
    # Footer
    if "findings" in line and "drift fix-plan" in line:
        return ACCENT_MAV
    # Prompt / command
    if s.startswith(PROMPT.strip()) or s.startswith("drift "):
        return ACCENT_GRN
    return FG


# ---------------------------------------------------------------------------
# Single-frame rendering
# ---------------------------------------------------------------------------

def _make_frame(lines: list[str], title: str = "drift analyze") -> object:
    from PIL import Image, ImageDraw  # type: ignore[import-untyped]

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = _load_font(FONT_SZ)

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
    visible = lines[-max_lines:] if len(lines) > max_lines else lines

    for raw_line in visible:
        line = _strip_ansi(raw_line)
        colour = _line_colour(line)

        # Subtle highlight background behind score-box lines
        stripped = line.strip()
        is_box_line = (
            stripped.startswith("╭")
            or stripped.startswith("╰")
            or (stripped.startswith("│") and "DRIFT SCORE" in line)
        )
        if is_box_line:
            draw.rectangle(
                [PADDING - 6, y - 2, W - PADDING + 6, y + LINE_H - 3],
                fill=SURFACE0,
            )

        draw.text((PADDING, y), line[:108], fill=colour, font=font)
        y += LINE_H
        if y > H - PADDING:
            break

    return img


# ---------------------------------------------------------------------------
# Build animation frames
# ---------------------------------------------------------------------------

def build_frames() -> list:
    """Assemble all animation frames as (PIL.Image, delay_ms) tuples."""
    frames: list = []
    prompt_line = PROMPT + TYPING_CMD

    # ── Act 1: Typing the command ──────────────────────────────────────────
    # Show just the prompt, then type chars in groups of 3
    frames.append((_make_frame([PROMPT + "_"], "drift"), 300))
    for i in range(len(PROMPT), len(prompt_line) + 1, 3):
        frames.append((_make_frame([prompt_line[:i] + "_"], "drift"), 55))
    # Cursor blink on complete command
    for blink in range(4):
        cursor = "_" if blink % 2 == 0 else ""
        frames.append((_make_frame([prompt_line + cursor], "drift"), 220))

    # ── Act 2: Scanning animation ──────────────────────────────────────────
    base: list[str] = [prompt_line, ""]
    for scan_text in SCAN_FRAMES:
        for _ in range(3):
            frames.append((_make_frame(base + [scan_text], "drift"), 110))
    # Brief pause
    frames.append((_make_frame(base + [SCAN_FRAMES[-1]], "drift"), 300))

    # ── Act 3a: Score box ──────────────────────────────────────────────────
    current = base + [""] + SCORE_BOX
    for _ in range(14):
        frames.append((_make_frame(current, "drift analyze"), 130))

    # ── Act 3b: Module table ───────────────────────────────────────────────
    current = current + MODULE_TABLE
    for _ in range(12):
        frames.append((_make_frame(current, "drift analyze"), 120))

    # ── Act 3c: Findings appear individually ──────────────────────────────
    current = current + FINDING_1
    for _ in range(11):
        frames.append((_make_frame(current, "drift analyze"), 120))

    current = current + FINDING_2
    for _ in range(11):
        frames.append((_make_frame(current, "drift analyze"), 120))

    current = current + FINDING_3
    for _ in range(11):
        frames.append((_make_frame(current, "drift analyze"), 120))

    # ── Act 4: Footer + hold ───────────────────────────────────────────────
    current = current + FOOTER
    for _ in range(32):
        frames.append((_make_frame(current, "drift analyze"), 150))

    return frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from PIL import Image  # type: ignore[import-untyped]

    repo_root = Path(__file__).parent.parent
    output    = repo_root / "demos" / "demo.gif"

    print("Building frames …")
    frames = build_frames()
    print(f"  {len(frames)} frames")

    imgs   = [f for f, _ in frames]
    delays = [d for _, d in frames]

    print("Quantising (256 colours) …")

    def _quantise(img):
        return img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=0)

    q0     = _quantise(imgs[0])
    q_rest = [_quantise(im) for im in imgs[1:]]

    print("Saving GIF …")
    q0.save(
        output,
        save_all=True,
        append_images=q_rest,
        optimize=True,
        loop=0,
        duration=delays,
    )
    print(f"Saved → {output}  ({output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
