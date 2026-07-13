"""Build ResolverContext from repo_root and framework detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.framework_intelligence import FrameworkIntelligenceService
from navigation.framework_intelligence.models import ProjectMetadata


@dataclass(frozen=True, slots=True)
class RepoLayoutHints:
    src_dir: Path | None = None
    app_dir: Path | None = None
    router_candidates: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "src_dir": str(self.src_dir) if self.src_dir else None,
            "app_dir": str(self.app_dir) if self.app_dir else None,
            "router_candidates": [str(p) for p in self.router_candidates],
        }


@dataclass(frozen=True, slots=True)
class ResolverContext:
    repo_root: Path
    framework: ProjectMetadata | None
    repo_layout: RepoLayoutHints

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": str(self.repo_root),
            "framework": self.framework.to_dict() if self.framework else None,
            "repo_layout": self.repo_layout.to_dict(),
        }


_ROUTER_CANDIDATE_REL = (
    "src/router.jsx",
    "src/router.tsx",
    "src/routes.tsx",
    "src/routes.jsx",
    "src/App.tsx",
    "src/App.jsx",
)


def _discover_layout(repo_root: Path) -> RepoLayoutHints:
    src = repo_root / "src"
    app = repo_root / "app"
    src_dir = src if src.is_dir() else None
    app_dir = app if app.is_dir() else None

    candidates: list[Path] = []
    for rel in _ROUTER_CANDIDATE_REL:
        path = repo_root / rel
        if path.is_file():
            candidates.append(path)
    if src_dir:
        for name in ("router.jsx", "router.tsx", "routes.tsx"):
            path = src_dir / name
            if path.is_file() and path not in candidates:
                candidates.append(path)

    return RepoLayoutHints(
        src_dir=src_dir,
        app_dir=app_dir,
        router_candidates=tuple(candidates),
    )


def build_resolver_context(
    repo_root: Path,
    *,
    framework: ProjectMetadata | None = None,
) -> ResolverContext:
    root = repo_root.resolve()
    meta = framework or FrameworkIntelligenceService().detect(root)
    return ResolverContext(
        repo_root=root,
        framework=meta,
        repo_layout=_discover_layout(root),
    )
