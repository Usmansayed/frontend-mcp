"""P0 distillation — runtime artifact validation (unit tests)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "coordination_layer" / "runtime"
BUILD = ROOT / "coordination_layer" / "distillation" / "build.py"
RESEARCH_STATE_ID = re.compile(r"(?:global|[a-z]+)\.S(?:\d{2}|xx)\.[a-z0-9_.]+")

yaml = pytest.importorskip("yaml")


def _load_json(name: str) -> dict:
    return json.loads((RUNTIME / name).read_text(encoding="utf-8"))


def _load_yaml(name: str) -> dict:
    with (RUNTIME / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.mark.unit
def test_runtime_manifest_checksums_match_files() -> None:
    manifest = _load_json("manifest.json")
    for _key, meta in manifest["artifacts"].items():
        path = RUNTIME / meta["path"]
        assert path.exists(), f"missing artifact {meta['path']}"
        assert _sha256(path) == meta["sha256"], f"checksum drift: {meta['path']}"


@pytest.mark.unit
def test_research_states_never_in_playbook_control_flow() -> None:
    playbooks = _load_yaml("playbook_templates.v1.yaml")
    for playbook in playbooks["playbooks"]:
        pb_id = playbook["playbook_id"]
        for step in playbook.get("steps", []):
            for field in ("semantic_action", "capability", "step_id"):
                val = step.get(field)
                if isinstance(val, str) and RESEARCH_STATE_ID.search(val):
                    pytest.fail(f"{pb_id}: research state in step.{field}: {val}")
        for cluster in playbook.get("applies_to_clusters", []):
            assert cluster.startswith("cluster."), f"{pb_id}: non-cluster routing ref {cluster}"


@pytest.mark.unit
def test_state_lexicon_telemetry_only() -> None:
    lexicon = _load_json("state_lexicon.v1.json")
    assert lexicon["telemetry_only"] is True
    assert lexicon["state_count"] == 150
    assert len(lexicon["states"]) == 150
    for state_id, entry in lexicon["states"].items():
        assert entry["telemetry_only"] is True
        assert entry["leaf_hint"] == state_id


@pytest.mark.unit
def test_capability_graph_is_public_api_shape() -> None:
    graph = _load_yaml("capability_graph.v1.yaml")
    cap_ids = {c["capability_id"] for c in graph["capabilities"]}
    assert len(cap_ids) == 32
    assert graph["design_principles"]
    for cap in graph["capabilities"]:
        assert cap["tier"] == "T1_global"
        assert "implements" in cap
        assert cap["capability_id"] in cap_ids


@pytest.mark.unit
def test_playbook_capabilities_exist_in_graph() -> None:
    graph = _load_yaml("capability_graph.v1.yaml")
    playbooks = _load_yaml("playbook_templates.v1.yaml")
    cap_ids = {c["capability_id"] for c in graph["capabilities"]}
    for playbook in playbooks["playbooks"]:
        for step in playbook.get("steps", []):
            cap = step.get("capability")
            if cap is None:
                continue
            assert cap in cap_ids, f"{playbook['playbook_id']}: missing {cap}"


@pytest.mark.unit
def test_psm_schema_includes_capability_posture() -> None:
    schema = _load_json("project_situation_model.schema.json")
    situation_props = schema["properties"]["situation"]["properties"]
    assert "capability_posture" in situation_props
    assert "leaf_hint" in situation_props
    leaf_hint = situation_props["leaf_hint"]
    assert "telemetry" in leaf_hint.get("description", "").lower()


@pytest.mark.unit
def test_cluster_registry_uses_cluster_ids_only_for_routing() -> None:
    registry = _load_yaml("cluster_registry.v1.yaml")
    for cluster in registry["clusters"]:
        assert cluster["cluster_id"].startswith("cluster.")
        for mid in cluster.get("member_state_ids", []):
            assert RESEARCH_STATE_ID.match(mid), f"bad member id: {mid}"


@pytest.mark.unit
def test_distillation_build_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.unit
def test_runtime_bundle_under_size_budget() -> None:
    manifest = _load_json("manifest.json")
    total = sum(m["bytes"] for m in manifest["artifacts"].values())
    assert total < 500_000, f"bundle too large: {total} bytes"
