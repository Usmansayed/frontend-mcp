"""API endpoint resolver — Next.js, Hono, Express-style route patterns."""
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

PLUGIN_ID = "api_endpoint.patterns"
_API_DIRS = (
    "pages/api",
    "app/api",
    "src/pages/api",
    "src/app/api",
    "src/routes",
    "src/server",
    "server",
)
_NEXT_HANDLER_RE = re.compile(
    r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    re.IGNORECASE,
)
_HONO_RE = re.compile(
    r"\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_FETCH_ROUTE_RE = re.compile(
    r"(?:fetch|axios\.(?:get|post|put|patch|delete))\(\s*['\"`]([^'\"`]+)['\"`]",
    re.IGNORECASE,
)
_MAX_FILES = 100
_READ_CAP = 120_000


def _normalize_route(path: str) -> str:
    p = path.strip()
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def _file_implies_route(file: Path, base: Path, repo_root: Path) -> str | None:
    """Filesystem route from app/api/users/route.ts → /api/users."""
    try:
        rel_from_repo = file.relative_to(repo_root)
    except ValueError:
        return None
    parts = list(rel_from_repo.parts)
    if not parts:
        return None
    if parts[-1] in ("route.ts", "route.js", "route.tsx", "route.jsx"):
        parts = parts[:-1]
    elif parts[-1].endswith((".ts", ".js", ".tsx", ".jsx")):
        parts[-1] = Path(parts[-1]).stem

    if "api" in parts:
        idx = parts.index("api")
        route_parts = parts[idx:]
    else:
        try:
            route_parts = list(file.relative_to(base).parts)
            if route_parts and route_parts[-1].startswith("route."):
                route_parts = route_parts[:-1]
        except ValueError:
            return None

    if not route_parts:
        return None
    return _normalize_route("/" + "/".join(route_parts))


def resolve_api_endpoint(path: str, ctx: ResolverContext, *, method: str = "") -> ResolverResult:
    start = time.perf_counter()
    route = _normalize_route(path)
    if route == "/":
        return ResolverResult(
            ok=False,
            kind=ResolverKind.API_ENDPOINT,
            status=ResolverStatus.ERROR,
            confidence=ConfidenceLevel.NONE,
            error="path required",
            latency_ms=0,
        )

    want_method = method.upper().strip()
    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []
    scanned = 0

    for rel_dir in _API_DIRS:
        base = ctx.repo_root / rel_dir
        if not base.is_dir():
            continue
        for file in base.rglob("*"):
            if scanned >= _MAX_FILES:
                break
            if file.suffix.lower() not in {".js", ".ts", ".jsx", ".tsx"}:
                continue
            scanned += 1
            text = file.read_text(encoding="utf-8", errors="replace")[:_READ_CAP]
            rel = str(file.relative_to(ctx.repo_root)).replace("\\", "/")

            implied = _file_implies_route(file, base, ctx.repo_root)
            if implied and _routes_match(route, implied):
                handlers = [m.group(1).upper() for m in _NEXT_HANDLER_RE.finditer(text)]
                if not want_method or want_method in handlers or not handlers:
                    matches.append(
                        ResolverMatch(
                            summary=f"Filesystem API route {implied}",
                            file_path=rel,
                            route=implied,
                            metadata={"methods": handlers or ["any"], "match": "filesystem"},
                        )
                    )
                    evidence.append(EvidenceRef(file=rel, snippet=f"route file → {implied}"))

            for m in _HONO_RE.finditer(text):
                http_method, hono_path = m.group(1).upper(), _normalize_route(m.group(2))
                if _routes_match(route, hono_path) and (not want_method or want_method == http_method):
                    matches.append(
                        ResolverMatch(
                            summary=f"Hono {http_method} {hono_path}",
                            file_path=rel,
                            route=hono_path,
                            metadata={"method": http_method, "match": "hono"},
                        )
                    )

            for m in _FETCH_ROUTE_RE.finditer(text):
                fetch_path = _normalize_route(m.group(1))
                if _routes_match(route, fetch_path):
                    matches.append(
                        ResolverMatch(
                            summary=f"Client fetch to {fetch_path}",
                            file_path=rel,
                            route=fetch_path,
                            metadata={"match": "fetch_reference"},
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
        kind=ResolverKind.API_ENDPOINT,
        status=status,
        confidence=conf,
        confidence_score=0.8 if status == ResolverStatus.RESOLVED else 0.35,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


def _routes_match(query: str, candidate: str) -> bool:
    q = _normalize_route(query)
    c = _normalize_route(candidate)
    if q == c:
        return True
    q_parts = q.strip("/").split("/")
    c_parts = c.strip("/").split("/")
    if len(q_parts) != len(c_parts):
        return False
    for qp, cp in zip(q_parts, c_parts, strict=False):
        if cp.startswith(":") or cp.startswith("["):
            continue
        if qp != cp:
            return False
    return True
