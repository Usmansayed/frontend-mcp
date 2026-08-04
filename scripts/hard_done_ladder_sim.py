"""Hard sim: design episode survives verify-fail without clearing claim-complete."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.coordination_intelligence.planning.cluster_resolver import ClusterResolver
from navigation.coordination_intelligence.planning.engineering_strategy import (
    compile_engineering_strategy,
)
from navigation.coordination_intelligence.planning.section_checklist import (
    seed_section_checklist_from_regions,
)
from navigation.coordination_intelligence.psm.normalize import apply_envelope
from navigation.coordination_intelligence.service import CoordinationIntelligenceService


def main() -> int:
    load_runtime_artifacts.cache_clear()
    bundle = load_runtime_artifacts()
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_hard_sim",
        intent="build a new SaaS analytics dashboard from scratch with sidebar KPIs",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    print("1. start scope=", psm.briefing.engineering_strategy.get("task_scope"))
    print("   sticky=", psm.episode.retry_counters.get("episode_design_scope"))

    # Soft page verify pass (lazy agent).
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {"verified": True, "reasons": []},
        },
        bundle,
    )
    psm.episode.retry_counters["last_capability"] = "browser_verify"
    ClusterResolver(bundle).resolve(psm)
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    print("2. soft verify pass cluster=", psm.situation.cluster_id)
    print("   scope=", strategy["task_scope"], "claim blocked=", "claim_complete" in (
        strategy["implementation_gate"].get("prohibited_actions") or []
    ))

    # Snapshot seeds checklist (post-draft).
    psm.artifacts.snapshot_id = "snap_hard"
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "label": "sidebar", "rect": {"w": 230, "h": 800}},
            {"role": "main", "rect": {"w": 1000, "h": 800}},
            {"role": "header", "rect": {"w": 1000, "h": 56}},
        ],
    )
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    gate = strategy["implementation_gate"]
    print("3. after snapshot section_req=", gate.get("section_checklist_required"))
    host = (strategy.get("host_action") or "").encode("ascii", "replace").decode("ascii")
    print("   host=", host[:120])
    assert gate.get("section_checklist_required") is True
    assert "claim_complete" in gate["prohibited_actions"]

    # Failed section verify — previously collapsed to debug and cleared claim gate.
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {
                "verified": False,
                "section_id": "aside:0",
                "reasons": ["js assertion failed: aside"],
            },
        },
        bundle,
    )
    psm.episode.retry_counters["last_capability"] = "browser_verify"
    psm.episode.retry_counters["last_tool"] = "perception_verify"
    ClusterResolver(bundle).resolve(psm)
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    gate = strategy["implementation_gate"]
    host = (strategy.get("host_action") or "").encode("ascii", "replace").decode("ascii")
    print("4. after VERIFY FAIL cluster=", psm.situation.cluster_id)
    print("   scope=", strategy["task_scope"], "influence=", strategy["influence_level"])
    print("   section_req=", gate.get("section_checklist_required"))
    print("   ship_req=", gate.get("ship_council_required"))
    print("   prohibited=", gate.get("prohibited_actions"))
    print("   host=", host[:140])
    print("   stops=", strategy.get("stop_conditions"))

    ok = (
        strategy["task_scope"] == "design_driven"
        and gate.get("section_checklist_required") is True
        and "claim_complete" in (gate.get("prohibited_actions") or [])
        and "SECTION CHECKLIST" in (strategy.get("host_action") or "")
        and not any("verify_passed_sufficient" in s for s in strategy.get("stop_conditions") or [])
    )
    if not ok:
        print("FAIL: design episode collapsed or claim-complete slipped")
        return 1
    print("PASS: verify-fail did not clear Done ladder / claim_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
