"""Layout resolver — read regions from a design snapshot."""
from __future__ import annotations

import time
from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)

PLUGIN_ID = "layout.design_snapshot"


def resolve_layout(snapshot: DesignSnapshot | dict[str, Any], *, region: str = "") -> ResolverResult:
    start = time.perf_counter()
    snap = snapshot if isinstance(snapshot, DesignSnapshot) else DesignSnapshot.from_dict(snapshot)
    layout = snap.layout
    regions = list(layout.regions or [])
    if region:
        regions = [r for r in regions if region.lower() in str(r.get("name", "")).lower()]

    matches: list[ResolverMatch] = []
    for reg in regions:
        matches.append(
            ResolverMatch(
                summary=str(reg.get("name") or reg.get("role") or "region"),
                file_path="",
                symbol=str(reg.get("role") or ""),
                metadata=dict(reg),
            )
        )

    if not matches and layout.layout_tree:
        matches.append(
            ResolverMatch(
                summary="layout_tree",
                file_path="",
                metadata={"nodes": len(layout.layout_tree)},
            )
        )

    if not matches:
        status = ResolverStatus.NOT_FOUND
        conf = ConfidenceLevel.NONE
    else:
        status = ResolverStatus.RESOLVED
        conf = ConfidenceLevel.MEDIUM

    return ResolverResult(
        ok=bool(matches),
        kind=ResolverKind.LAYOUT,
        status=status,
        confidence=conf,
        confidence_score=0.75 if matches else 0.0,
        matches=matches,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
