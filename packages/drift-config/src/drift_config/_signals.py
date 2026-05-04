"""Signal abbreviation map and CLI filter helpers."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

from drift_config._schema import SignalWeights

if TYPE_CHECKING:
    from drift_config._loader import DriftConfig


_STATIC_ABBREV_FALLBACK: dict[str, str] = {
    "PFS": "pattern_fragmentation",
    "AVS": "architecture_violation",
    "MDS": "mutant_duplicate",
    "EDS": "explainability_deficit",
    "TVS": "temporal_volatility",
    "SMS": "system_misalignment",
    "DIA": "doc_impl_drift",
    "BEM": "broad_exception_monoculture",
    "TPD": "test_polarity_deficit",
    "GCD": "guard_clause_deficit",
    "COD": "cohesion_deficit",
    "NBV": "naming_contract_violation",
    "BAT": "bypass_accumulation",
    "ECM": "exception_contract_drift",
    "CCC": "co_change_coupling",
    "TSA": "ts_architecture",
    "CXS": "cognitive_complexity",
    "FOE": "fan_out_explosion",
    "CIR": "circular_import",
    "DCA": "dead_code_accumulation",
    "MAZ": "missing_authorization",
    "ISD": "insecure_default",
    "HSC": "hardcoded_secret",
    "PHR": "phantom_reference",
}


def _build_signal_abbrev() -> dict[str, str]:
    """Build abbrev→signal_id map from the central registry, with static fallback."""
    try:
        from drift.signal_registry import get_abbrev_map

        return get_abbrev_map()
    except ImportError:
        pass
    # Static fallback for environments where signals haven't been imported yet
    return _STATIC_ABBREV_FALLBACK


SIGNAL_ABBREV: dict[str, str] = _build_signal_abbrev()


def resolve_signal_names(raw: str) -> list[str]:
    """Resolve comma-separated signal IDs (abbreviations or full names) to full names.

    Raises ValueError for unknown signal IDs.
    """
    all_known = set(SignalWeights.model_fields.keys())
    result: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        upper = token.upper()
        if upper in SIGNAL_ABBREV:
            result.append(SIGNAL_ABBREV[upper])
        elif token.lower() in all_known:
            result.append(token.lower())
        else:
            all_abbrevs = sorted(SIGNAL_ABBREV)
            close = difflib.get_close_matches(upper, all_abbrevs, n=1, cutoff=0.6)
            hint = f" — did you mean '{close[0]}'?" if close else ""
            abbrevs = ", ".join(all_abbrevs)
            raise ValueError(
                f"Unknown signal: {token!r}{hint}\n"
                f"  Valid abbreviations: {abbrevs}"
            )
    return result


def apply_signal_filter(
    cfg: DriftConfig,
    select: str | None,
    ignore: str | None,
) -> None:
    """Modify config weights based on --select / --ignore CLI flags.

    --select: only these signals are active (all others set to weight 0).
    --ignore: these signals are deactivated (weight 0).
    If both are given, --select is applied first, then --ignore removes
    from the selected set.
    """
    if select:
        selected = set(resolve_signal_names(select))
        for key in SignalWeights.model_fields:
            if key not in selected:
                setattr(cfg.weights, key, 0.0)

    if ignore:
        ignored = set(resolve_signal_names(ignore))
        for key in ignored:
            setattr(cfg.weights, key, 0.0)
