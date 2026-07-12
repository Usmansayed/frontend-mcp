"""Validators for coordination runtime artifact distillation."""

from __future__ import annotations

import re
from typing import Any

# Research state IDs: archetype.S##_... or global.Sxx...
RESEARCH_STATE_ID = re.compile(
    r"^(?:global|[a-z]+)\.S(?:\d{2}|xx)\.[a-z0-9_.]+$"
)

# Broader pattern for embedded state references in strings
RESEARCH_STATE_EMBED = re.compile(
    r"(?:global|[a-z]+)\.S(?:\d{2}|xx)\.[a-z0-9_.]+"
)


def is_research_state_id(value: str) -> bool:
    return bool(RESEARCH_STATE_ID.match(value.strip()))


def collect_strings(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """Return (json_path, string_value) pairs from nested structures."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            child = f"{path}.{key}" if path else str(key)
            out.extend(collect_strings(val, child))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            out.extend(collect_strings(val, f"{path}[{i}]"))
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def validate_no_research_states_in_control_flow(
    playbooks: dict[str, Any],
    *,
    allowed_fields: frozenset[str] = frozenset(),
) -> list[str]:
    """Ensure research state IDs never appear in playbook control-flow fields."""
    errors: list[str] = []
    control_roots = {"playbooks", "steps", "applies_to_clusters", "sequence_constraints"}
    for playbook in playbooks.get("playbooks", []):
        pb_id = playbook.get("playbook_id", "?")
        for path, value in collect_strings(playbook):
            top = path.split(".")[0].split("[")[0]
            if top in allowed_fields:
                continue
            if "recovery_map" in path or "global_recovery" in path:
                continue
            if RESEARCH_STATE_EMBED.search(value):
                errors.append(
                    f"playbook {pb_id}: research state ID in control field {path}: {value!r}"
                )
    return errors


def validate_playbook_capabilities_exist(
    playbooks: dict[str, Any],
    capability_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for playbook in playbooks.get("playbooks", []):
        pb_id = playbook.get("playbook_id", "?")
        for step in playbook.get("steps", []):
            cap = step.get("capability")
            if cap is None:
                if step.get("host_llm_only"):
                    continue
                if step.get("recovery_map_ref"):
                    continue
                errors.append(f"playbook {pb_id} step {step.get('step_id')}: missing capability")
                continue
            if cap not in capability_ids:
                errors.append(
                    f"playbook {pb_id} step {step.get('step_id')}: unknown capability {cap!r}"
                )
    return errors


def validate_cluster_playbooks_exist(
    cluster_registry: dict[str, Any],
    playbook_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for cluster in cluster_registry.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        pb = cluster.get("default_playbook")
        if pb and pb not in playbook_ids:
            errors.append(f"cluster {cid}: unknown default_playbook {pb!r}")
    return errors


def validate_tool_bindings_reference_capabilities(
    tool_bindings: dict[str, Any],
    capability_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for binding in tool_bindings.get("bindings", []):
        cap = binding.get("capability")
        ref = binding.get("tools_ref", "?")
        if cap and cap not in capability_ids:
            errors.append(f"tool_bindings {ref}: unknown capability {cap!r}")
    return errors


def validate_state_lexicon_telemetry_only(lexicon: dict[str, Any]) -> list[str]:
    """Lexicon may contain state IDs; ensure schema marks telemetry purpose."""
    if lexicon.get("telemetry_only") is not True:
        return ["state_lexicon must set telemetry_only: true"]
    if "control_flow" in lexicon:
        return ["state_lexicon must not define control_flow"]
    return []


def validate_cluster_members_telemetry(
    cluster_registry: dict[str, Any],
    state_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for cluster in cluster_registry.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        members = cluster.get("member_state_ids", [])
        for mid in members:
            if not is_research_state_id(mid):
                errors.append(f"cluster {cid}: invalid member_state_id format {mid!r}")
            elif mid not in state_ids:
                errors.append(f"cluster {cid}: unknown member_state_id {mid!r}")
    return errors


def extract_capability_ids(capability_graph: dict[str, Any]) -> set[str]:
    return {
        c["capability_id"]
        for c in capability_graph.get("capabilities", [])
        if "capability_id" in c
    }


def extract_playbook_ids(playbooks: dict[str, Any]) -> set[str]:
    return {p["playbook_id"] for p in playbooks.get("playbooks", []) if "playbook_id" in p}


def run_all_validations(
    *,
    playbooks: dict[str, Any],
    capability_graph: dict[str, Any],
    cluster_registry: dict[str, Any],
    tool_bindings: dict[str, Any],
    state_lexicon: dict[str, Any],
) -> list[str]:
    cap_ids = extract_capability_ids(capability_graph)
    pb_ids = extract_playbook_ids(playbooks)
    state_ids = set(state_lexicon.get("states", {}).keys())

    errors: list[str] = []
    errors.extend(validate_no_research_states_in_control_flow(playbooks))
    errors.extend(validate_playbook_capabilities_exist(playbooks, cap_ids))
    errors.extend(validate_cluster_playbooks_exist(cluster_registry, pb_ids))
    errors.extend(validate_tool_bindings_reference_capabilities(tool_bindings, cap_ids))
    errors.extend(validate_state_lexicon_telemetry_only(state_lexicon))
    errors.extend(validate_cluster_members_telemetry(cluster_registry, state_ids))
    return errors
