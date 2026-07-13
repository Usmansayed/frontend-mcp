"""Design token resolver — CSS variables and tailwind theme keys."""
from __future__ import annotations

import re
import time
from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    EvidenceRef,
    ResolverKind,
    ResolverMatch,
    ResolverResult,
    ResolverStatus,
)

PLUGIN_ID = "design_token.css_vars"
_VAR_RE = re.compile(r"--([\w-]+)\s*:\s*([^;}\n]+)")


def _normalize_token(token: str) -> str:
    token = token.strip()
    return token[2:] if token.startswith("--") else token


def resolve_design_token(token: str, ctx: ResolverContext) -> ResolverResult:
    start = time.perf_counter()
    key = _normalize_token(token)
    if not key:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.DESIGN_TOKEN,
            status=ResolverStatus.ERROR,
            confidence=ConfidenceLevel.NONE,
            error="token required",
            latency_ms=0,
        )

    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []

    css_files = list(ctx.repo_root.glob("src/**/*.css"))[:20]
    if not css_files:
        css_files = list(ctx.repo_root.glob("**/*.css"))[:20]

    for path in css_files:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in _VAR_RE.finditer(line):
                var_name, value = match.group(1), match.group(2).strip()
                if var_name != key:
                    continue
                rel = str(path.relative_to(ctx.repo_root)).replace("\\", "/")
                matches.append(
                    ResolverMatch(
                        summary=f"CSS variable --{var_name}",
                        file_path=rel,
                        symbol=var_name,
                        line_start=line_no,
                        metadata={"value": value, "source": "css_var"},
                    )
                )
                evidence.append(EvidenceRef(file=rel, line=line_no, snippet=line.strip()))

    tailwind = ctx.repo_root / "tailwind.config.js"
    for cfg_name in ("tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"):
        cfg = ctx.repo_root / cfg_name
        if cfg.is_file():
            text = cfg.read_text(encoding="utf-8", errors="replace")[:200_000]
            if key in text:
                rel = str(cfg.relative_to(ctx.repo_root)).replace("\\", "/")
                matches.append(
                    ResolverMatch(
                        summary=f"Tailwind theme key {key}",
                        file_path=rel,
                        symbol=key,
                        metadata={"source": "tailwind_config"},
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
        kind=ResolverKind.DESIGN_TOKEN,
        status=status,
        confidence=conf,
        confidence_score=0.85 if status == ResolverStatus.RESOLVED else 0.4,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
