"""Build the HandoffBlock and render it to Rich terminal or dict."""
from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from ._models import HandoffBlock, SessionData

_PROMPT_NAMES: list[str] = [
    "drift-fix-plan",
    "drift-export-report",
    "drift-auto-fix-loop",
    "drift-feature-guardrails",
]
_SESSION_FILE = ".vscode/drift-session.json"


def build_handoff_block(session: SessionData) -> HandoffBlock:
    """Construct a :class:`HandoffBlock` from a :class:`SessionData`."""
    return HandoffBlock(
        drift_score=session.drift_score,
        grade=session.grade,
        analyzed_at=session.analyzed_at,
        top_findings=list(session.top_findings),
        prompts=_PROMPT_NAMES,
        session_file=_SESSION_FILE,
        findings_total=session.findings_total,
    )


def render_handoff_rich(
    block: HandoffBlock,
    console: Console,
    *,
    setup_required: bool = False,
) -> None:
    """Print the drift-kit panel to *console*.

    If *setup_required* is ``True``, an additional hint is printed below
    the panel explaining how to enable the slash commands in VS Code.
    """
    table = Table(
        "Severity",
        "Signal",
        "File",
        "Reason",
        show_header=True,
        header_style="bold",
        box=None,
        expand=True,
    )
    for f in block.top_findings:
        severity_color = "red" if f.severity in ("critical", "high") else "yellow"
        reason = f.reason
        if len(reason) > 80:
            reason = reason[:79] + "\u2026"
        table.add_row(
            f"[{severity_color}]{escape(f.severity)}[/]",
            escape(f.signal_type),
            escape(f.file_path),
            escape(reason),
        )

    prompt_line = "  ".join(f"/{p}" for p in block.prompts)
    body = table if block.top_findings else "[dim]No findings.[/dim]"
    console.print(
        Panel(
            body,
            title=(
                f"[bold]drift-kit[/bold]"
                f"  score: {block.drift_score:.3f}"
                f"  grade: {escape(block.grade)}"
                f"  findings: {block.findings_total}"
            ),
            subtitle=f"[cyan]{escape(prompt_line)}[/cyan]",
            expand=False,
        )
    )
    if setup_required:
        console.print(
            "[dim]Tip: to enable the slash commands in VS Code Copilot Chat, add "
            '"chat.promptFilesLocations": [".github/prompts/"] '
            "to .vscode/settings.json[/dim]"
        )


def handoff_to_dict(block: HandoffBlock) -> dict:
    """Serialize *block* to a plain dict suitable for JSON embedding."""
    return block.model_dump(mode="json")
