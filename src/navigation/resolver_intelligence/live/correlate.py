"""Live correlation — match resolution/claim against live scan observation."""
from __future__ import annotations

import re
import time
from typing import Any

from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    EvidenceRef,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)

PLUGIN_ID = "live.correlate"
_TESTID_RE = re.compile(r'data-testid=["\']([^"\']+)["\']', re.IGNORECASE)


def _observation_text(scan: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("dom_text", "dom_summary", "dom", "page_text"):
        val = scan.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    obs = scan.get("observation")
    if isinstance(obs, dict):
        for key in ("dom_text", "dom_summary"):
            val = obs.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val)
    return "\n".join(parts).lower()


def _collect_symbols(
    *,
    resolution: dict[str, Any] | None,
    claim: dict[str, Any] | None,
) -> list[str]:
    symbols: list[str] = []
    if resolution:
        for match in resolution.get("matches") or []:
            if isinstance(match, dict):
                for field in ("symbol", "summary"):
                    val = match.get(field)
                    if val:
                        symbols.append(str(val))
                route = match.get("route")
                if route:
                    symbols.append(str(route).strip("/").split("/")[-1])
    if claim:
        comp = claim.get("component")
        if isinstance(comp, dict) and comp.get("name"):
            symbols.append(str(comp["name"]))
        elif isinstance(comp, str):
            symbols.append(comp)
        route = claim.get("route")
        if route:
            symbols.append(str(route).strip("/").split("/")[-1])
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in symbols:
        key = s.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def correlate_live(
    scan: dict[str, Any],
    *,
    resolution: dict[str, Any] | None = None,
    claim: dict[str, Any] | None = None,
) -> ResolverResult:
    start = time.perf_counter()
    text_blob = _observation_text(scan)
    test_ids = _TESTID_RE.findall(text_blob)
    symbols = _collect_symbols(resolution=resolution, claim=claim)

    hits: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []

    for symbol in symbols:
        sym_lower = symbol.lower()
        if sym_lower in text_blob:
            hits.append(
                ResolverMatch(
                    summary=f"DOM text contains {symbol!r}",
                    file_path="",
                    symbol=symbol,
                    metadata={"signal": "dom_text"},
                )
            )
            evidence.append(EvidenceRef(snippet=f"text match: {symbol}"))
        kebab = "".join(["-" + c.lower() if c.isupper() else c for c in symbol]).lstrip("-")
        for tid in test_ids:
            if sym_lower in tid.lower() or kebab in tid.lower():
                hits.append(
                    ResolverMatch(
                        summary=f"data-testid {tid!r} matches {symbol}",
                        file_path="",
                        symbol=symbol,
                        metadata={"signal": "data-testid", "testid": tid},
                    )
                )
                evidence.append(EvidenceRef(snippet=f'data-testid="{tid}"'))

    agent = scan.get("agent_summary") or {}
    blocking = list(agent.get("blocking") or [])

    if hits:
        status = ResolverStatus.RESOLVED
        conf = ConfidenceLevel.HIGH
        score = 0.9
    elif symbols and text_blob:
        status = ResolverStatus.LOW_CONFIDENCE
        conf = ConfidenceLevel.LOW
        score = 0.25
    else:
        status = ResolverStatus.NOT_FOUND
        conf = ConfidenceLevel.NONE
        score = 0.0

    return ResolverResult(
        ok=bool(hits),
        kind=ResolverKind.ROUTE,
        status=status,
        confidence=conf,
        confidence_score=score,
        matches=hits,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        degraded=blocking[:3],
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
