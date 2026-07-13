"""DTCG design token JSON resolver."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import EvidenceRef, ResolverMatch

PLUGIN_ID = "design_token.dtcg"
_TOKEN_FILE_NAMES = (
    "tokens.json",
    "design-tokens.json",
    "tokens/design-tokens.json",
    "src/tokens.json",
    "src/styles/tokens.json",
)


def _flatten_tokens(node: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(node, dict):
        if "$value" in node:
            val = node["$value"]
            out[prefix] = str(val)
            return out
        for key, value in node.items():
            if key.startswith("$"):
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_tokens(value, child_prefix))
    return out


def find_dtcg_matches(token: str, ctx: ResolverContext) -> tuple[list[ResolverMatch], list[EvidenceRef]]:
    matches: list[ResolverMatch] = []
    evidence: list[EvidenceRef] = []
    key = token.lstrip("-").strip()

    for rel in _TOKEN_FILE_NAMES:
        path = ctx.repo_root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        flat = _flatten_tokens(data)
        for name, value in flat.items():
            leaf = name.split(".")[-1]
            if name == key or leaf == key or name.endswith(f".{key}"):
                rel_path = str(path.relative_to(ctx.repo_root)).replace("\\", "/")
                matches.append(
                    ResolverMatch(
                        summary=f"DTCG token {name}",
                        file_path=rel_path,
                        symbol=name,
                        metadata={"value": value, "source": "dtcg"},
                    )
                )
                evidence.append(EvidenceRef(file=rel_path, snippet=f"{name}: {value}"))
    return matches, evidence
