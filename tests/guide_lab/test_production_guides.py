"""Production-like contracts for Option C dual agent guides."""
from __future__ import annotations

from pathlib import Path

import pytest

from navigation.guide_lab.policies import decide_arm_b
from navigation.guide_lab.runner import run_pack
from navigation.mcp.methodology_resources import METHODOLOGY_RESOURCES
from navigation.mcp.resources import read_resource

ROOT = Path(__file__).resolve().parents[2]
GUIDE_URIS = [
    "perception://guide/scoreboard",
    "perception://guide/greenfield",
    "perception://guide/redesign",
    "perception://guide/feature",
    "perception://guide/hotfix",
    "perception://guide/forms",
    "perception://guide/hard-fails",
    "perception://guide/right-sizing",
]

ALWAYS_ON = [
    ROOT / ".cursor" / "rules" / "frontend-perception-mcp.mdc",
    ROOT / "src" / "navigation" / "cli" / "data" / "frontend_mcp_agent_rule.md",
]


@pytest.mark.unit
def test_all_guide_uris_registered_and_structured() -> None:
    for uri in GUIDE_URIS:
        assert uri in METHODOLOGY_RESOURCES
        mime, text, is_blob = read_resource(uri)
        assert mime == "text/markdown"
        assert is_blob is False
        assert "Use when" in text
        assert "Implementation boundary" in text
        assert "Done condition" in text or "Done" in text


@pytest.mark.unit
def test_hard_fails_card_covers_p0_failures() -> None:
    _, text, _ = read_resource("perception://guide/hard-fails")
    lowered = text.lower()
    for needle in (
        "tunnel",
        "mockup",
        "snapshot",
        "soft text",
        "claim",
        "seo",
        "parallel",
        "end-of-task",
    ):
        assert needle in lowered, f"hard-fails missing {needle!r}"


@pytest.mark.unit
def test_redesign_card_prefers_snapshot_over_inspiration() -> None:
    _, text, _ = read_resource("perception://guide/redesign")
    lowered = text.lower()
    assert "snapshot" in lowered
    assert "mockup" in lowered
    assert "inspiration" in lowered


@pytest.mark.unit
def test_hotfix_card_has_sticky_design_exception() -> None:
    _, text, _ = read_resource("perception://guide/hotfix")
    lowered = text.lower()
    assert "sticky" in lowered or "design_driven" in lowered
    assert "overlay" in lowered or "wash" in lowered or "opacity" in lowered


@pytest.mark.unit
def test_always_on_rule_is_short_and_binding() -> None:
    for path in ALWAYS_ON:
        text = path.read_text(encoding="utf-8")
        words = len(text.split())
        assert words <= 550, f"{path} too long: {words} words"
        lowered = text.lower()
        for needle in (
            "unpaid",
            "owed",
            "gate",
            "episode_card",
            "perception://guide/",
            "data.verified",
            "tunnel",
        ):
            assert needle in lowered, f"{path.name} missing {needle!r}"


@pytest.mark.unit
def test_always_on_rules_stay_in_sync() -> None:
    a = ALWAYS_ON[0].read_text(encoding="utf-8")
    b = ALWAYS_ON[1].read_text(encoding="utf-8")
    # Strip YAML frontmatter from mdc
    if a.startswith("---"):
        a = a.split("---", 2)[-1]
    for marker in (
        "Scoreboard loop",
        "Hard fails",
        "Done ladder",
        "perception://guide/greenfield",
        "perception://guide/hard-fails",
    ):
        assert marker in a and marker in b


@pytest.mark.unit
def test_agent_coordination_points_at_guide_cards() -> None:
    _, text, _ = read_resource("perception://agent-coordination")
    assert "perception://guide/" in text


@pytest.mark.unit
def test_empty_unpaid_uses_class_minimum_path() -> None:
    d = decide_arm_b(
        {
            "class": "feature",
            "unpaid": [],
            "gate": {"next_required_capability": "browser_verify"},
        }
    )
    assert d["owed"] == ["observe", "verify"]
    assert d["first_family"] == "observe"


@pytest.mark.unit
def test_sticky_polish_keeps_ship_family() -> None:
    d = decide_arm_b(
        {
            "class": "polish",
            "sticky_design": True,
            "unpaid": ["observe", "verify", "design_review"],
            "gate": {"next_required_capability": "design_review"},
            "backlog_top": "design_review",
        }
    )
    assert "design_review" in d["owed"]
    assert d["first_family"] == "observe"


@pytest.mark.unit
def test_seo_only_unpaid_does_not_owe_seo() -> None:
    d = decide_arm_b(
        {
            "class": "feature",
            "unpaid": ["seo"],
            "gate": {"next_required_capability": "browser_observe"},
            "backlog_top": "seo",
        }
    )
    assert "seo" not in d["owed"]
    assert "observe" in d["owed"]


@pytest.mark.unit
def test_full_production_pack_b_near_perfect() -> None:
    summary = run_pack()
    assert summary["n_cases"] >= 80
    assert summary["winner"] == "B"
    assert summary["B_accuracy"] == 1.0
    assert summary["tallies"]["B"]["pass"] == summary["n_cases"]
    prod = [r for r in summary["rows"] if str(r["id"]).startswith("P") and r["arm"] == "B"]
    assert len(prod) >= 30
    assert all(r["pass"] for r in prod)
