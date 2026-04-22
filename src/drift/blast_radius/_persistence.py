"""Persistence-Schicht für Blast-Reports.

Reports werden nach ``<repo>/blast_reports/<yyyymmdd_hhmmss>_<short_sha>.json``
geschrieben. Das Verzeichnis wird bei Bedarf erzeugt und enthält eine
``README.md`` mit Retention-Hinweisen (Maintainer-Aufgabe, nicht vom Agent).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from drift.blast_radius._change_detector import short_sha
from drift.blast_radius._models import BlastReport

_log = logging.getLogger("drift.blast_radius.persistence")

_REPORTS_DIRNAME = "blast_reports"


def blast_reports_dir(repo_path: Path) -> Path:
    """Liefere den Report-Ordner (ohne ihn zu erzeugen)."""
    return repo_path / _REPORTS_DIRNAME


def _ensure_dir(repo_path: Path) -> Path:
    target = blast_reports_dir(repo_path)
    target.mkdir(parents=True, exist_ok=True)
    acks = target / "acks"
    acks.mkdir(parents=True, exist_ok=True)
    return target


def _report_filename(report: BlastReport) -> str:
    """Stabiler Dateiname: Timestamp + Short-SHA + Suffix."""
    try:
        ts = datetime.fromisoformat(report.generated_at)
    except ValueError:
        ts = datetime.now(UTC)
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    sha = short_sha(report.trigger.head_sha)
    return f"{stamp}_{sha}.json"


def save_blast_report(repo_path: Path, report: BlastReport) -> Path:
    """Serialisiere einen Report als JSON und gib den Zielpfad zurück."""
    target_dir = _ensure_dir(repo_path)
    target = target_dir / _report_filename(report)
    payload = report.model_dump(mode="json")
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _log.debug("Blast-Report geschrieben: %s", target)
    return target


def load_blast_report(path: Path) -> BlastReport:
    """Lade einen zuvor gespeicherten Report. Raises ValueError bei Schema-Fehlern."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"Blast-Report nicht lesbar: {path}: {exc}"
        raise ValueError(msg) from exc
    try:
        return BlastReport.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — Pydantic-Fehler in ValueError kapseln
        msg = f"Blast-Report-Schema ungültig in {path}: {exc}"
        raise ValueError(msg) from exc


def find_report_for_sha(repo_path: Path, head_sha: str) -> Path | None:
    """Finde den jüngsten Report, dessen Dateiname auf ``short_sha(head_sha)`` endet."""
    if not head_sha:
        return None
    suffix = short_sha(head_sha)
    target_dir = blast_reports_dir(repo_path)
    if not target_dir.is_dir():
        return None
    candidates = sorted(target_dir.glob(f"*_{suffix}.json"), reverse=True)
    return candidates[0] if candidates else None


def find_ack_for_sha(repo_path: Path, head_sha: str) -> Path | None:
    """Finde eine Maintainer-Ack-Datei ``blast_reports/acks/<short_sha>.yaml``."""
    if not head_sha:
        return None
    suffix = short_sha(head_sha)
    ack = blast_reports_dir(repo_path) / "acks" / f"{suffix}.yaml"
    return ack if ack.is_file() else None
