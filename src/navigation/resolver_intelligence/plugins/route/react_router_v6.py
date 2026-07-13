"""React Router v6 static route resolver — reference plugin."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from navigation.resolver_intelligence.confidence import fallback_for_status, score_route_match
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

PLUGIN_ID = "react-router-v6.static"
_SKIP_COMPONENTS = frozenset({"ProtectedRoute", "Navigate", "Fragment", "Outlet"})
_IMPORT_RE = re.compile(
    r"""^import\s+(?:\{[^}]+\}|\w+)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_NAMED_IMPORT_RE = re.compile(
    r"""^import\s+(\w+)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_PATH_RE = re.compile(r"""path:\s*['"]([^'"]*)['"]""")
_ELEMENT_SECTION_RE = re.compile(r"element:\s*([\s\S]*?)(?:,\s*(?:children|index)\b|$)")


@dataclass(slots=True)
class _RouteHit:
    route: str
    component: str
    line: int
    router_file: Path


def can_handle(ctx: ResolverContext) -> bool:
    meta = ctx.framework
    if meta is None:
        return False
    if meta.primary_package == "react-router-dom":
        return True
    if meta.framework in ("react", "vite-react") and meta.router_mode in (
        "react-router",
        "react-router-dom",
        None,
    ):
        return bool(ctx.repo_layout.router_candidates)
    deps_signal = (meta.project_structure or {}).get("dependencies") or {}
    if isinstance(deps_signal, dict) and "react-router-dom" in deps_signal:
        return True
    pkg = ctx.repo_root / "package.json"
    if pkg.is_file():
        text = pkg.read_text(encoding="utf-8", errors="replace")
        return "react-router-dom" in text
    return False


def router_file_candidates(ctx: ResolverContext) -> list[Path]:
    return list(ctx.repo_layout.router_candidates)


def _read_bounded(path: Path, max_bytes: int = 512_000) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def _resolve_import(router_dir: Path, spec: str) -> str | None:
    if spec.startswith("."):
        base = (router_dir / spec).resolve()
        for ext in ("", ".jsx", ".tsx", ".js", ".ts"):
            candidate = Path(str(base) + ext)
            if candidate.is_file():
                return str(candidate)
    return None


def _build_import_map(router_file: Path, text: str) -> dict[str, str]:
    router_dir = router_file.parent
    mapping: dict[str, str] = {}
    for match in _NAMED_IMPORT_RE.finditer(text):
        name, spec = match.group(1), match.group(2)
        resolved = _resolve_import(router_dir, spec)
        if resolved:
            mapping[name] = resolved
    for match in _IMPORT_RE.finditer(text):
        line = match.group(0)
        brace = re.search(r"\{([^}]+)\}", line)
        if not brace:
            continue
        spec = match.group(1)
        resolved = _resolve_import(router_dir, spec)
        if not resolved:
            continue
        for part in brace.group(1).split(","):
            name = part.strip().split(" as ")[0].strip()
            if name:
                mapping[name] = resolved
    return mapping


def _join_paths(parent: str, child: str) -> str:
    if child.startswith("/"):
        return child.rstrip("/") or "/"
    parent = (parent or "").strip()
    if not parent or parent == "/":
        base = ""
    else:
        base = parent if parent.startswith("/") else f"/{parent}"
        base = base.rstrip("/")
    if not child:
        return base or "/"
    if not base:
        return f"/{child.lstrip('/')}"
    return f"{base}/{child.lstrip('/')}".replace("//", "/")


def _extract_element_component(segment: str) -> str | None:
    names = re.findall(r"<(\w+)", segment)
    for name in reversed(names):
        if name not in _SKIP_COMPONENTS:
            return name
    return names[-1] if names else None


def _find_bracket_end(text: str, open_index: int) -> int:
    depth = 0
    for i in range(open_index, len(text)):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_brace_end(text: str, open_index: int) -> int:
    depth = 0
    for i in range(open_index, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_top_level_objects(array_body: str) -> list[str]:
    blocks: list[str] = []
    i = 0
    length = len(array_body)
    while i < length:
        while i < length and array_body[i] not in "{":
            i += 1
        if i >= length:
            break
        end = _find_brace_end(array_body, i)
        if end < 0:
            break
        blocks.append(array_body[i : end + 1])
        i = end + 1
    return blocks


def _line_number_at(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _route_header(block: str) -> str:
    children_match = re.search(r"\bchildren:\s*\[", block)
    if children_match:
        return block[: children_match.start()]
    return block


def _parse_route_block(
    block: str,
    *,
    parent_path: str,
    router_file: Path,
    full_text: str,
    block_offset: int,
) -> list[_RouteHit]:
    hits: list[_RouteHit] = []
    header = _route_header(block)
    path_match = _PATH_RE.search(header)
    is_index = bool(re.search(r"\bindex:\s*true\b", header))
    segment = path_match.group(1) if path_match else ""
    full_path = parent_path if is_index else _join_paths(parent_path, segment)

    element_match = _ELEMENT_SECTION_RE.search(header)
    if element_match:
        component = _extract_element_component(element_match.group(1))
        if component:
            line = _line_number_at(full_text, block_offset + element_match.start())
            hits.append(
                _RouteHit(
                    route=full_path,
                    component=component,
                    line=line,
                    router_file=router_file,
                )
            )

    children_match = re.search(r"children:\s*\[", block)
    if children_match:
        bracket_start = block.index("[", children_match.start())
        bracket_end = _find_bracket_end(block, bracket_start)
        if bracket_end > bracket_start:
            inner = block[bracket_start + 1 : bracket_end]
            inner_offset = block_offset + bracket_start + 1
            for child_block in _split_top_level_objects(inner):
                child_offset = inner.find(child_block)
                hits.extend(
                    _parse_route_block(
                        child_block,
                        parent_path=full_path,
                        router_file=router_file,
                        full_text=full_text,
                        block_offset=inner_offset + child_offset,
                    )
                )
    return hits


def _extract_router_array(text: str) -> tuple[str, int] | None:
    marker = "createBrowserRouter("
    idx = text.find(marker)
    if idx < 0:
        return None
    bracket_start = text.find("[", idx)
    if bracket_start < 0:
        return None
    bracket_end = _find_bracket_end(text, bracket_start)
    if bracket_end < 0:
        return None
    return text[bracket_start + 1 : bracket_end], bracket_start + 1


def _collect_hits(router_file: Path, text: str) -> list[_RouteHit]:
    extracted = _extract_router_array(text)
    if extracted is None:
        return []
    body, offset = extracted
    hits: list[_RouteHit] = []
    for block in _split_top_level_objects(body):
        block_offset = offset + body.find(block)
        hits.extend(
            _parse_route_block(
                block,
                parent_path="",
                router_file=router_file,
                full_text=text,
                block_offset=block_offset,
            )
        )
    return hits


def _normalize_route(path: str) -> str:
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") or "/"


def _match_route(query_path: str, hit_route: str) -> bool:
    q = _normalize_route(query_path)
    r = _normalize_route(hit_route)
    if q == r:
        return True
    # dynamic segment: /team/:id matches /team/42
    q_parts = q.strip("/").split("/")
    r_parts = r.strip("/").split("/")
    if len(q_parts) != len(r_parts):
        return False
    for qp, rp in zip(q_parts, r_parts, strict=False):
        if rp.startswith(":"):
            continue
        if qp != rp:
            return False
    return True


def resolve_route(path: str, ctx: ResolverContext) -> ResolverResult:
    start = time.perf_counter()
    candidates = router_file_candidates(ctx)
    if not candidates:
        return ResolverResult(
            ok=False,
            kind=ResolverKind.ROUTE,
            status=ResolverStatus.UNSUPPORTED,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["no_router_candidates"],
            fallback=FallbackHint(
                strategy="host_search",
                message="No router config files found.",
                suggested_tools=["perception_validate_route_claim"],
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    all_hits: list[_RouteHit] = []
    import_maps: dict[Path, dict[str, str]] = {}
    for router_file in candidates:
        rel = router_file
        try:
            rel = router_file.relative_to(ctx.repo_root)
        except ValueError:
            pass
        text = _read_bounded(router_file)
        if "createBrowserRouter" not in text:
            continue
        import_maps[router_file] = _build_import_map(router_file, text)
        all_hits.extend(_collect_hits(router_file, text))

    matched = [h for h in all_hits if _match_route(path, h.route)]
    if not matched:
        latency = int((time.perf_counter() - start) * 1000)
        return ResolverResult(
            ok=False,
            kind=ResolverKind.ROUTE,
            status=ResolverStatus.NOT_FOUND,
            confidence=ConfidenceLevel.NONE,
            resolver_id=PLUGIN_ID,
            degraded=["route_not_in_static_config"],
            fallback=FallbackHint(
                strategy="host_search",
                message=f"No static route match for {path!r}.",
                suggested_tools=["perception_validate_route_claim"],
            ),
            latency_ms=latency,
        )

    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []
    for hit in matched:
        imports = import_maps.get(hit.router_file, {})
        file_path = imports.get(hit.component, "")
        rel_file = file_path
        if file_path:
            try:
                rel_file = str(Path(file_path).relative_to(ctx.repo_root)).replace("\\", "/")
            except ValueError:
                rel_file = file_path.replace("\\", "/")
        on_disk = bool(file_path and Path(file_path).is_file())
        matches.append(
            ResolverMatch(
                summary=f"{hit.component} renders {hit.route}",
                file_path=rel_file,
                symbol=hit.component,
                line_start=hit.line,
                route=hit.route,
                metadata={"router_file": str(hit.router_file.relative_to(ctx.repo_root)).replace("\\", "/")},
            )
        )
        evidence.append(
            EvidenceRef(
                file=str(hit.router_file.relative_to(ctx.repo_root)).replace("\\", "/"),
                line=hit.line,
                snippet=f"element: <{hit.component} />",
            )
        )

    exact = any(_normalize_route(path) == _normalize_route(m.route or "") for m in matches)
    dynamic_seg = any(":" in (m.route or "") for m in matches)
    score, confidence, status = score_route_match(
        exact_path=exact,
        file_on_disk=all(Path(import_maps.get(h.router_file, {}).get(h.component, "")).is_file() for h in matched),
        dynamic_segment=dynamic_seg,
        match_count=len(matches),
    )

    strategy = fallback_for_status(status)
    fallback = None
    if status != ResolverStatus.RESOLVED:
        fallback = FallbackHint(
            strategy=strategy,  # type: ignore[arg-type]
            message=f"Route resolution {status.value}.",
            suggested_tools=["perception_validate_route_claim"],
        )

    latency = int((time.perf_counter() - start) * 1000)
    return ResolverResult(
        ok=status == ResolverStatus.RESOLVED,
        kind=ResolverKind.ROUTE,
        status=status,
        confidence=confidence,
        confidence_score=score,
        matches=matches,
        evidence=evidence,
        resolver_id=PLUGIN_ID,
        fallback=fallback,
        latency_ms=latency,
    )
