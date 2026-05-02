"""Accountability cluster aggregation for drift-cockpit (Feature 006).

Pure functions — no I/O.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from drift_sdk.models import Finding

from drift_cockpit._models import AccountabilityCluster


def aggregate_clusters(
    findings: list[Finding],
    files: list[str] | None = None,
) -> list[AccountabilityCluster]:
    """Group findings into AccountabilityClusters by signal category (FR-005).

    Returns clusters sorted by risk_contribution descending.
    """
    if not findings:
        return []

    # Group by signal category (signal_id prefix before underscore, or full signal_id)
    groups: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        signal_id = getattr(f, "signal_id", None) or getattr(f, "check", None) or "unknown"
        # Use the signal category prefix as cluster label (e.g. "AVS", "PFS")
        category = signal_id.split("_")[0].upper() if signal_id else "UNKNOWN"
        groups[category].append(f)

    # Compute total impact for normalisation
    total_impact = sum(getattr(f, "impact", 0.0) for fs in groups.values() for f in fs)
    total_impact = max(total_impact, 1e-9)

    clusters: list[AccountabilityCluster] = []
    for label, group_findings in groups.items():
        cluster_impact = sum(getattr(f, "impact", 0.0) for f in group_findings)
        risk_contribution = round(cluster_impact / total_impact, 4)
        cluster_files = list(
            {
                str(ref)
                for f in group_findings
                for ref in [getattr(f, "file", None) or getattr(f, "path", None)]
                if ref
            }
        )
        driver_ids = [
            getattr(f, "signal_id", None) or getattr(f, "check", None) or "unknown"
            for f in group_findings
        ]
        clusters.append(
            AccountabilityCluster(
                cluster_id=f"ac-{uuid.uuid4().hex[:8]}",
                pr_id="",  # filled in by build_decision_bundle
                label=label,
                files=cluster_files,
                risk_contribution=risk_contribution,
                dominant_drivers=list(dict.fromkeys(driver_ids)),
            )
        )

    return sorted(clusters, key=lambda c: c.risk_contribution, reverse=True)
