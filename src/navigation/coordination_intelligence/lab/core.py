"""Decision Layer Lab — production coordination without real MCP tools."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import (
    RuntimeArtifactBundle,
    load_runtime_artifacts,
)
from navigation.coordination_intelligence.lab.expect import (
    ExpectationError,
    assert_expectations,
    check_expectations,
)
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


class DecisionLayerLab:
    """Feed fake envelopes into CoordinationIntelligenceService; inspect decisions."""

    def __init__(
        self,
        *,
        bundle: RuntimeArtifactBundle | None = None,
        session_id: str = "lab_session",
    ) -> None:
        self._bundle = bundle or load_runtime_artifacts()
        self.service = CoordinationIntelligenceService(bundle=self._bundle)
        self.session_id = session_id
        self.episode_id: str | None = None
        self.history: list[dict[str, Any]] = []
        self.last_ship: dict[str, Any] | None = None

    def start(
        self,
        intent: str,
        *,
        lifecycle_stage: str = "S03_design",
        project_maturity: str = "M1",
        situation_class: str = "new_feature",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        psm = self.service.episode_start(
            session_id=session_id or self.session_id,
            intent=intent,
            lifecycle_stage=lifecycle_stage,
            project_maturity=project_maturity,
            situation_class=situation_class,
            **kwargs,
        )
        self.episode_id = psm.episode_id
        self.history = [{"op": "start", "intent": intent, "episode_id": self.episode_id}]
        return self.episode_id

    def _require_episode(self) -> str:
        if not self.episode_id:
            raise RuntimeError("call start() before feed/snapshot")
        return self.episode_id

    def feed(
        self,
        tool: str,
        *,
        ok: bool = True,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        arguments: dict[str, Any] | None = None,
        capability_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        eid = self._require_episode()
        envelope = make_envelope(
            tool,
            ok=ok,
            session_id=session_id or self.session_id,
            error=error,
            data=dict(data or {}),
        )
        enriched = self.service.on_tool_envelope(
            eid,
            tool,
            dict(arguments or {}),
            envelope,
            capability_hint=capability_id,
        )
        snap = self.snapshot()
        self.history.append({
            "op": "feed",
            "tool": tool,
            "ok": ok,
            "capability_id": capability_id,
            "snapshot": snap,
        })
        return {"envelope": enriched, "snapshot": snap}

    def seed_ledger(
        self,
        capability_id: str,
        outcome: dict[str, Any],
    ) -> dict[str, Any]:
        """Bypass normalize — write capability_ledger directly (fast path)."""
        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        psm.evidence.capability_ledger[capability_id] = dict(outcome)
        self.service.runtime.save(psm)
        # Refresh strategy without a tool envelope
        self.service.briefing(eid)
        snap = self.snapshot()
        self.history.append({
            "op": "seed_ledger",
            "capability_id": capability_id,
            "snapshot": snap,
        })
        return snap

    def set_retry(self, key: str, value: Any) -> dict[str, Any]:
        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        psm.episode.retry_counters[key] = value
        self.service.runtime.save(psm)
        self.service.briefing(eid)
        return self.snapshot()

    def set_surface_type(self, surface_type: str) -> dict[str, Any]:
        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        psm.episode.surface_type = surface_type
        self.service.runtime.save(psm)
        self.service.briefing(eid)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        eid = self._require_episode()
        briefing = self.service.briefing(eid)
        strategy = dict(briefing.engineering_strategy or {})
        gate = dict(strategy.get("implementation_gate") or {})
        psm = self.service.runtime.require(eid)
        from navigation.coordination_intelligence.planning.coordinator_card import (
            build_episode_card,
        )

        episode_card = build_episode_card(
            episode_id=eid,
            strategy=strategy,
            suggested_capability=briefing.suggested_capability,
            suggested_semantic_action=briefing.suggested_semantic_action,
            stop_reason=briefing.stop_reason,
        )
        from navigation.coordination_intelligence.planning.coordinator_card import (
            build_coordinator_card,
        )
        from navigation.coordination_intelligence.planning.engineering_strategy import (
            promote_coordinator_visibility,
        )

        coord_card = build_coordinator_card(
            episode_id=eid,
            strategy=strategy,
            suggested_capability=briefing.suggested_capability,
            suggested_semantic_action=briefing.suggested_semantic_action,
            stop_reason=briefing.stop_reason,
        )
        agent_summary: dict[str, Any] = {
            "engineering_strategy": strategy,
            "episode_card": episode_card,
        }
        promote_envelope = {"agent_summary": agent_summary, "data": {"coordinator": coord_card}}
        promote_coordinator_visibility(promote_envelope, coord_card)
        return {
            "episode_id": eid,
            "suggested_capability": briefing.suggested_capability,
            "suggested_semantic_action": briefing.suggested_semantic_action,
            "stop_reason": briefing.stop_reason,
            "strategy": strategy,
            "gate": gate,
            "surface_type": strategy.get("surface_type") or getattr(psm.episode, "surface_type", None),
            "backlog": strategy.get("episode_backlog") or {},
            "initiative": strategy.get("initiative") or {},
            "episode_portfolio": strategy.get("episode_portfolio") or {},
            "episode_confidence": strategy.get("episode_confidence") or {},
            "episode_card": episode_card,
            "coordinator": coord_card,
            "agent_summary": agent_summary,
            "host_action": strategy.get("host_action"),
            "what_matters_now": strategy.get("what_matters_now") or [],
            "verification_status": psm.episode.verification_status,
            "capability_ledger": dict(psm.evidence.capability_ledger),
            "retry_counters": dict(psm.episode.retry_counters),
            "gate_next": gate.get("next_required_capability"),
            "host_theme": _host_theme(strategy.get("host_action")),
            "last_ship": dict(self.last_ship) if self.last_ship else None,
        }

    def run_ship(
        self,
        snapshot: dict[str, Any] | Any,
        *,
        dispositions: list[dict[str, Any]] | None = None,
        auto_dispose: str | None = None,
        force: bool = True,
    ) -> dict[str, Any]:
        """Run Ship Council against a snapshot fixture (no MCP design_review tool)."""
        from navigation.coordination_intelligence.planning.ship_council import build_ship_council
        from navigation.design_snapshot_engine.models import DesignSnapshot

        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        strategy = self.snapshot()["strategy"]
        if isinstance(snapshot, dict):
            snap_obj = DesignSnapshot.from_dict(snapshot)
        else:
            snap_obj = snapshot

        ship = build_ship_council(
            psm=psm,
            strategy=strategy,
            snapshot=snap_obj,
            engineering_delta=None,
            revision_gate={},
            findings=[],
            dispositions=None,
            force=force,
        )

        disp = list(dispositions or [])
        if auto_dispose in ("revised", "accepted") and ship.get("challenges"):
            reason = (
                "revised layout hierarchy and composition against measured snapshot evidence"
                if auto_dispose == "revised"
                else (
                    "accepted: product analytics convention requires equal KPI weight "
                    "for this dashboard surface by design system"
                )
            )
            disp = [
                {
                    "signal": c["signal"],
                    "disposition": auto_dispose,
                    "reason": reason,
                }
                for c in ship["challenges"]
            ]
            ship = build_ship_council(
                psm=psm,
                strategy=self.snapshot()["strategy"],
                snapshot=snap_obj,
                engineering_delta=None,
                revision_gate={},
                findings=[],
                dispositions=disp,
                force=force,
            )

        self.service.runtime.save(psm)
        self.service.briefing(eid)
        snap = self.snapshot()
        self.last_ship = {
            "ship_gate": ship.get("ship_gate"),
            "challenges": list(ship.get("challenges") or []),
            "signals": [c.get("signal") for c in ship.get("challenges") or []],
            "rejected_dispositions": ship.get("rejected_dispositions"),
        }
        snap["last_ship"] = dict(self.last_ship)
        self.history.append({
            "op": "run_ship",
            "ship_gate": ship.get("ship_gate"),
            "challenges": self.last_ship["signals"],
            "snapshot": snap,
        })
        return {"ship": ship, "snapshot": snap}

    def complete_sections(self) -> dict[str, Any]:
        """Lab helper: mark all section checklist items observed+verified."""
        from navigation.coordination_intelligence.planning.section_checklist import (
            incomplete_sections,
            mark_section_observed,
            mark_section_verified,
        )

        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        for sid in list(incomplete_sections(psm)):
            mark_section_observed(psm, section_id=sid)
            mark_section_verified(psm, section_id=sid, verified=True)
        self.service.runtime.save(psm)
        self.service.briefing(eid)
        snap = self.snapshot()
        self.history.append({"op": "complete_sections", "snapshot": snap})
        return snap

    def seed_sections_from_regions(self, regions: list[dict[str, Any]]) -> dict[str, Any]:
        from navigation.coordination_intelligence.planning.section_checklist import (
            seed_section_checklist_from_regions,
        )

        eid = self._require_episode()
        psm = self.service.runtime.require(eid)
        seed_section_checklist_from_regions(psm, regions)
        self.service.runtime.save(psm)
        self.service.briefing(eid)
        return self.snapshot()

    def expect(self, **assertions: Any) -> dict[str, Any]:
        snap = self.snapshot()
        assert_expectations(snap, assertions)
        return snap

    def check(self, expect: dict[str, Any] | None) -> list[str]:
        return check_expectations(self.snapshot(), expect)

    def show(self) -> str:
        snap = self.snapshot()
        gate = snap.get("gate") or {}
        conf = snap.get("episode_confidence") or {}
        top = (snap.get("backlog") or {}).get("top") or {}
        portfolio = snap.get("episode_portfolio") or {}
        paid = ",".join(p.get("family", "") for p in (portfolio.get("paid") or [])) or "-"
        unpaid = ",".join(u.get("family", "") for u in (portfolio.get("unpaid") or [])) or "-"
        lines = [
            f"episode={snap.get('episode_id')}",
            f"surface={snap.get('surface_type')}  scope={snap['strategy'].get('task_scope')}  "
            f"influence={snap['strategy'].get('influence_level')}",
            f"gate.state={gate.get('state')}  next={gate.get('next_required_capability')}  "
            f"host_theme={snap.get('host_theme')}",
            f"prohibited={gate.get('prohibited_actions')}",
            f"section={gate.get('section_checklist_required')}  ship={gate.get('ship_council_required')}  "
            f"residue={gate.get('residue_scan_required')}  evidence_open={gate.get('evidence_plan_incomplete')}",
            f"confidence={conf.get('score')} ({conf.get('band')})",
            f"portfolio paid=[{paid}] unpaid=[{unpaid}]",
            f"backlog.top={top.get('kind')}:{top.get('id')}  {top.get('title')}",
            f"suggested={snap.get('suggested_capability')} / {snap.get('suggested_semantic_action')}",
            f"host={snap.get('host_action')}",
        ]
        return "\n".join(lines)


def _host_theme(host_action: str | None) -> str:
    text = host_action or ""
    for key in (
        "SHIP GATE",
        "RESIDUE SCAN",
        "SECTION CHECKLIST",
        "EVIDENCE PLAN",
        "BLOCKED",
    ):
        if text.startswith(key) or key in text[:40]:
            return key
    return "other"


__all__ = [
    "DecisionLayerLab",
    "ExpectationError",
    "assert_expectations",
    "check_expectations",
]
