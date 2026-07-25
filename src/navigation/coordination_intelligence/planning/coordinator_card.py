from __future__ import annotations

import hashlib
import json
from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

CARD_SCHEMA = "coordinator_card.v1"
EPISODE_CARD_SCHEMA = "episode_card.v1"

_QUALITY_FLAGS = (
    "thin",
    "thin_clear",
    "revision_required",
    "soft_seed_partial",
    "evidence_useful",
    "seed_unresolved_count",
    "usable_image_refs",
)


def strategy_fingerprint(psm: ProjectSituationModel) -> str:
    ledger_bits = []
    for cap, outcome in sorted((psm.evidence.capability_ledger or {}).items()):
        if not isinstance(outcome, dict):
            continue
        q = outcome.get("quality") if isinstance(outcome.get("quality"), dict) else {}
        flags = {k: q.get(k) for k in _QUALITY_FLAGS if k in q}
        ledger_bits.append({
            "cap": cap,
            "status": outcome.get("status"),
            "adv": outcome.get("advancement_eligible"),
            "flags": flags,
        })
    section_raw = psm.episode.retry_counters.get("section_checklist")
    section_bits: list[dict[str, Any]] = []
    section_complete = False
    if isinstance(section_raw, dict):
        section_complete = bool(section_raw.get("complete"))
        for item in section_raw.get("sections") or []:
            if not isinstance(item, dict):
                continue
            section_bits.append({
                "id": item.get("section_id"),
                "o": bool(item.get("observed")),
                "v": bool(item.get("verified")),
            })
        section_bits.sort(key=lambda x: str(x.get("id") or ""))
    residual = {
        "verify": psm.episode.verification_status,
        "surface": getattr(psm.episode, "surface_type", None),
        "ship_clear": bool(psm.episode.retry_counters.get("ship_council_clear")),
        "ship_run": bool(psm.episode.retry_counters.get("ship_council_run")),
        "residue": psm.episode.retry_counters.get("residue_scan"),
        "sections_complete": section_complete,
        "sections": section_bits,
        "lifecycle": psm.situation.lifecycle_stage,
        "maturity": psm.situation.project_maturity,
        "sclass": psm.situation.situation_class,
        "intent": "|".join(f.intent for f in psm.episode.intent_stack),
        "active_route": getattr(psm.episode, "active_route_path", None)
        or psm.episode.retry_counters.get("active_route_path"),
        "routes": sorted(
            (
                f"{e.get('path')}:{e.get('surface')}"
                for e in (getattr(psm.episode, "route_surfaces", None) or {}).values()
                if isinstance(e, dict)
            )
        ),
    }
    payload = {"ledger": ledger_bits, "ep": residual}
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def build_coordinator_card(
    *,
    episode_id: str,
    strategy: dict[str, Any] | None,
    suggested_capability: str | None = None,
    suggested_semantic_action: str | None = None,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    strategy = strategy or {}
    gate = dict(strategy.get("implementation_gate") or {})
    conf = strategy.get("episode_confidence") or {}
    portfolio = strategy.get("episode_portfolio") or {}
    paid = [
        str(p.get("family"))
        for p in (portfolio.get("paid") or [])
        if isinstance(p, dict) and p.get("family")
    ]
    unpaid = [
        str(u.get("family"))
        for u in (portfolio.get("unpaid") or [])
        if isinstance(u, dict) and u.get("family")
    ]
    return {
        "schema": CARD_SCHEMA,
        "episode_id": episode_id,
        "integrated": True,
        "host_action": strategy.get("host_action"),
        "gate": {
            "state": gate.get("state"),
            "next_required_capability": gate.get("next_required_capability"),
            "prohibited_actions": list(gate.get("prohibited_actions") or []),
        },
        "implementation_gate": gate,  # one-cycle alias
        "suggested_capability": suggested_capability,
        "suggested_semantic_action": suggested_semantic_action,
        "stop_reason": stop_reason,
        "confidence": {
            "score": conf.get("score"),
            "band": conf.get("band"),
        },
        "portfolio": {"paid": paid, "unpaid": unpaid},
        "evidence_quality_alerts": list(strategy.get("evidence_quality_alerts") or []),
        "recommended_resource": strategy.get("recommended_resource"),
        "active_route": strategy.get("active_route"),
        "routes": list(strategy.get("routes") or []),
    }


def build_episode_card(
    *,
    episode_id: str,
    strategy: dict[str, Any] | None,
    suggested_capability: str | None = None,
    suggested_semantic_action: str | None = None,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    """Unified agent-facing readout — coordinator card + what_matters one-liner."""
    strategy = strategy or {}
    base = build_coordinator_card(
        episode_id=episode_id,
        strategy=strategy,
        suggested_capability=suggested_capability,
        suggested_semantic_action=suggested_semantic_action,
        stop_reason=stop_reason,
    )
    matters = list(strategy.get("what_matters_now") or [])
    what_matters = str(matters[0]) if matters else str(strategy.get("host_action") or "")
    return {
        **base,
        "schema": EPISODE_CARD_SCHEMA,
        "what_matters": what_matters,
        "surface_type": strategy.get("surface_type") or "unknown",
        "influence_level": strategy.get("influence_level"),
        "active_route": strategy.get("active_route"),
        "routes": list(strategy.get("routes") or []),
    }
