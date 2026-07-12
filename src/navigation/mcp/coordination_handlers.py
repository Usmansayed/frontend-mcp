"""MCP handlers for Coordination Intelligence (additive — does not change existing tools)."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.integration.bridge import get_coordinator_bridge
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


def _get_service() -> CoordinationIntelligenceService:
    return get_coordinator_bridge().service


async def handle_coordinator_episode_start(args: dict[str, Any]) -> dict[str, Any]:
    svc = _get_service()
    psm = svc.episode_start(
        project_id=args.get("project_id") or "default",
        cluster_id=args.get("cluster_id"),
        playbook_id=args.get("playbook_id"),
        situation_class=args.get("situation_class") or "new_feature",
        lifecycle_stage=args.get("lifecycle_stage") or "S05_implementation",
        repo_root=args.get("repo_root"),
        website_url=args.get("website_url"),
        session_id=args.get("session_id"),
        intent=args.get("intent"),
        leaf_hint=args.get("leaf_hint"),
    )
    briefing = svc.briefing(psm.episode_id, step_context=args.get("step_context"))
    if psm.artifacts.session_id:
        get_coordinator_bridge()._bindings.bind_session(
            psm.artifacts.session_id,
            psm.episode_id,
        )
    return make_envelope(
        "perception_coordinator_episode_start",
        ok=True,
        session_id=psm.artifacts.session_id,
        data={
            "episode_id": psm.episode_id,
            "coordinator_briefing": briefing.to_dict(),
            "psm": svc.get_psm(psm.episode_id),
        },
    )


async def handle_coordinator_apply_envelope(args: dict[str, Any]) -> dict[str, Any]:
    episode_id = args.get("episode_id")
    if not episode_id:
        return make_envelope(
            "perception_coordinator_apply_envelope",
            ok=False,
            error="episode_id is required",
        )
    envelope = args.get("envelope")
    if not isinstance(envelope, dict):
        return make_envelope(
            "perception_coordinator_apply_envelope",
            ok=False,
            error="envelope object is required",
        )
    svc = _get_service()
    try:
        briefing = svc.apply_envelope(
            episode_id,
            envelope,
            capability_id=args.get("capability_id"),
            step_context=args.get("step_context"),
        )
    except KeyError:
        return make_envelope(
            "perception_coordinator_apply_envelope",
            ok=False,
            error=f"unknown episode_id: {episode_id}",
        )
    psm = svc.get_psm(episode_id)
    return make_envelope(
        "perception_coordinator_apply_envelope",
        ok=True,
        session_id=psm.get("artifacts", {}).get("session_id"),
        scan_id=psm.get("artifacts", {}).get("scan_id"),
        data={
            "episode_id": episode_id,
            "coordinator_briefing": briefing.to_dict(),
            "psm": psm,
        },
    )


async def handle_coordinator_briefing(args: dict[str, Any]) -> dict[str, Any]:
    episode_id = args.get("episode_id")
    if not episode_id:
        return make_envelope(
            "perception_coordinator_briefing",
            ok=False,
            error="episode_id is required",
        )
    svc = _get_service()
    try:
        briefing = svc.briefing(episode_id, step_context=args.get("step_context"))
        psm = svc.get_psm(episode_id)
    except KeyError:
        return make_envelope(
            "perception_coordinator_briefing",
            ok=False,
            error=f"unknown episode_id: {episode_id}",
        )
    return make_envelope(
        "perception_coordinator_briefing",
        ok=True,
        session_id=psm.get("artifacts", {}).get("session_id"),
        data={
            "episode_id": episode_id,
            "coordinator_briefing": briefing.to_dict(),
            "psm": psm,
        },
    )
