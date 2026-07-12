"""Coordination validation suite — harness and workflow spec tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

yaml = pytest.importorskip("yaml")

from coordination_validation.harness import ValidationHarness
from coordination_validation.workflows import all_workflow_ids, load_workflows, workflow_by_id


@pytest.mark.unit
def test_workflows_yaml_loads_fourteen_workflows() -> None:
    data = load_workflows()
    ids = all_workflow_ids()
    assert len(ids) == 14
    assert ids[0] == "CVW-01"
    assert ids[-1] == "CVW-14"
    for wf in data["workflows"]:
        assert wf.get("expected_capabilities")
        assert wf.get("expected_tools")
        assert wf.get("simulate_steps")


@pytest.mark.unit
def test_each_workflow_has_engineering_goal() -> None:
    for wid in all_workflow_ids():
        wf = workflow_by_id(wid)
        assert wf is not None
        assert wf.get("title")
        assert wf.get("engineering_goal")
        assert wf.get("modules")


@pytest.mark.unit
def test_cvw04_form_workflow_passes_simulate() -> None:
    harness = ValidationHarness()
    result = harness.run_workflow("CVW-04")
    assert result["metrics"]["success"] is True
    assert result["metrics"]["playbook_accuracy"] == 1.0
    assert result["metrics"]["unnecessary_tool_calls"] == 0
    decisions = result["decisions"]
    assert any(d["stop_reason"] == "playbook_complete" for d in decisions)


@pytest.mark.unit
def test_full_suite_runs_and_produces_report_shape() -> None:
    harness = ValidationHarness()
    report = harness.run_all(mode="simulate")
    assert report["suite_version"]
    assert report["mode"] == "simulate"
    assert len(report["workflows"]) == 14
    assert "summary" in report
    assert "coordination_score" in report
    cs = report["coordination_score"]
    assert "categories" in cs
    assert "composite" in cs
    assert "cluster_accuracy" in cs["categories"]
    for wf in report["workflows"]:
        m = wf["metrics"]
        assert "cluster_accuracy" in m
        assert "step_compilation_scope" in m
        assert m["step_compilation_scope"] == "simulate_host_driven_not_scored"
        assert m["step_compilation_accuracy"] is None
        assert "decisions" in wf
        assert "findings" in wf
        assert "psm_timeline" in wf


@pytest.mark.unit
def test_decision_records_include_coordinator_fields() -> None:
    harness = ValidationHarness()
    result = harness.run_workflow("CVW-04")
    for d in result["decisions"]:
        assert "cluster_id" in d
        assert "tool" in d
        if d["tool"] == "perception_probe_form":
            assert d["capability_id"] == "form_probe"


@pytest.mark.unit
def test_validation_runner_cli(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "run_coordination_validation.py"),
            "--workflow",
            "CVW-04",
            "--output",
            str(out),
        ],
        cwd=ROOT,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["workflows"][0]["workflow_id"] == "CVW-04"
