"""Component resolver — folder conventions (components/, pages/)."""
from __future__ import annotations

import time
from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)

PLUGIN_ID = "component.conventions"
_MAX_FILES = 200
_READ_CAP = 50_000


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

    src = ctx.repo_layout.src_dir
    if src is None:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.COMPONENT,
            status=ResolverStatus.UNSUPPORTED,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["no_src_dir"],
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    targets = [src / "components", src / "pages"]
    matches: list[ResolverMatch] = []
    scanned = 0
    for base in targets:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if scanned >= _MAX_FILES:
                break
            if path.suffix.lower() not in {".jsx", ".tsx", ".js", ".ts"}:
                continue
            scanned += 1
            rel = str(path.relative_to(ctx.repo_root)).replace("\\", "/")
            stem_match = path.stem.lower() == name.lower()
            symbol = name
            if stem_match:
                matches.append(
                    ResolverMatch(
                        summary=f"Component file {path.stem}",
                        file_path=rel,
                        symbol=path.stem,
                        metadata={"match": "filename"},
                    )
                )
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:_READ_CAP]
            patterns = (
                f"export function {name}",
                f"export default function {name}",
                f"function {name}(",
                f"const {name} =",
            )
            if any(p in text for p in patterns):
                matches.append(
                    ResolverMatch(
                        summary=f"Exported component {name}",
                        file_path=rel,
                        symbol=name,
                        metadata={"match": "export"},
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
        kind=ResolverKind.COMPONENT,
        status=status,
        confidence=conf,
        confidence_score=0.9 if status == ResolverStatus.RESOLVED else 0.5,
        matches=matches,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
