"""Shadcn components.json component resolver."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import ResolverMatch

PLUGIN_ID = "component.shadcn"
_CANDIDATE_NAMES = ("components.json", "components.jsonc")


def _load_components_json(repo_root: Path) -> dict[str, Any] | None:
    for name in _CANDIDATE_NAMES:
        path = repo_root / name
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
    return None


def _alias_to_path(repo_root: Path, alias_path: str) -> Path | None:
    """Map @/components/ui → src/components/ui (common Vite/TS alias)."""
    raw = alias_path.strip()
    if raw.startswith("@/"):
        raw = raw[2:]
    candidates = [
        repo_root / "src" / raw,
        repo_root / raw,
    ]
    for base in candidates:
        if base.is_dir():
            return base
    return None


def find_shadcn_matches(name: str, ctx: ResolverContext) -> list[ResolverMatch]:
    cfg = _load_components_json(ctx.repo_root)
    if cfg is None:
        return []

    aliases = cfg.get("aliases") or {}
    ui_alias = str(aliases.get("ui") or aliases.get("components") or "").strip()
    if not ui_alias:
        return []

    ui_dir = _alias_to_path(ctx.repo_root, ui_alias)
    if ui_dir is None:
        return []

    kebab = "".join(["-" + c.lower() if c.isupper() else c for c in name]).lstrip("-")
    candidates = [
        ui_dir / f"{name}.tsx",
        ui_dir / f"{name}.jsx",
        ui_dir / f"{kebab}.tsx",
        ui_dir / f"{kebab}.jsx",
        ui_dir / name / "index.tsx",
        ui_dir / name / "index.jsx",
    ]
    matches: list[ResolverMatch] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            rel = str(path.relative_to(ctx.repo_root)).replace("\\", "/")
        except ValueError:
            rel = str(path).replace("\\", "/")
        matches.append(
            ResolverMatch(
                summary=f"Shadcn component {name}",
                file_path=rel,
                symbol=name,
                metadata={"match": "components_json", "plugin": PLUGIN_ID},
            )
        )
    return matches
