"""Load distilled runtime artifacts (R0–R12) from coordination_layer/runtime/."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def runtime_dir() -> Path:
    """Bundled R0–R12 artifacts shipped inside the installed wheel."""
    bundled = Path(__file__).resolve().parent / "runtime"
    if bundled.is_dir() and (bundled / "manifest.json").is_file():
        return bundled
    # Dev checkout: coordination_layer/runtime at repo root
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "coordination_layer" / "runtime"


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required to load coordination runtime artifacts")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    """R12 and future artifacts — empty dict if missing (backward compatible)."""
    if not path.is_file():
        return {}
    return _load_yaml(path)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@dataclass
class RuntimeArtifactBundle:
    """Validated runtime artifacts consumed by PSM Runtime and planning layer."""

    manifest: dict[str, Any]
    capability_graph: dict[str, Any]
    cluster_registry: dict[str, Any]
    playbook_templates: dict[str, Any]
    invariant_registry: dict[str, Any]
    replan_registry: dict[str, Any]
    decision_heuristics: dict[str, Any]
    tool_bindings: dict[str, Any]
    anti_patterns: dict[str, Any]
    evidence_lattice: dict[str, Any]
    state_lexicon: dict[str, Any]
    psm_schema: dict[str, Any]
    situation_policy_catalog: dict[str, Any] = field(default_factory=dict)

    capability_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    playbook_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    cluster_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    tool_to_capability: dict[str, str] = field(default_factory=dict)
    bindings_by_capability: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    bindings_by_semantic_action: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, base: Path | None = None) -> RuntimeArtifactBundle:
        root = base or runtime_dir()
        bundle = cls(
            manifest=_load_json(root / "manifest.json"),
            capability_graph=_load_yaml(root / "capability_graph.v1.yaml"),
            cluster_registry=_load_yaml(root / "cluster_registry.v1.yaml"),
            playbook_templates=_load_yaml(root / "playbook_templates.v1.yaml"),
            invariant_registry=_load_yaml(root / "invariant_registry.v1.yaml"),
            replan_registry=_load_yaml(root / "replan_registry.v1.yaml"),
            decision_heuristics=_load_yaml(root / "decision_heuristics.v1.yaml"),
            tool_bindings=_load_yaml(root / "tool_bindings.v1.yaml"),
            anti_patterns=_load_yaml(root / "anti_patterns.v1.yaml"),
            evidence_lattice=_load_yaml(root / "evidence_lattice.v1.yaml"),
            state_lexicon=_load_json(root / "state_lexicon.v1.json"),
            psm_schema=_load_json(root / "project_situation_model.schema.json"),
            situation_policy_catalog=_load_optional_yaml(root / "situation_policy_catalog.v1.yaml"),
        )
        bundle._index()
        return bundle

    def _index(self) -> None:
        for cap in self.capability_graph.get("capabilities", []):
            cid = cap.get("capability_id")
            if cid:
                self.capability_by_id[cid] = cap

        for pb in self.playbook_templates.get("playbooks", []):
            pid = pb.get("playbook_id")
            if pid:
                self.playbook_by_id[pid] = pb

        for cluster in self.cluster_registry.get("clusters", []):
            cid = cluster.get("cluster_id")
            if cid:
                self.cluster_by_id[cid] = cluster

        for binding in self.tool_bindings.get("bindings", []):
            cap = binding.get("capability")
            if cap:
                self.bindings_by_capability.setdefault(cap, []).append(binding)
            for action in binding.get("semantic_actions") or []:
                self.bindings_by_semantic_action[action] = binding
            for tool_spec in binding.get("tools") or []:
                tool_name = tool_spec.get("tool")
                if tool_name and cap:
                    self.tool_to_capability[tool_name] = cap


@lru_cache(maxsize=1)
def load_runtime_artifacts() -> RuntimeArtifactBundle:
    return RuntimeArtifactBundle.load()
