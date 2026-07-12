#!/usr/bin/env python3
"""P0 distillation build — research corpus → runtime artifacts (R0–R11).

Does not modify MCP behavior. Produces validated YAML/JSON under coordination_layer/runtime/.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DISTILLATION_DIR = Path(__file__).resolve().parent
if str(_DISTILLATION_DIR) not in sys.path:
    sys.path.insert(0, str(_DISTILLATION_DIR))

from validators import run_all_validations

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required for distillation build. Install with: pip install pyyaml"
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
COORD = ROOT / "coordination_layer"
RESEARCH = COORD / "research"
SOURCES = COORD / "distillation" / "sources"
SCHEMAS = COORD / "distillation" / "schemas"
RUNTIME = COORD / "runtime"
STATES_DIR = RESEARCH / "state_space" / "states"
CLUSTER_INDEX = RESEARCH / "state_space" / "abstracted" / "cluster_index.md"
STATE_GRAPH_INDEX = RESEARCH / "state_space" / "state_graph_index.json"

BUNDLE_VERSION = "1.0.0"

SOURCE_ARTIFACTS = {
    "capability_graph.v1.yaml": "capability_graph.v1.yaml",
    "cluster_registry.v1.yaml": "cluster_registry.v1.yaml",
    "playbook_templates.v1.yaml": "playbook_templates.v1.yaml",
    "invariant_registry.v1.yaml": "invariant_registry.v1.yaml",
    "replan_registry.v1.yaml": "replan_registry.v1.yaml",
    "decision_heuristics.v1.yaml": "decision_heuristics.v1.yaml",
    "tool_bindings.v1.yaml": "tool_bindings.v1.yaml",
    "anti_patterns.v1.yaml": "anti_patterns.v1.yaml",
    "evidence_lattice.v1.yaml": "evidence_lattice.v1.yaml",
}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def expand_brace_member(token: str) -> list[str]:
    """Expand archetype.S##.path.{a, b, c} into full state IDs."""
    token = token.strip().rstrip(",")
    if not token:
        return []
    brace_start = token.find("{")
    if brace_start == -1:
        return [token]
    prefix = token[:brace_start]
    inner = token[brace_start + 1 : token.rfind("}")]
    suffixes = [s.strip() for s in inner.split(",")]
    return [f"{prefix}{suffix}" for suffix in suffixes if suffix]


def preprocess_members_line(raw: str) -> str:
    """Normalize cluster_index Members line before tokenization."""
    raw = raw.strip()
    # marketing.S12.framework_migration.{..., rollback} → migration.rollback
    arrow_match = re.search(
        r"(\w+\.S\d+\.[\w]+)\.\{([^}]+)\}\s*→\s*([\w.]+)",
        raw,
    )
    if arrow_match:
        archetype_stage = arrow_match.group(1)  # marketing.S12.framework_migration
        inner = arrow_match.group(2)
        alias_path = arrow_match.group(3)  # migration.rollback
        stage_parts = archetype_stage.split(".")
        archetype = stage_parts[0]
        stage = stage_parts[1] if len(stage_parts) > 1 else "S12"
        parts = [p.strip() for p in inner.split(",")]
        expanded = [f"{archetype_stage}.{p}" for p in parts if p and p != "rollback"]
        expanded.append(f"{archetype}.{stage}.{alias_path}")
        replacement = ", ".join(expanded)
        raw = raw[: arrow_match.start()] + replacement + raw[arrow_match.end() :]
    return raw


def tokenize_members(raw: str) -> list[str]:
    """Split members line on commas outside braces."""
    raw = preprocess_members_line(raw)
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in raw:
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            tokens.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        tokens.append(tail)
    return tokens


def expand_member_token(token: str, all_state_ids: set[str]) -> list[str]:
    token = token.strip().rstrip(",")
    if not token:
        return []
    if "global.Sxx" in token:
        return sorted(s for s in all_state_ids if s.startswith("global.Sxx."))
    if "{" in token:
        return expand_brace_member(token)
    return [token]


def parse_cluster_index_members(
    text: str,
    all_state_ids: set[str],
) -> dict[str, list[str]]:
    """Parse cluster_index.md Members lines into cluster_id → state_id list."""
    mapping: dict[str, list[str]] = {}
    current_cluster: str | None = None
    for line in text.splitlines():
        m_header = re.match(r"^### (cluster\.[a-z0-9_.]+)", line)
        if m_header:
            current_cluster = m_header.group(1)
            mapping.setdefault(current_cluster, [])
            continue
        m_members = re.match(r"^- \*\*Members:\*\* (.+)$", line)
        if m_members and current_cluster:
            raw = m_members.group(1)
            members: list[str] = []
            for token in tokenize_members(raw):
                members.extend(expand_member_token(token, all_state_ids))
            mapping[current_cluster].extend(members)
    return mapping


def load_research_states() -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for path in sorted(STATES_DIR.glob("*.yaml")):
        data = load_yaml(path)
        if not data or "state_id" not in data:
            continue
        states[data["state_id"]] = data
    return states


def infer_cluster_for_state(
    state_id: str,
    cluster_members: dict[str, list[str]],
) -> str | None:
    for cluster_id, members in cluster_members.items():
        if state_id in members:
            return cluster_id
    return None


def build_state_lexicon(
    states: dict[str, dict[str, Any]],
    cluster_members: dict[str, list[str]],
) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for state_id, data in sorted(states.items()):
        cluster_id = data.get("parent_cluster") or infer_cluster_for_state(
            state_id, cluster_members
        )
        entries[state_id] = {
            "leaf_hint": state_id,
            "cluster_id": cluster_id,
            "lifecycle_stage": data.get("lifecycle_stage"),
            "situation_class": data.get("situation_class"),
            "project_archetype": data.get("project_archetype"),
            "mcp_ready": data.get("mcp_ready", True),
            "forest_id": data.get("forest_id"),
            "telemetry_only": True,
        }
    return {
        "schema_version": "1.0",
        "telemetry_only": True,
        "description": (
            "Research state lexicon for debugging, analytics, and leaf_hint telemetry. "
            "MUST NOT influence planning or routing."
        ),
        "generated_from": "research/state_space/states/*.yaml",
        "state_count": len(entries),
        "states": entries,
    }


def enrich_cluster_registry(
    base: dict[str, Any],
    cluster_members: dict[str, list[str]],
) -> dict[str, Any]:
    enriched = dict(base)
    clusters_out = []
    by_id = {c["cluster_id"]: dict(c) for c in base.get("clusters", [])}

    for cluster_id, members in sorted(cluster_members.items()):
        row = by_id.get(cluster_id, {"cluster_id": cluster_id})
        row["member_state_ids"] = sorted(members)
        row["member_count"] = len(members)
        row["member_state_ids_note"] = "Telemetry only — never control flow"
        clusters_out.append(row)

    # Preserve clusters defined in source without members in index
    seen = {c["cluster_id"] for c in clusters_out}
    for cluster_id, row in by_id.items():
        if cluster_id not in seen:
            row.setdefault("member_state_ids", [])
            row.setdefault("member_count", 0)
            clusters_out.append(row)

    enriched["clusters"] = sorted(clusters_out, key=lambda c: c["cluster_id"])
    enriched["cluster_count"] = len(clusters_out)
    return enriched


def count_capabilities(graph: dict[str, Any]) -> dict[str, int]:
    caps = graph.get("capabilities", [])
    t1 = sum(1 for c in caps if c.get("tier") == "T1_global")
    mcp_false = sum(1 for c in caps if c.get("risk", {}).get("mcp_ready") is False)
    return {
        "T1": t1,
        "total": len(caps),
        "edges": len(graph.get("edges", [])),
        "mcp_ready_false": mcp_false,
    }


def build_manifest(artifact_paths: dict[str, Path], capability_counts: dict[str, int]) -> dict[str, Any]:
    artifacts_meta = {}
    for name, path in sorted(artifact_paths.items()):
        artifacts_meta[name] = {
            "path": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }

    index = load_json(STATE_GRAPH_INDEX) if STATE_GRAPH_INDEX.exists() else {}
    counts = index.get("counts", {})

    return {
        "bundle_version": BUNDLE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_git_sha": git_sha(),
        "research_state_count": counts.get("total_states", len(list(STATES_DIR.glob("*.yaml")))),
        "architecture_status": "frozen",
        "principles": [
            "capabilities_not_modules",
            "host_llm_sole_reasoner",
            "research_states_never_control_flow",
            "capability_ids_stable_tools_via_r8",
        ],
        "artifacts": artifacts_meta,
        "capability_counts": capability_counts,
    }


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    print(f"Distillation build — root: {ROOT}")
    RUNTIME.mkdir(parents=True, exist_ok=True)

    states = load_research_states()
    if not states:
        print("ERROR: no research states found", file=sys.stderr)
        return 1

    all_state_ids = set(states.keys())
    cluster_members = parse_cluster_index_members(
        CLUSTER_INDEX.read_text(encoding="utf-8"),
        all_state_ids,
    )

    state_lexicon = build_state_lexicon(states, cluster_members)
    cluster_registry = enrich_cluster_registry(
        load_yaml(SOURCES / "cluster_registry.v1.yaml"),
        cluster_members,
    )

    copied: dict[str, Any] = {}
    for src_name, dst_name in SOURCE_ARTIFACTS.items():
        copied[dst_name] = load_yaml(SOURCES / src_name)

    playbooks = copied["playbook_templates.v1.yaml"]
    capability_graph = copied["capability_graph.v1.yaml"]
    tool_bindings = copied["tool_bindings.v1.yaml"]

    errors = run_all_validations(
        playbooks=playbooks,
        capability_graph=capability_graph,
        cluster_registry=cluster_registry,
        tool_bindings=tool_bindings,
        state_lexicon=state_lexicon,
    )
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    artifact_paths: dict[str, Path] = {}

    # R1 schema
    schema_src = SCHEMAS / "project_situation_model.v1.json"
    schema_dst = RUNTIME / "project_situation_model.schema.json"
    schema_dst.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    artifact_paths["project_situation_model.schema"] = schema_dst

    # R2–R10 from sources + enriched cluster registry
    for dst_name, data in copied.items():
        out = RUNTIME / dst_name
        dump_yaml(data, out)
        artifact_paths[dst_name.replace(".v1.yaml", "")] = out

    dump_yaml(cluster_registry, RUNTIME / "cluster_registry.v1.yaml")
    artifact_paths["cluster_registry"] = RUNTIME / "cluster_registry.v1.yaml"

    # R11 state lexicon
    lexicon_path = RUNTIME / "state_lexicon.v1.json"
    dump_json(state_lexicon, lexicon_path)
    artifact_paths["state_lexicon"] = lexicon_path

    cap_counts = count_capabilities(capability_graph)
    manifest = build_manifest(artifact_paths, cap_counts)
    manifest_path = RUNTIME / "manifest.json"
    dump_json(manifest, manifest_path)

    total_bytes = sum(p.stat().st_size for p in artifact_paths.values())
    print(f"OK: {len(artifact_paths)} artifacts -> {RUNTIME}")
    print(f"    states: {state_lexicon['state_count']}, T1 capabilities: {cap_counts['T1']}")
    print(f"    bundle size: {total_bytes:,} bytes")
    if total_bytes > 500_000:
        print(f"WARN: bundle exceeds 500KB target ({total_bytes:,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
