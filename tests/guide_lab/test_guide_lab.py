"""Guide Lab policy quizzes — isolated from production MCP."""
from __future__ import annotations

from navigation.guide_lab.policies import decide_arm_a, decide_arm_b
from navigation.guide_lab.runner import run_pack
from navigation.guide_lab.scoring import score_decision


def test_arm_a_tunnels_on_gate_next():
    case = {
        "class": "greenfield",
        "unpaid": ["inspiration", "component"],
        "gate": {"next_required_capability": "browser_observe"},
        # no backlog_top → fall through to gate.next
    }
    d = decide_arm_a(case)
    assert d["first_family"] == "observe"
    assert d["owed"] == ["observe"]


def test_arm_a_prefers_backlog_top_when_unpaid():
    case = {
        "class": "greenfield",
        "unpaid": ["inspiration", "component"],
        "gate": {"next_required_capability": "browser_observe"},
        "backlog_top": "inspiration",
    }
    d = decide_arm_a(case)
    assert d["owed"] == ["inspiration"]
    assert len(d["owed"]) == 1


def test_arm_b_greenfield_multi_owed():
    case = {
        "class": "greenfield",
        "unpaid": ["inspiration", "snapshot", "component"],
        "gate": {"next_required_capability": "browser_observe"},
        "backlog_top": "inspiration",
    }
    d = decide_arm_b(case)
    assert "inspiration" in d["owed"] or "snapshot" in d["owed"]
    assert "component" in d["owed"]
    assert len(d["owed"]) >= 2


def test_arm_b_mockup_prefers_snapshot_not_inspiration():
    case = {
        "class": "mockup",
        "unpaid": ["inspiration", "snapshot", "observe"],
        "gate": {"next_required_capability": "inspiration_workflow"},
        "backlog_top": "inspiration",
    }
    d = decide_arm_b(case)
    assert d["first_family"] == "snapshot"
    assert "inspiration" not in d["owed"]


def test_arm_b_polish_skips_foundation():
    case = {
        "class": "polish",
        "unpaid": ["observe", "verify", "component"],
        "gate": {"next_required_capability": "component_select"},
        "backlog_top": "component",
    }
    d = decide_arm_b(case)
    assert d["owed"] == ["observe", "verify"]
    assert d["first_family"] == "observe"


def test_score_must_not():
    gold = {"owed": ["observe"], "first_family": "observe", "must_not": ["seo"]}
    bad = {"owed": ["seo"], "first_family": "seo"}
    assert score_decision(gold, bad)["pass"] is False


def test_full_pack_b_beats_a():
    summary = run_pack()
    assert summary["n_cases"] >= 80
    assert summary["B_accuracy"] > summary["A_accuracy"]
    assert summary["winner"] == "B"
    assert summary["B_accuracy"] == 1.0
