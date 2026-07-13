"""State owner resolver — React context, zustand, redux slices."""
from __future__ import annotations

import re
import time

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    EvidenceRef,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)

PLUGIN_ID = "state_owner.orchestrator"
_PATTERNS = (
    "**/*Context.jsx",
    "**/*Context.tsx",
    "**/*Slice.js",
    "**/*Slice.ts",
    "**/*Slice.jsx",
    "**/*Slice.tsx",
    "**/*store*.js",
    "**/*store*.ts",
    "**/*store*.jsx",
    "**/*store*.tsx",
)
_ZUSTAND_RE = re.compile(r"create\s*\(\s*(?:\([^)]*\)\s*=>)?\s*\{([^}]{0,2000})", re.DOTALL)
_REDUX_SLICE_RE = re.compile(
    r"createSlice\s*\(\s*\{[\s\S]*?name:\s*['\"]([^'\"]+)['\"]",
    re.DOTALL,
)
_VALUE_KEY_RE = re.compile(r"\b([a-zA-Z_][\w]*)\s*:")


def _keys_in_object_block(text: str, marker: str) -> set[str]:
    idx = text.find(marker)
    if idx < 0:
        return set()
    brace = text.find("{", idx)
    if brace < 0:
        return set()
    depth = 0
    for i in range(brace, min(len(text), brace + 4000)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                block = text[brace : i + 1]
                return {m.group(1) for m in _VALUE_KEY_RE.finditer(block)}
    return set()


def resolve_state_owner(key: str, ctx: ResolverContext, *, store_name: str = "") -> ResolverResult:
    start = time.perf_counter()
    needle = key.strip()
    store_hint = store_name.strip()
    if not needle and not store_hint:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.STATE_OWNER,
            status=ResolverStatus.ERROR,
            confidence=ConfidenceLevel.NONE,
            error="key or store_name required",
            latency_ms=0,
        )

    src = ctx.repo_layout.src_dir or ctx.repo_root
    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []
    scanned = 0

    for pattern in _PATTERNS:
        for path in src.glob(pattern):
            if scanned >= 50:
                break
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")[:80_000]
            rel = str(path.relative_to(ctx.repo_root)).replace("\\", "/")
            stem = path.stem.lower()

            if store_hint and store_hint.lower() not in stem and store_hint.lower() not in text.lower():
                continue

            slice_match = _REDUX_SLICE_RE.search(text)
            if slice_match and store_hint and slice_match.group(1).lower() == store_hint.lower():
                keys = _keys_in_object_block(text, "initialState")
                if not needle or needle in keys or needle in text:
                    matches.append(
                        ResolverMatch(
                            summary=f"Redux slice {slice_match.group(1)}",
                            file_path=rel,
                            symbol=slice_match.group(1),
                            metadata={"kind": "redux_slice", "key": needle or store_hint},
                        )
                    )
                    evidence.append(EvidenceRef(file=rel, snippet=f"createSlice name: {slice_match.group(1)}"))
                    continue

            if "zustand" in text or "create((" in text or "create((set" in text:
                zustand_body = _ZUSTAND_RE.search(text)
                if zustand_body and (not needle or needle in zustand_body.group(1)):
                    matches.append(
                        ResolverMatch(
                            summary=f"Zustand store in {path.stem}",
                            file_path=rel,
                            symbol=path.stem,
                            metadata={"kind": "zustand", "key": needle},
                        )
                    )
                    evidence.append(EvidenceRef(file=rel, snippet="zustand create()"))
                    continue

            search_terms = [t for t in (needle, store_hint) if t]
            if any(term in text for term in search_terms):
                kind = "react_context" if "createContext" in text else "store_file"
                matches.append(
                    ResolverMatch(
                        summary=f"State owner {path.stem}",
                        file_path=rel,
                        symbol=path.stem,
                        metadata={"kind": kind, "key": needle or store_hint},
                    )
                )

    if not matches:
        status = ResolverStatus.NOT_FOUND
        conf = ConfidenceLevel.NONE
    elif len(matches) > 1:
        status = ResolverStatus.AMBIGUOUS
        conf = ConfidenceLevel.MEDIUM
    else:
        status = ResolverStatus.RESOLVED
        conf = ConfidenceLevel.HIGH

    return ResolverResult(
        ok=status == ResolverStatus.RESOLVED,
        kind=ResolverKind.STATE_OWNER,
        status=status,
        confidence=conf,
        confidence_score=0.85 if status == ResolverStatus.RESOLVED else 0.4,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
