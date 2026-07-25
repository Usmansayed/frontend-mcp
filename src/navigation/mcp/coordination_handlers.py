"""MCP handlers for Coordination Intelligence (additive — does not change existing tools)."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.integration.bridge import get_coordinator_bridge
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


def _get_service() -> CoordinationIntelligenceService:
    return get_coordinator_bridge().service


async def handle_coordinator_episode_start(args: dict[str, Any]) -> dict[str, Any]:
    """Start or reuse a coordinator episode.

    Default: if session_id is already bound to a live episode, REUSE it (preserve
    budget/evidence/gate). Pass force_new=true for an explicit hard reset.
    """
    svc = _get_service()
    bridge = get_coordinator_bridge()
    project_id = str(args.get("project_id") or "default")
    session_id = str(args.get("session_id") or "").strip() or None
    force_new = bool(args.get("force_new") or False)

    reused = False
    previous_episode_id: str | None = None
    if session_id and not force_new:
        existing = bridge._bindings.resolve_session(session_id)
        if existing and svc.runtime.get(existing):
            psm = svc.runtime.require(existing)
            previous_episode_id = existing
            if args.get("website_url"):
                psm.artifacts.website_url = str(args["website_url"])
            if args.get("repo_root"):
                psm.artifacts.repo_root = str(args["repo_root"])
            psm.artifacts.session_id = session_id
            if args.get("intent"):
                svc.push_intent(existing, str(args["intent"]))
            else:
                svc.runtime.save(psm)
            reused = True
            briefing = svc.briefing(psm.episode_id, step_context=args.get("step_context"))
            return make_envelope(
                "perception_coordinator_episode_start",
                ok=True,
                session_id=psm.artifacts.session_id,
                data={
                    "episode_id": psm.episode_id,
                    "reused_existing_episode": True,
                    "force_new": False,
                    "previous_episode_id": previous_episode_id,
                    "reset": False,
                    "host_action": (
                        "Reused existing episode for this session — evidence/budget preserved. "
                        "Pass force_new=true to hard-reset PSM."
                    ),
                    "coordinator_briefing": briefing.to_dict(),
                    "psm": svc.get_psm(psm.episode_id),
                },
            )

    if session_id:
        previous_episode_id = bridge._bindings.resolve_session(session_id)

    psm = svc.episode_start(
        project_id=project_id,
        cluster_id=args.get("cluster_id"),
        playbook_id=args.get("playbook_id"),
        situation_class=args.get("situation_class") or "new_feature",
        lifecycle_stage=args.get("lifecycle_stage") or "S05_implementation",
        repo_root=args.get("repo_root"),
        website_url=args.get("website_url"),
        session_id=session_id,
        intent=args.get("intent"),
        leaf_hint=args.get("leaf_hint"),
    )
    briefing = svc.briefing(psm.episode_id, step_context=args.get("step_context"))
    bridge._bindings.bind_project(project_id, psm.episode_id)
    if psm.artifacts.session_id:
        bridge._bindings.bind_session(
            psm.artifacts.session_id,
            psm.episode_id,
        )
    return make_envelope(
        "perception_coordinator_episode_start",
        ok=True,
        session_id=psm.artifacts.session_id,
        data={
            "episode_id": psm.episode_id,
            "reused_existing_episode": reused,
            "force_new": force_new,
            "previous_episode_id": previous_episode_id,
            "reset": True,
            "host_action": (
                "Started a NEW episode — prior episode evidence/budget were NOT merged. "
                "Omit force_new (default) with the same session_id to reuse instead."
            ),
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
        session_id=psm.get("artifacts", {}).get("session_id") if isinstance(psm, dict) else None,
        scan_id=psm.get("artifacts", {}).get("scan_id") if isinstance(psm, dict) else None,
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
        session_id=psm.get("artifacts", {}).get("session_id") if isinstance(psm, dict) else None,
        data={
            "episode_id": episode_id,
            "coordinator_briefing": briefing.to_dict(),
            "psm": psm,
        },
    )
