"""Invisible coordinator bridge — hooks MCP tool results into PSM Runtime."""

from __future__ import annotations

import os
from typing import Any

from navigation.coordination_intelligence.integration.episode_binding import EpisodeBindingStore
from navigation.coordination_intelligence.service import CoordinationIntelligenceService

COORDINATOR_TOOL_PREFIX = "perception_coordinator_"

# Tools that manage coordinator state explicitly; bridge skips double-processing.
SKIP_BRIDGE_TOOLS = frozenset({
    "perception_coordinator_episode_start",
    "perception_coordinator_apply_envelope",
    "perception_coordinator_briefing",
})


def coordinator_enabled() -> bool:
    return os.environ.get("COORDINATION_DISABLED", "").lower() not in ("1", "true", "yes")


class CoordinatorBridge:
    """Transparent layer: every MCP tool result updates PSM and refreshes briefing."""

    def __init__(
        self,
        service: CoordinationIntelligenceService | None = None,
        *,
        bindings: EpisodeBindingStore | None = None,
    ) -> None:
        self._service = service or CoordinationIntelligenceService()
        self._bindings = bindings or EpisodeBindingStore()

    @property
    def service(self) -> CoordinationIntelligenceService:
        return self._service

    def process(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        envelope: dict[str, Any],
    ) -> dict[str, Any]:
        if not coordinator_enabled():
            return envelope
        if tool_name in SKIP_BRIDGE_TOOLS:
            return envelope
        if tool_name.startswith(COORDINATOR_TOOL_PREFIX):
            return envelope

        try:
            return self._process_inner(tool_name, arguments, envelope)
        except Exception:
            # Coordinator must never break existing MCP tool behavior.
            return envelope

    def _process_inner(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        envelope: dict[str, Any],
    ) -> dict[str, Any]:
        args = arguments or {}
        session_id = _extract_session_id(args, envelope)
        project_id = str(args.get("project_id") or "default")
        episode_id = self._bindings.resolve(
            session_id=session_id,
            project_id=project_id,
            episode_id=args.get("episode_id"),
        )

        if tool_name == "perception_session_start" and envelope.get("ok"):
            episode_id = self._ensure_session_episode(
                session_id=session_id or envelope.get("session_id"),
                project_id=project_id,
                website_url=args.get("base_url") or envelope.get("url"),
                repo_root=args.get("repo_root"),
                playbook_id=args.get("playbook_id"),
                cluster_id=args.get("cluster_id"),
                intent=args.get("intent"),
            )

        if not episode_id and session_id:
            episode_id = self._ensure_session_episode(
                session_id=session_id,
                project_id=project_id,
                website_url=envelope.get("url") or args.get("website_url"),
                repo_root=args.get("repo_root"),
            )

        if not episode_id:
            return envelope

        enriched = self._service.on_tool_envelope(
            episode_id,
            tool_name,
            args,
            envelope,
        )
        return enriched

    def _ensure_session_episode(
        self,
        *,
        session_id: str | None,
        project_id: str,
        website_url: str | None = None,
        repo_root: str | None = None,
        playbook_id: str | None = None,
        cluster_id: str | None = None,
        intent: str | None = None,
    ) -> str | None:
        if not session_id:
            return None
        existing = self._bindings.resolve(session_id=session_id)
        if existing and self._service.runtime.get(existing):
            psm = self._service.runtime.require(existing)
            if website_url:
                psm.artifacts.website_url = website_url
            if repo_root:
                psm.artifacts.repo_root = repo_root
            psm.artifacts.session_id = session_id
            self._service.runtime.save(psm)
            return existing

        psm = self._service.episode_start(
            project_id=project_id,
            session_id=session_id,
            website_url=website_url,
            repo_root=repo_root,
            playbook_id=playbook_id,
            cluster_id=cluster_id,
            intent=intent,
        )
        self._bindings.bind_session(session_id, psm.episode_id)
        self._bindings.bind_project(project_id, psm.episode_id)
        return psm.episode_id


def _extract_session_id(args: dict[str, Any], envelope: dict[str, Any]) -> str | None:
    for key in ("session_id",):
        val = args.get(key) or envelope.get(key)
        if val:
            return str(val)
    return None


_bridge: CoordinatorBridge | None = None


def get_coordinator_bridge() -> CoordinatorBridge:
    global _bridge
    if _bridge is None:
        _bridge = CoordinatorBridge()
    return _bridge


def process_tool_envelope(
    tool_name: str,
    arguments: dict[str, Any],
    envelope: dict[str, Any],
) -> dict[str, Any]:
    return get_coordinator_bridge().process(tool_name, arguments, envelope)
