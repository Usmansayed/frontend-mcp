"""Design token resolver — CSS vars, tailwind config, DTCG JSON."""
from __future__ import annotations

import time

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    FallbackHint,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)
from navigation.resolver_intelligence.plugins.design_token import css_vars, dtcg

PLUGIN_ID = "design_token.orchestrator"


def resolve_design_token(token: str, ctx: ResolverContext) -> ResolverResult:
    start = time.perf_counter()
    css_result = css_vars.resolve_design_token(token, ctx)
    dtcg_matches, dtcg_evidence = dtcg.find_dtcg_matches(token, ctx)

    matches: list[ResolverMatch] = list(css_result.matches)
    evidence = list(css_result.evidence)
    seen = {m.file_path + (m.symbol or "") for m in matches}
    for m in dtcg_matches:
        sig = m.file_path + (m.symbol or "")
        if sig not in seen:
            matches.append(m)
            seen.add(sig)
    evidence.extend(dtcg_evidence)

    if not matches:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.DESIGN_TOKEN,
            status=ResolverStatus.NOT_FOUND,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["token_not_found"],
            fallback=FallbackHint(
                strategy="host_search",
                message=f"Design token {token!r} not found in CSS, tailwind, or DTCG files.",
                suggested_tools=[],
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if len(matches) > 1:
        status = ResolverStatus.AMBIGUOUS
        conf = ConfidenceLevel.MEDIUM
    else:
        status = ResolverStatus.RESOLVED
        conf = ConfidenceLevel.HIGH

    return ResolverResult(
        ok=status == ResolverStatus.RESOLVED,
        kind=ResolverKind.DESIGN_TOKEN,
        status=status,
        confidence=conf,
        confidence_score=0.9 if status == ResolverStatus.RESOLVED else 0.5,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
