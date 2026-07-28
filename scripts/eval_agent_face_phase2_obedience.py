"""Phase 2 obedience: bootstrap card routing for all 6 A/B intents (no full UI)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.coordinator_card import (  # noqa: E402
    build_agent_face_card,
)

CASES = [
    {
        "id": "forms",
        "intent": "Verify /forms/validation: invalid then valid submit. Use Frontend MCP.",
        "expect_class": "forms",
        "expect_next_prefix": "perception_probe_form",
        "expect_depth_in": {"light", "standard"},
        "forbid_inspiration": True,
    },
    {
        "id": "hotfix",
        "intent": "Fix overlapping CTA on homepage — surgical CSS. Use Frontend MCP.",
        "expect_class": "hotfix",
        "expect_next_prefix": "perception_navigate_and_observe",
        "expect_depth_in": {"light", "standard"},
        "forbid_inspiration": True,
    },
    {
        "id": "greenfield",
        "intent": "New SaaS landing with strong brand hero. Use Frontend MCP before coding.",
        "expect_class": "greenfield",
        "expect_next_prefix": "perception_inspiration_collect",
        "expect_depth_in": {"full"},
        "forbid_inspiration": False,
    },
    {
        "id": "redesign",
        "intent": "Redesign dashboard to match a mockup — measure first. Use Frontend MCP.",
        "expect_class": "redesign",
        "expect_next_in": {
            "perception_navigate_and_observe",
            "perception_build_design_snapshot",
        },
        "expect_depth_in": {"full"},
        "forbid_inspiration": True,
    },
    {
        "id": "feature",
        "intent": "Add a settings toggle to an existing page. Use Frontend MCP.",
        "expect_class": "feature",
        "expect_next_prefix": "perception_navigate_and_observe",
        "expect_depth_in": {"standard", "full"},
        "forbid_inspiration": True,
        "strategy_extra": {
            "task_scope": "feature_incremental",
            "influence_level": "balanced",
        },
    },
    {
        "id": "polish",
        "intent": "Tighten spacing on the navbar only. Use Frontend MCP.",
        "expect_class": "hotfix",
        "expect_next_prefix": "perception_navigate_and_observe",
        "expect_depth_in": {"light", "standard"},
        "forbid_inspiration": True,
        "strategy_extra": {
            "task_scope": "design_driven",
            "right_sizing": {"tier": "polish"},
            "influence_level": "structural",
        },
    },
]


def _base_strategy(case: dict) -> dict:
    extra = dict(case.get("strategy_extra") or {})
    unpaid = []
    if case["id"] == "greenfield":
        unpaid = [
            {"family": "inspiration", "suggested": "perception_inspiration_collect"},
            {"family": "visual_feedback", "suggested": "perception_visual_feedback"},
            {"family": "observe", "suggested": "perception_navigate_and_observe"},
        ]
    elif case["id"] == "redesign":
        unpaid = [
            {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
            {"family": "observe", "suggested": "perception_navigate_and_observe"},
            {"family": "visual_feedback", "suggested": "perception_visual_feedback"},
        ]
    elif case["id"] == "feature":
        unpaid = [
            {"family": "inspiration", "suggested": "perception_inspiration_collect"},
            {"family": "observe", "suggested": "perception_navigate_and_observe"},
            {"family": "verify", "suggested": "perception_verify"},
        ]
    return {
        "intent": case["intent"],
        "verification_status": "pending",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "component_search_plan",
            "prohibited_actions": ["claim_complete"],
            "ship_council_required": case["id"] == "greenfield",
        },
        "episode_portfolio": {"paid": [], "unpaid": unpaid},
        "recommended_resource": "perception://getting-started",
        **extra,
    }


def main() -> int:
    rows = []
    ok = True
    for case in CASES:
        face = build_agent_face_card(episode_id=f"ab_{case['id']}", strategy=_base_strategy(case))
        cls_ok = face["class"] == case["expect_class"]
        if "expect_next_in" in case:
            next_ok = face["next"] in case["expect_next_in"]
        else:
            next_ok = str(face["next"]).startswith(case["expect_next_prefix"])
        depth_ok = face["depth"] in case["expect_depth_in"]
        insp_ok = True
        if case.get("forbid_inspiration"):
            insp_ok = face["next"] != "perception_inspiration_collect"
            insp_ok = insp_ok and all(o["family"] != "inspiration" for o in face["owed"])
        claim_ok = face["claim_ok"] is False  # pending verify
        passed = all([cls_ok, next_ok, depth_ok, insp_ok, claim_ok])
        ok = ok and passed
        rows.append(
            {
                "id": case["id"],
                "passed": passed,
                "class": face["class"],
                "depth": face["depth"],
                "next": face["next"],
                "owed": [o["family"] for o in face["owed"]],
                "claim_ok": face["claim_ok"],
                "checks": {
                    "class": cls_ok,
                    "next": next_ok,
                    "depth": depth_ok,
                    "no_inspiration": insp_ok,
                    "claim_blocked": claim_ok,
                },
            }
        )
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case['id']}: class={face['class']} depth={face['depth']} next={face['next']}")

    out = ROOT / "docs" / "research" / "agent_face_phase2_obedience_board.json"
    payload = {"ok": ok, "passed": sum(1 for r in rows if r["passed"]), "total": len(rows), "rows": rows}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"BOARD: {'PASS' if ok else 'FAIL'} ({payload['passed']}/{payload['total']})")
    print(f"Wrote {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
