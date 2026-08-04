"""Ship Council — unit and integration tests."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel
from navigation.coordination_intelligence.planning.decision_ledger import (
    apply_dispositions,
    load_ledger,
    validate_accept_reason,
)
from navigation.coordination_intelligence.planning.ship_council import (
    MAX_CHALLENGES,
    build_ship_council,
    compute_roi_score,
    episode_needs_ship_council,
    ship_council_hint,
    should_recommend_ship_mode,
    should_skip_ship_council,
)
from navigation.coordination_intelligence.psm.normalize import apply_envelope
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.mcp.design_intelligence_handlers import handle_design_review
from navigation.mcp.resources import list_resources, read_resource
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

DASHBOARD_FIXTURE = {
    "url": "http://localhost:5173/dashboard",
    "layout": {
        "viewport": {"width": 1280, "height": 720},
        "document_size": {"width": 2000, "height": 900},
        "visual_insights": {
            "issues": [{"kind": "horizontal_overflow", "severity": "blocking", "detail": "scrollWidth=2000"}],
            "blocking": ["horizontal_overflow"],
            "boxes": [{"x": 0, "y": 0, "w": 100, "h": 40}] * 45,
        },
        "overflow_issues": [{"kind": "horizontal_overflow", "severity": "blocking"}],
        "regions": [
            {"role": "sidebar", "label": "nav", "position": "static", "width_ratio": 0.18},
            {"role": "main", "label": "content", "centered": True, "width_ratio": 0.62, "layout_pattern": "marketing_centered"},
            {"role": "section", "label": "kpi"},
            {"role": "section", "label": "kpi"},
            {"role": "section", "label": "kpi"},
            {"role": "section", "label": "chart"},
            {"role": "section", "label": "table"},
        ],
    },
    "hierarchy": {
        "prominence_scores": [
            {"score": 0.51, "label": "revenue"},
            {"score": 0.50, "label": "users"},
            {"score": 0.52, "label": "churn"},
            {"score": 0.49, "label": "mrr"},
        ],
    },
    "colors": {
        "token_backed_ratio": 0.22,
        "raw_color_count": 18,
    },
    "design_tokens": {},
}

STRUCTURAL_STRATEGY = {
    "influence_level": "structural",
    "task_scope": "design_driven",
    "unresolved_decisions": [
        {"decision_id": "layout_shell", "impact_weight": 0.9},
    ],
    "implementation_gate": {"state": "ready"},
}

MINIMAL_STRATEGY = {
    "influence_level": "minimal",
    "task_scope": "hotfix",
    "unresolved_decisions": [],
    "implementation_gate": {"state": "maintenance"},
}


def _dashboard_snapshot() -> DesignSnapshot:
    return DesignSnapshot.from_dict(DASHBOARD_FIXTURE)


def _structural_psm(*, verify_passed: bool = True) -> ProjectSituationModel:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_test"
    psm.episode.verification_status = "passed" if verify_passed else "pending"
    psm.episode.intent_stack.append(
        type("F", (), {"intent": "build a new SaaS analytics dashboard", "pushed_at": "t"})()
    )
    from navigation.coordination_intelligence.models import IntentFrame, _utc_now

    psm.episode.intent_stack = [
        IntentFrame(intent="build a new SaaS analytics dashboard", pushed_at=_utc_now()),
    ]
    psm.situation.situation_class = "inspiration_needed"
    psm.situation.lifecycle_stage = "S05_implementation"
    return psm


@pytest.mark.unit
def test_validate_accept_reason_rejects_hollow() -> None:
    ok, _ = validate_accept_reason("Looks fine.")
    assert ok is False
    ok, _ = validate_accept_reason(
        "Sidebar is intentionally non-sticky because short pages avoid losing horizontal space on 13-inch laptops."
    )
    assert ok is True


@pytest.mark.unit
def test_dispositions_update_ledger_stats() -> None:
    psm = ProjectSituationModel()
    ledger = load_ledger(psm)
    applied, rejected = apply_dispositions(
        ledger,
        [
            {
                "signal": "nav_not_sticky",
                "disposition": "accepted",
                "reason": "Optimized for short pages on 13-inch laptops with limited horizontal space.",
            },
            {"signal": "equal_weight_kpi_cluster", "disposition": "revised"},
        ],
    )
    assert len(applied) == 2
    assert len(rejected) == 0
    assert ledger["session_stats"]["accepted"] == 1
    assert ledger["session_stats"]["revised"] == 1


@pytest.mark.unit
def test_dispositions_reject_hollow_accept() -> None:
    ledger = {"entries": {}, "session_stats": {}}
    _, rejected = apply_dispositions(
        ledger,
        [{"signal": "nav_not_sticky", "disposition": "accepted", "reason": "Looks fine."}],
    )
    assert len(rejected) == 1


@pytest.mark.unit
def test_roi_score_varies_with_evidence_not_fixed_template() -> None:
    psm = _structural_psm()
    low = compute_roi_score(
        severity="major",
        strategy=STRUCTURAL_STRATEGY,
        psm=psm,
        specdiff_magnitude=0.3,
        visual_improvement=0.88,
        signal="nav_not_sticky",
    )
    high = compute_roi_score(
        severity="major",
        strategy=STRUCTURAL_STRATEGY,
        psm=psm,
        specdiff_magnitude=0.95,
        visual_improvement=0.92,
        signal="equal_weight_kpi_cluster",
    )
    assert high > low
    assert high != 0.95
    assert low != 0.89


# Live Design Snapshot Engine shape — role/rect only, font-size prominence, boxes.
LIVE_SHAPED_DASHBOARD = {
    "url": "http://localhost:5173/dashboard",
    "layout": {
        "viewport": {"width": 1280, "height": 720},
        "document_size": {"width": 1280, "height": 1400},
        "visual_insights": {
            "issues": [],
            "blocking": [],
            "element_boxes": [
                {"x": 220, "y": 80, "w": 240, "h": 110, "tag": "div", "classes": ["card"]},
                {"x": 480, "y": 80, "w": 240, "h": 110, "tag": "div", "classes": ["card"]},
                {"x": 740, "y": 80, "w": 240, "h": 110, "tag": "div", "classes": ["card"]},
                {"x": 1000, "y": 80, "w": 240, "h": 110, "tag": "div", "classes": ["card"]},
            ],
        },
        "interactive_boxes": [
            {"x": 220, "y": 80, "w": 240, "h": 110},
            {"x": 480, "y": 80, "w": 240, "h": 110},
            {"x": 740, "y": 80, "w": 240, "h": 110},
            {"x": 1000, "y": 80, "w": 240, "h": 110},
        ],
        "overflow_issues": [],
        "regions": [
            {
                "role": "nav",
                "rect": {"x": 0, "y": 0, "w": 220, "h": 1400},
                "text": "Dashboard Analytics",
                "children_count": 0,
            },
            {
                "role": "main",
                "rect": {"x": 320, "y": 40, "w": 640, "h": 900},
                "text": "Overview",
                "children_count": 0,
            },
            {
                "role": "section",
                "rect": {"x": 220, "y": 80, "w": 1020, "h": 140},
                "text": "KPIs",
            },
            {
                "role": "section",
                "rect": {"x": 220, "y": 240, "w": 1020, "h": 320},
                "text": "Chart",
            },
            {
                "role": "section",
                "rect": {"x": 220, "y": 580, "w": 1020, "h": 400},
                "text": "Table",
            },
            {
                "role": "header",
                "rect": {"x": 220, "y": 0, "w": 1060, "h": 56},
                "text": "App",
            },
            {
                "role": "footer",
                "rect": {"x": 220, "y": 1300, "w": 1060, "h": 80},
                "text": "Footer",
            },
        ],
    },
    "hierarchy": {
        "prominence_scores": [
            {"label": "Revenue", "score": 28.0, "level": 2},
            {"label": "Users", "score": 28.0, "level": 2},
            {"label": "Churn", "score": 27.0, "level": 2},
            {"label": "MRR", "score": 27.5, "level": 2},
        ],
    },
    "colors": {
        "token_backed_ratio": 0.18,
        "raw_color_count": 22,
    },
    "design_tokens": {},
}


@pytest.mark.unit
def test_majors_emit_even_without_verify_passed_on_psm() -> None:
    """Handler PSM may lack verification_status; majors must still challenge."""
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_live"
    ship = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=DesignSnapshot.from_dict(LIVE_SHAPED_DASHBOARD),
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    signals = {c["signal"] for c in ship["challenges"]}
    assert "nav_not_sticky" not in signals  # verify convention, not Ship Council
    assert "responsive_breakage" not in signals
    assert "narrow_centered_main" in signals
    assert ship["ship_gate"]["council_clear"] is False


@pytest.mark.unit
def test_live_shaped_snapshot_emits_layout_and_hierarchy_challenges() -> None:
    """Council must fire on live extractor shapes, not only hand-crafted fixtures."""
    psm = _structural_psm()
    snapshot = DesignSnapshot.from_dict(LIVE_SHAPED_DASHBOARD)
    ship = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    signals = {c["signal"] for c in ship["challenges"]}
    assert "nav_not_sticky" not in signals
    assert "narrow_centered_main" in signals
    assert "equal_weight_kpi_cluster" in signals
    assert ship["ship_gate"]["council_clear"] is False
    assert ship["ship_gate"]["state"] == "challenge"


@pytest.mark.unit
def test_maze_style_equal_kpi_h2s_not_poisoned_by_sidebar_h4() -> None:
    """Same-level KPI headings must fire even when sidebar chrome has smaller headings."""
    from navigation.coordination_intelligence.planning.ship_council import (
        _collect_snapshot_signals,
    )

    snap = {
        "layout": {
            "viewport": {"width": 1440, "height": 900},
            "interactive_boxes": [],  # static cards — not interactive
            "visual_insights": {"element_boxes": []},
            "regions": [
                {"role": "aside", "rect": {"x": 0, "y": 0, "w": 230, "h": 900}},
                {"role": "main", "rect": {"x": 230, "y": 0, "w": 1210, "h": 900}},
            ],
        },
        "hierarchy": {
            "prominence_scores": [
                {"label": "Welcome, admin", "score": 40.0, "level": 1},
                {"label": "Revenue", "score": 28.0, "level": 2},
                {"label": "Users", "score": 28.0, "level": 2},
                {"label": "Churn", "score": 28.0, "level": 2},
                {"label": "NPS", "score": 28.0, "level": 2},
                {"label": "OVERVIEW", "score": 12.0, "level": 4},
                {"label": "REPORTS", "score": 12.0, "level": 4},
                {"label": "TEAM", "score": 12.0, "level": 4},
            ],
        },
        "colors": {"token_backed_ratio": 0.2},
    }
    signals = {s["signal"] for s in _collect_snapshot_signals(snap, surface_type="dashboard")}
    assert "equal_weight_kpi_cluster" in signals


@pytest.mark.unit
def test_sparse_login_clear_has_low_confidence_not_false_certainty() -> None:
    psm = _structural_psm()
    sparse = {
        "url": "http://localhost:5173/login",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "document_size": {"width": 1280, "height": 720},
            "visual_insights": {"issues": [], "blocking": [], "element_boxes": []},
            "regions": [
                {"role": "form", "rect": {"x": 440, "y": 200, "w": 400, "h": 320}, "text": "Login"},
                {"role": "main", "rect": {"x": 0, "y": 0, "w": 1280, "h": 720}, "text": ""},
            ],
            "overflow_issues": [],
        },
        "hierarchy": {"prominence_scores": [{"label": "Sign in", "score": 32.0, "level": 1}]},
        "colors": {"token_backed_ratio": 0.7, "raw_color_count": 4},
        "design_tokens": {},
    }
    ship = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=DesignSnapshot.from_dict(sparse),
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    assert ship["ship_gate"]["council_clear"] is True
    summary = ship["ship_summary"] or {}
    assert summary.get("ship_confidence", 1.0) <= 0.65
    assert ship["ship_gate"].get("coverage") in ("thin", "partial")


@pytest.mark.unit
def test_build_ship_council_emits_ranked_challenges() -> None:
    psm = _structural_psm()
    snapshot = _dashboard_snapshot()
    ship = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=snapshot,
        engineering_delta={
            "top_by_impact": [
                {
                    "decision_id": "hierarchy.primary_kpi",
                    "kind": "hierarchy",
                    "severity": "major",
                    "impact_weight": 0.91,
                    "detail": "KPI cluster lacks focal point",
                },
            ],
        },
        revision_gate={"revision_required": False},
        findings=[],
    )
    assert ship["mode"] == "ship"
    challenges = ship["challenges"]
    assert 1 <= len(challenges) <= MAX_CHALLENGES
    scores = [c["roi_score"] for c in challenges]
    assert scores == sorted(scores, reverse=True)
    assert all("question" in c and "why_it_matters" in c for c in challenges)
    assert ship["ship_gate"]["council_clear"] is False
    assert ship["ship_gate"]["state"] == "challenge"


@pytest.mark.unit
def test_build_ship_council_skips_minimal_influence() -> None:
    psm = _structural_psm()
    ship = build_ship_council(
        psm=psm,
        strategy=MINIMAL_STRATEGY,
        snapshot=_dashboard_snapshot(),
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    assert ship["ship_gate"]["state"] == "skipped"
    assert ship["ship_gate"]["council_clear"] is True


@pytest.mark.unit
def test_build_ship_council_clears_after_dispositions() -> None:
    psm = _structural_psm()
    snapshot = _dashboard_snapshot()
    first = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    signals = [c["signal"] for c in first["challenges"]]
    assert signals

    dispositions = []
    for sig in signals:
        dispositions.append({
            "signal": sig,
            "disposition": "accepted",
            "reason": "Matches explicit product requirement for equal metric emphasis across all KPI cards.",
        })
    second = build_ship_council(
        psm=psm,
        strategy=STRUCTURAL_STRATEGY,
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        dispositions=dispositions,
    )
    for sig in signals:
        entry = (second["decision_ledger"].get("entries") or {}).get(sig) or {}
        assert entry.get("disposition") == "accepted"
    assert (second["decision_ledger"].get("session_stats") or {}).get("accepted") == len(signals)


@pytest.mark.unit
def test_should_recommend_ship_mode_after_verify() -> None:
    psm = _structural_psm(verify_passed=True)
    assert should_recommend_ship_mode(psm, STRUCTURAL_STRATEGY) is True
    psm.episode.verification_status = "pending"
    assert should_recommend_ship_mode(psm, STRUCTURAL_STRATEGY) is False


@pytest.mark.unit
def test_should_recommend_ship_even_when_precode_gate_still_blocked() -> None:
    """Once draft+verify exist, pre-code blocked gate must not hide ship hint."""
    psm = _structural_psm(verify_passed=True)
    blocked = {
        **STRUCTURAL_STRATEGY,
        "implementation_gate": {"state": "blocked", "reason": "inspiration_needed"},
    }
    assert should_recommend_ship_mode(psm, blocked) is True
    assert ship_council_hint(blocked, psm) is not None


@pytest.mark.unit
def test_design_driven_maintenance_still_requires_ship_before_claim_done() -> None:
    """After redesign verify, influence may collapse to maintenance — Ship Council must still run."""
    from navigation.coordination_intelligence.planning.implementation_readiness import (
        compile_implementation_readiness,
    )
    from navigation.coordination_intelligence.planning.ship_council import (
        episode_needs_ship_council,
        should_skip_ship_council,
    )

    psm = _structural_psm(verify_passed=True)
    maintenance = {
        "influence_level": "maintenance",
        "task_scope": "design_driven",
        "unresolved_decisions": [],
        "implementation_gate": {"state": "maintenance"},
    }
    assert episode_needs_ship_council(psm, maintenance) is True
    assert should_recommend_ship_mode(psm, maintenance) is True
    assert should_skip_ship_council(
        influence_level="maintenance",
        task_scope="design_driven",
    ) is False

    gate, _, resource = compile_implementation_readiness(
        psm,
        influence_level="maintenance",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    assert "claim_complete" in gate["prohibited_actions"]
    assert gate.get("ship_council_required") is True
    assert resource == "perception://ship-council"
    assert should_recommend_ship_mode(psm, maintenance) is True

    # After council clears, claim-done may proceed.
    psm.episode.retry_counters["ship_council_clear"] = True
    assert episode_needs_ship_council(psm, maintenance) is False
    gate2, _, _ = compile_implementation_readiness(
        psm,
        influence_level="maintenance",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    assert "claim_complete" not in gate2["prohibited_actions"]
    assert gate2.get("ship_council_required") is not True


@pytest.mark.unit
def test_should_skip_ship_council_for_hotfix() -> None:
    assert should_skip_ship_council(
        influence_level="minimal",
        task_scope="hotfix",
    ) is True


@pytest.mark.unit
def test_ship_council_hint_payload_when_eligible() -> None:
    psm = _structural_psm(verify_passed=True)
    hint = ship_council_hint(STRUCTURAL_STRATEGY, psm)
    assert hint is not None
    assert hint.get("mode") == "ship"
    assert hint.get("capability") == "design_review"
    assert hint.get("resource") == "perception://ship-council"


@pytest.mark.unit
def test_normalize_ship_mode_provisional_when_gate_open() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    envelope = {
        "ok": True,
        "tool": "perception_design_review",
        "data": {
            "mode": "ship",
            "challenges": [{"signal": "nav_not_sticky"}],
            "ship_gate": {"council_clear": False, "open_high_roi": 1, "state": "challenge"},
        },
    }
    apply_envelope(psm, envelope, bundle)
    outcome = psm.evidence.capability_ledger["design_review"]
    assert outcome["status"] == "provisional"
    assert outcome["advancement_eligible"] is False


@pytest.mark.unit
def test_normalize_ship_mode_succeeded_when_clear() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    envelope = {
        "ok": True,
        "tool": "perception_design_review",
        "data": {
            "mode": "ship",
            "challenges": [],
            "ship_gate": {"council_clear": True, "open_high_roi": 0, "state": "clear"},
            "coordination_evidence": {
                "outcome": "success",
                "advancement_eligible": True,
            },
        },
    }
    apply_envelope(psm, envelope, bundle)
    outcome = psm.evidence.capability_ledger["design_review"]
    assert outcome["status"] == "succeeded"
    assert outcome["advancement_eligible"] is True


@pytest.mark.unit
def test_ship_council_methodology_resource() -> None:
    listed = {item["uri"] for item in list_resources()}
    assert "perception://ship-council" in listed
    mime, text, is_blob = read_resource("perception://ship-council")
    assert mime == "text/markdown"
    assert is_blob is False
    assert "Ship Council" in text
    assert 'mode="ship"' in text


@pytest.mark.unit
def test_handle_design_review_ship_mode_surfaces_coverage() -> None:
    snapshot = DesignSnapshot.from_dict(LIVE_SHAPED_DASHBOARD)
    snapshots = SnapshotRegistry()
    rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

    result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snapshots,
            {"snapshot_id": rec.snapshot_id, "user_task": "Ship dashboard", "mode": "ship"},
        )
    )
    assert result["ok"] is True
    data = result["data"]
    assert data["mode"] == "ship"
    assert data["ship_gate"]["council_clear"] is False
    assert data["ship_gate"].get("coverage") in ("full", "partial")
    assert "coverage" in (data["agent_summary"].get("ship_council_hint") or {})
    assert len(data["challenges"]) >= 3


@pytest.mark.unit
def test_handle_design_review_ship_mode() -> None:
    snapshot = _dashboard_snapshot()
    snapshots = SnapshotRegistry()
    rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

    result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snapshots,
            {"snapshot_id": rec.snapshot_id, "user_task": "Ship dashboard", "mode": "ship"},
        )
    )
    assert result["ok"] is True
    data = result["data"]
    assert data["mode"] == "ship"
    assert "challenges" in data
    assert "ship_gate" in data
    assert "framing" in data
    assert data["agent_summary"]["mode"] == "ship"
    assert len(data["challenges"]) <= MAX_CHALLENGES


@pytest.mark.unit
def test_handle_design_review_review_mode_unchanged() -> None:
    snapshot = _dashboard_snapshot()
    snapshots = SnapshotRegistry()
    rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

    result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snapshots,
            {"snapshot_id": rec.snapshot_id, "user_task": "Review dashboard", "mode": "review"},
        )
    )
    assert result["ok"] is True
    data = result["data"]
    assert data.get("mode", "review") != "ship" or "report" in data
    assert "report" in data
    assert "top_findings" in data


@pytest.mark.unit
def test_uneven_kpi_columns_challenge_and_equal_weight_guidance() -> None:
    """Broken col-span hierarchy fixes must be challenged; equal-weight must forbid them."""
    from navigation.coordination_intelligence.planning.ship_council import (
        SIGNAL_TEMPLATES,
        _collect_snapshot_signals,
        _materialize_challenge,
    )

    tpl = SIGNAL_TEMPLATES["equal_weight_kpi_cluster"]
    assert "col-span" in str(tpl.get("revise_guidance") or "").lower() or "equal-width" in str(
        tpl.get("revise_guidance") or ""
    ).lower()

    uneven = {
        "url": "http://localhost:5173/",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "interactive_boxes": [
                {"x": 40, "y": 120, "w": 420, "h": 140},
                {"x": 480, "y": 120, "w": 200, "h": 140},
                {"x": 700, "y": 120, "w": 200, "h": 140},
                {"x": 920, "y": 120, "w": 200, "h": 140},
            ],
            "regions": [{"role": "main", "rect": {"x": 0, "y": 0, "w": 1280, "h": 720}}],
            "overflow_issues": [],
        },
        "hierarchy": {"prominence_scores": []},
        "colors": {"token_backed_ratio": 0.8},
        "design_tokens": {},
    }
    signals = {s["signal"] for s in _collect_snapshot_signals(uneven, surface_type="dashboard")}
    assert "uneven_kpi_columns" in signals

    psm = _structural_psm()
    challenge = _materialize_challenge(
        {"signal": "equal_weight_kpi_cluster", "severity": "major", "specdiff_magnitude": 0.8},
        strategy=STRUCTURAL_STRATEGY,
        psm=psm,
    )
    assert challenge is not None
    assert "revise_guidance" in challenge
    assert "anti_patterns" in challenge
    assert any("col-span" in a.lower() for a in challenge["anti_patterns"])


@pytest.mark.unit
def test_marketing_about_skips_kpi_and_dashboard_composition() -> None:
    """About/marketing pages must not get dashboard KPI heuristics (Test 7 false-fire)."""
    from navigation.coordination_intelligence.planning.ship_council import (
        _collect_snapshot_signals,
    )
    from navigation.coordination_intelligence.planning.surface_type import derive_surface_type

    about = {
        "url": "http://127.0.0.1:3000/about",
        "layout": {
            "viewport": {"width": 1280, "height": 900},
            "regions": [
                {"role": "banner", "rect": {"x": 0, "y": 0, "w": 1280, "h": 72}},
                {"role": "main", "rect": {"x": 80, "y": 100, "w": 1120, "h": 700}},
                {"role": "section", "rect": {"x": 80, "y": 120, "w": 1120, "h": 180}, "text": "Journey"},
                {"role": "section", "rect": {"x": 80, "y": 320, "w": 1120, "h": 180}, "text": "Work"},
                {"role": "section", "rect": {"x": 80, "y": 520, "w": 1120, "h": 180}, "text": "Essays"},
                {"role": "section", "rect": {"x": 80, "y": 720, "w": 1120, "h": 120}, "text": "Contact"},
                {"role": "contentinfo", "rect": {"x": 0, "y": 860, "w": 1280, "h": 40}},
            ],
            "interactive_boxes": [],
            "overflow_issues": [],
        },
        "hierarchy": {
            "prominence_scores": [
                {"label": "My journey", "score": 40.0, "level": 1},
                {"label": "Selected work", "score": 28.0, "level": 2},
                {"label": "Essays", "score": 28.0, "level": 2},
                {"label": "Get in touch", "score": 27.0, "level": 2},
            ],
        },
        "colors": {"token_backed_ratio": 0.2},
        "design_tokens": {},
    }
    surface = derive_surface_type("redesign artful portfolio about page", snapshot=about)
    assert surface == "marketing"
    signals = {s["signal"] for s in _collect_snapshot_signals(about, surface_type=surface)}
    assert "equal_weight_kpi_cluster" not in signals
    assert "dashboard_composition" not in signals
    assert "theme_not_coupled" in signals  # still allowed on marketing

    psm = _structural_psm()
    psm.episode.intent_stack.append(
        IntentFrame(intent="redesign artful portfolio about page", pushed_at="t")
    )
    ship = build_ship_council(
        psm=psm,
        strategy={**STRUCTURAL_STRATEGY, "surface_type": "marketing"},
        snapshot=DesignSnapshot.from_dict(about),
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    signals2 = {c["signal"] for c in ship["challenges"]}
    assert "equal_weight_kpi_cluster" not in signals2
    assert "dashboard_composition" not in signals2
    assert ship["ship_gate"]["surface_type"] == "marketing"

    # Findings path used to default majors to dashboard_composition — must still filter.
    noisy_findings = [
        {"severity": "major", "category": "composition", "id": "dense_regions"},
        {"severity": "major", "category": "hierarchy", "id": "kpi_row"},
    ]
    ship2 = build_ship_council(
        psm=_structural_psm(),
        strategy={**STRUCTURAL_STRATEGY, "surface_type": "marketing"},
        snapshot=DesignSnapshot.from_dict(about),
        engineering_delta=None,
        revision_gate={},
        findings=noisy_findings,
        force=True,
    )
    signals3 = {c["signal"] for c in ship2["challenges"]}
    assert "equal_weight_kpi_cluster" not in signals3
    assert "dashboard_composition" not in signals3


def main() -> int:
    print("ship council tests: use pytest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
