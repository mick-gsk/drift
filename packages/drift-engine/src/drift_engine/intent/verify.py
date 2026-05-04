"""Structural feature verification for build artifacts against a captured intent."""
from __future__ import annotations

import contextlib
import re
from pathlib import Path

from drift_engine.intent._models import CapturedIntent, VerifyResult

_SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".md",
    ".txt", ".json", ".yaml", ".yml", ".toml", ".svelte", ".vue",
}
_MAX_FILE_SIZE = 200_000


def _scan_artifact_content(artifact_path: Path) -> str:
    if not artifact_path.exists():
        return ""
    parts: list[str] = []
    if artifact_path.is_file():
        with contextlib.suppress(OSError):
            parts.append(artifact_path.read_text(encoding="utf-8", errors="replace"))
        return " ".join(parts)
    for file in artifact_path.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() not in _SCANNABLE_EXTENSIONS:
            continue
        try:
            if file.stat().st_size > _MAX_FILE_SIZE:
                continue
            parts.append(file.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return " ".join(parts)


def _feature_present(feature: str, content_lower: str) -> bool:
    keywords = re.split(r"[-/]", feature.lower())
    return any(kw.strip() in content_lower for kw in keywords if len(kw.strip()) > 2)


def verify_artifact(
    *,
    intent: CapturedIntent,
    artifact_path: Path,
    iteration: int = 1,
) -> VerifyResult:
    content = _scan_artifact_content(artifact_path)
    content_lower = content.lower()

    if not content.strip():
        return VerifyResult(
            status="incomplete",
            confidence=0.1,
            missing=list(intent.required_features),
            agent_feedback=(
                "Das Artefakt ist leer oder enthält keine lesbaren Dateien. "
                f"Bitte implementiere: {', '.join(intent.required_features)}."
            ),
            iteration=iteration,
        )

    missing: list[str] = []
    found: list[str] = []
    for feature in intent.required_features:
        if _feature_present(feature, content_lower):
            found.append(feature)
        else:
            missing.append(feature)

    total = len(intent.required_features)
    coverage = len(found) / total if total > 0 else 1.0
    confidence = round(0.5 + coverage * 0.5, 2)

    if not missing:
        return VerifyResult(
            status="fulfilled",
            confidence=confidence,
            missing=[],
            agent_feedback="",
            iteration=iteration,
        )

    feedback = (
        f"Folgende Features fehlen noch: {', '.join(missing)}. "
        "Bitte implementiere diese Funktionen."
    )
    return VerifyResult(
        status="incomplete",
        confidence=confidence,
        missing=missing,
        agent_feedback=feedback,
        iteration=iteration,
    )
