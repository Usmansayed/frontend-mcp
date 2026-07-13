"""Component resolver — shadcn components.json + folder conventions."""
from __future__ import annotations

import time
from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    EvidenceRef,
    FallbackHint,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)
from navigation.resolver_intelligence.plugins.component import conventions, shadcn

PLUGIN_ID = "component.orchestrator"


def resolve_component(name: str, ctx: ResolverContext) -> ResolverResult:
    start = time.perf_counter()
    if not name.strip():
        return ResolverResult(
            ok=False,
            kind=ResolverKind.COMPONENT,
            status=ResolverStatus.ERROR,
            confidence=ConfidenceLevel.NONE,
            error="name required",
            latency_ms=0,
        )

    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []

    shadcn_matches = shadcn.find_shadcn_matches(name, ctx)
    if shadcn_matches:
        matches.extend(shadcn_matches)
        evidence.append(
            EvidenceRef(file="components.json", snippet=f"shadcn alias lookup for {name}")
        )

    conv = conventions.resolve_component(name, ctx)
    if conv.matches:
        seen = {m.file_path for m in matches}
        for m in conv.matches:
            if m.file_path not in seen:
                matches.append(m)

    if not matches:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.COMPONENT,
            status=ResolverStatus.NOT_FOUND,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["component_not_found"],
            fallback=FallbackHint(
                strategy="host_search",
                message=f"No component match for {name!r}.",
                suggested_tools=["perception_validate_component_claim"],
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if len(matches) > 1:
        status = ResolverStatus.AMBIGUOUS
        conf = ConfidenceLevel.MEDIUM
        score = 0.55
    else:
        status = ResolverStatus.RESOLVED
        conf = ConfidenceLevel.HIGH if shadcn_matches else ConfidenceLevel.MEDIUM
        score = 0.95 if shadcn_matches else 0.85

    return ResolverResult(
        ok=status == ResolverStatus.RESOLVED,
        kind=ResolverKind.COMPONENT,
        status=status,
        confidence=conf,
        confidence_score=score,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
