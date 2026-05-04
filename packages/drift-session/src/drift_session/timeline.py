"""Root-cause timeline analysis — identifies *when* and *why* drift began.

Analyzes git history per module to find inflection points where drift
scores started increasing, and correlates them with AI-attributed commits.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

from drift.models import CommitInfo, FileHistory, Finding


@dataclass
class DriftEvent:
    """A single event on the drift timeline."""

    date: datetime.date
    description: str
    commit_hash: str | None = None
    author: str | None = None
    is_ai: bool = False
    ai_confidence: float = 0.0
    files_affected: list[str] = field(default_factory=list)


@dataclass
class ModuleTimeline:
    """Drift timeline for a single module."""

    module_path: str
    clean_until: datetime.date | None = None
    drift_started: datetime.date | None = None
    trigger_commits: list[DriftEvent] = field(default_factory=list)
    ai_burst: AiBurst | None = None
    current_score: float = 0.0
    finding_count: int = 0


@dataclass
class AiBurst:
    """A burst of AI-attributed commits in a short time window."""

    start_date: datetime.date
    end_date: datetime.date
    commit_count: int
    ai_commit_count: int
    files_affected: list[str] = field(default_factory=list)


@dataclass
class RepoTimeline:
    """Complete timeline analysis for a repository."""

    module_timelines: list[ModuleTimeline] = field(default_factory=list)
    global_events: list[DriftEvent] = field(default_factory=list)
    ai_burst_periods: list[AiBurst] = field(default_factory=list)


def _group_commits_by_module(
    commits: list[CommitInfo],
) -> dict[str, list[CommitInfo]]:
    """Group commits by the module directory of each changed file."""
    by_module: dict[str, list[CommitInfo]] = {}
    for commit in commits:
        modules_in_commit: set[str] = set()
        for fpath in commit.files_changed:
            parts = Path(fpath).parts
            module = parts[0] if len(parts) > 1 else "."
            modules_in_commit.add(module)
        for module in modules_in_commit:
            by_module.setdefault(module, []).append(commit)
    return by_module


def _detect_ai_bursts(
    commits: list[CommitInfo],
    window_days: int = 3,
    min_commits: int = 3,
) -> list[AiBurst]:
    """Find periods with concentrated AI-attributed commits."""
    ai_commits = sorted(
        [c for c in commits if c.is_ai_attributed],
        key=lambda c: c.timestamp,
    )
    if len(ai_commits) < min_commits:
        return []

    bursts: list[AiBurst] = []
    window = datetime.timedelta(days=window_days)
    i = 0

    while i < len(ai_commits):
        start = ai_commits[i]
        group = [start]
        j = i + 1
        while j < len(ai_commits) and (ai_commits[j].timestamp - start.timestamp) <= window:
            group.append(ai_commits[j])
            j += 1

        if len(group) >= min_commits:
            all_files: set[str] = set()
            for c in group:
                all_files.update(c.files_changed)
            # Count total commits (including non-AI) in the same window
            start_dt = group[0].timestamp
            end_dt = group[-1].timestamp
            total_in_window = sum(1 for c in commits if start_dt <= c.timestamp <= end_dt)
            bursts.append(
                AiBurst(
                    start_date=start_dt.date(),
                    end_date=end_dt.date(),
                    commit_count=total_in_window,
                    ai_commit_count=len(group),
                    files_affected=sorted(all_files),
                )
            )
            i = j
        else:
            i += 1

    return bursts


def _find_drift_onset(
    module_commits: list[CommitInfo],
    file_histories: dict[str, FileHistory],
    module_path: str,
) -> tuple[datetime.date | None, datetime.date | None, list[DriftEvent]]:
    """Find when a module was clean and when drift started.

    Returns (clean_until, drift_started, trigger_commits).
    """
    if not module_commits:
        return None, None, []

    sorted_commits = sorted(module_commits, key=lambda c: c.timestamp)

    # Find module files
    module_files = {
        fp for fp in file_histories if fp.startswith(module_path + "/") or module_path == "."
    }

    # Track cumulative "problem indicators" over time
    # A commit is a "drift trigger" if it's AI-attributed and touches many files,
    # or introduces defect-correlated changes
    trigger_commits: list[DriftEvent] = []
    clean_until: datetime.date | None = None
    drift_started: datetime.date | None = None

    # Walk commits chronologically, look for the first problematic cluster
    problem_streak = 0
    last_clean_date: datetime.date | None = None

    for commit in sorted_commits:
        if module_files:
            commit_files = set(commit.files_changed) & module_files
        else:
            commit_files = set(commit.files_changed)
        if not commit_files:
            continue

        is_problematic = False
        reasons: list[str] = []

        if commit.is_ai_attributed:
            is_problematic = True
            reasons.append(f"AI-attributed (confidence: {commit.ai_confidence:.0%})")

        # Check if it's a defect-fix
        msg_lower = commit.message.lower()
        if any(w in msg_lower for w in ("fix", "bug", "revert", "hotfix", "broken")):
            is_problematic = True
            reasons.append("defect-correlated commit")

        # Large change touching many module files
        if len(commit_files) >= 5:
            reasons.append(f"touched {len(commit_files)} files in module")

        if is_problematic:
            problem_streak += 1
            if problem_streak >= 2 and drift_started is None:
                drift_started = commit.timestamp.date()
                clean_until = last_clean_date

            trigger_commits.append(
                DriftEvent(
                    date=commit.timestamp.date(),
                    description="; ".join(reasons),
                    commit_hash=commit.hash,
                    author=commit.author,
                    is_ai=commit.is_ai_attributed,
                    ai_confidence=commit.ai_confidence,
                    files_affected=sorted(commit_files),
                )
            )
        else:
            if drift_started is None:
                problem_streak = 0
                last_clean_date = commit.timestamp.date()

    return clean_until, drift_started, trigger_commits


def build_timeline(
    commits: list[CommitInfo],
    file_histories: dict[str, FileHistory],
    findings: list[Finding],
    module_scores: dict[str, float],
) -> RepoTimeline:
    """Build a complete drift timeline for the repository.

    Args:
        commits: All parsed commits from git history.
        file_histories: Per-file history statistics.
        findings: All findings from the analysis.
        module_scores: Module path → drift score mapping.
    """
    by_module = _group_commits_by_module(commits)

    # Global AI burst detection
    ai_bursts = _detect_ai_bursts(commits)

    # Per-module timelines (only for modules with findings)
    module_finding_count: dict[str, int] = {}
    for f in findings:
        if f.file_path:
            parts = f.file_path.parts
            module = parts[0] if len(parts) > 1 else "."
            module_finding_count[module] = module_finding_count.get(module, 0) + 1

    module_timelines: list[ModuleTimeline] = []
    for module_path in sorted(
        module_finding_count,
        key=lambda m: module_finding_count[m],
        reverse=True,
    ):
        module_commits = by_module.get(module_path, [])
        clean_until, drift_started, triggers = _find_drift_onset(
            module_commits,
            file_histories,
            module_path,
        )

        # Find AI burst overlapping this module
        module_burst = None
        for burst in ai_bursts:
            burst_files_in_module = [
                f
                for f in burst.files_affected
                if f.startswith(module_path + "/") or module_path == "."
            ]
            if burst_files_in_module:
                module_burst = burst
                break

        module_timelines.append(
            ModuleTimeline(
                module_path=module_path,
                clean_until=clean_until,
                drift_started=drift_started,
                trigger_commits=triggers,
                ai_burst=module_burst,
                current_score=module_scores.get(module_path, 0.0),
                finding_count=module_finding_count[module_path],
            )
        )

    # Global events: significant commits (defect fixes, AI bursts, large changes)
    global_events: list[DriftEvent] = []
    for commit in sorted(commits, key=lambda c: c.timestamp):
        if commit.is_ai_attributed and commit.ai_confidence >= 0.9:
            global_events.append(
                DriftEvent(
                    date=commit.timestamp.date(),
                    description=(
                        f"High-confidence AI commit: {commit.message.split(chr(10))[0][:60]}"
                    ),
                    commit_hash=commit.hash,
                    author=commit.author,
                    is_ai=True,
                    ai_confidence=commit.ai_confidence,
                    files_affected=commit.files_changed,
                )
            )

    return RepoTimeline(
        module_timelines=module_timelines,
        global_events=global_events,
        ai_burst_periods=ai_bursts,
    )
