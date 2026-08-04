"""Next.js App Router static route resolver (app/ and src/app/)."""
from __future__ import annotations

import time
from pathlib import Path

from navigation.resolver_intelligence.confidence import score_route_match
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

PLUGIN_ID = "next-app-router.static"
_PAGE_NAMES = ("page.tsx", "page.jsx", "page.ts", "page.js")


def can_handle(ctx: ResolverContext) -> bool:
    meta = ctx.framework
    if meta is not None and (meta.framework == "Next.js" or meta.primary_package == "next"):
        return True
    app_dir = ctx.repo_layout.app_dir
    return bool(app_dir and app_dir.is_dir())


def _app_roots(ctx: ResolverContext) -> list[Path]:
    roots: list[Path] = []
    if ctx.repo_layout.app_dir and ctx.repo_layout.app_dir.is_dir():
        roots.append(ctx.repo_layout.app_dir)
    for rel in ("app", "src/app"):
        path = ctx.repo_root / rel
        if path.is_dir() and path not in roots:
            roots.append(path)
    return roots


def _normalize_url_path(path: str) -> str:
    p = (path or "/").strip()
    if not p.startswith("/"):
        p = "/" + p
    if p != "/" and p.endswith("/"):
        p = p[:-1]
    return p or "/"


def _segments(url_path: str) -> list[str]:
    if url_path == "/":
        return []
    return [s for s in url_path.strip("/").split("/") if s]


def _is_route_group(name: str) -> bool:
    return name.startswith("(") and name.endswith(")")


def _segment_matches(dir_name: str, url_seg: str) -> bool:
    if _is_route_group(dir_name):
        return False
    if dir_name == url_seg:
        return True
    # [slug], [...slug], [[...slug]]
    return dir_name.startswith("[") and dir_name.endswith("]")


def _expand_for_segment(cur: Path, seg: str) -> list[Path]:
    out: list[Path] = []
    if not cur.is_dir():
        return out
    exact = cur / seg
    if exact.is_dir():
        out.append(exact)
    for child in sorted(cur.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if _is_route_group(name):
            out.extend(_expand_for_segment(child, seg))
        elif _segment_matches(name, seg) and child not in out:
            out.append(child)
    return out


def _page_in_dir(cur: Path) -> Path | None:
    for name in _PAGE_NAMES:
        page = cur / name
        if page.is_file():
            return page
    if not cur.is_dir():
        return None
    for child in sorted(cur.iterdir()):
        if child.is_dir() and _is_route_group(child.name):
            found = _page_in_dir(child)
            if found:
                return found
    return None


def _find_page_file(app_root: Path, url_path: str) -> Path | None:
    segs = _segments(url_path)
    candidates: list[Path] = [app_root]
    for seg in segs:
        next_level: list[Path] = []
        for cur in candidates:
            next_level.extend(_expand_for_segment(cur, seg))
        candidates = next_level
        if not candidates:
            return None
    for cur in candidates:
        found = _page_in_dir(cur)
        if found:
            return found
    return None


def resolve_route(path: str, ctx: ResolverContext) -> ResolverResult:
    start = time.perf_counter()
    url_path = _normalize_url_path(path)
    roots = _app_roots(ctx)
    if not roots:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.ROUTE,
            status=ResolverStatus.UNSUPPORTED,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["next_app_dir_missing"],
            fallback=FallbackHint(
                strategy="host_search",
                message="No Next.js app/ or src/app directory found.",
                suggested_tools=["perception_detect_framework"],
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    page: Path | None = None
    for root in roots:
        page = _find_page_file(root, url_path)
        if page:
            break

    if page is None:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.ROUTE,
            status=ResolverStatus.NOT_FOUND,
            confidence=ConfidenceLevel.LOW,
            resolver_id=PLUGIN_ID,
            degraded=["next_route_not_found"],
            fallback=FallbackHint(
                strategy="host_search",
                message=f"No page.tsx matched for route {url_path}.",
                suggested_tools=["perception_validate_route_claim"],
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    try:
        rel = str(page.relative_to(ctx.repo_root)).replace("\\", "/")
    except ValueError:
        rel = str(page).replace("\\", "/")

    dynamic = "[" in page.as_posix()
    score, confidence, status = score_route_match(
        exact_path=not dynamic,
        file_on_disk=True,
        dynamic_segment=dynamic,
        match_count=1,
    )
    return ResolverResult(
        ok=True,
        kind=ResolverKind.ROUTE,
        status=status,
        confidence=confidence,
        confidence_score=score,
        resolver_id=PLUGIN_ID,
        matches=[
            ResolverMatch(
                summary=f"Next.js App Router page for {url_path}",
                file_path=rel,
                symbol="page",
                route=url_path,
                metadata={"router": "app"},
            )
        ],
        evidence=[EvidenceRef(file=rel, snippet="export default function Page")],
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
