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

        if tool_name == "perception_health":
            return self._attach_health_strategy(args, envelope)

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
            if episode_id and args.get("effort_tier"):
                try:
                    from navigation.coordination_intelligence.planning.right_sizing import (
                        set_effort_tier,
                    )

                    psm = self._service.runtime.require(episode_id)
                    set_effort_tier(psm, str(args["effort_tier"]), source="agent")
                    self._service.runtime.save(psm)
                except Exception:
                    pass
            if not str(args.get("intent") or "").strip():
                summary = envelope.setdefault("agent_summary", {})
                advisory = summary.setdefault("advisory", [])
                note = (
                    "intent_missing: pass intent on session_start so coordinator "
                    "can classify greenfield vs hotfix before large UI code"
                )
                if note not in advisory:
                    advisory.append(note)

        # Do NOT mint episodes for unbound session_id on other tools (failed
        # design_review / stale IDs after MCP restart). That created orphan
        # episodes and rebound project/default, poisoning coordinator state.
        if not episode_id and session_id and tool_name != "perception_session_start":
            return envelope

        if not episode_id:
            return envelope

        enriched = self._service.on_tool_envelope(
            episode_id,
            tool_name,
            args,
            envelope,
        )
        if tool_name == "perception_session_start" and enriched.get("ok"):
            self._maybe_schedule_prefetch(
                episode_id=episode_id,
                session_id=session_id or enriched.get("session_id"),
                args=args,
                envelope=enriched,
            )
        elif tool_name == "perception_session_end":
            self._cancel_prefetch(
                episode_id=episode_id,
                session_id=session_id or args.get("session_id"),
            )
        return enriched

    def _maybe_schedule_prefetch(
        self,
        *,
        episode_id: str,
        session_id: str | None,
        args: dict[str, Any],
        envelope: dict[str, Any],
    ) -> None:
        """Fire HTTP prefetch for unpaid heavy-band families (never browser)."""
        try:
            from navigation.coordination_intelligence.planning.episode_prefetch import (
                schedule_episode_prefetch,
            )

            strategy = (envelope.get("data") or {}).get("engineering_strategy") or {}
            if not isinstance(strategy, dict):
                strategy = {}
            face = (envelope.get("agent_summary") or {}).get("card") or {}
            face_class = str(face.get("class") or "")
            evidence_band = str(face.get("evidence_band") or "")
            pack = face.get("pack") if isinstance(face.get("pack"), dict) else {}
            remaining = list(pack.get("remaining") or [])
            intent = str(
                args.get("intent")
                or strategy.get("intent")
                or strategy.get("user_intent")
                or ""
            ).strip()
            if not intent:
                return
            if not face_class:
                # Fallback from task_scope discriminators
                scope = str(strategy.get("task_scope") or "").lower()
                if scope in {"design_driven", "greenfield"}:
                    face_class = "greenfield"
                elif scope == "redesign":
                    face_class = "redesign"
                elif scope in {"hotfix", "debug"}:
                    face_class = "hotfix"
                else:
                    face_class = "feature"
            if not evidence_band:
                if face_class in {"greenfield", "redesign"}:
                    evidence_band = "very_heavy"
                elif face_class in {"hotfix", "forms"}:
                    evidence_band = "light"
                else:
                    evidence_band = "heavy"
            snap = schedule_episode_prefetch(
                episode_id=episode_id,
                session_id=str(session_id) if session_id else None,
                query=intent,
                face_class=face_class,
                evidence_band=evidence_band,
                pack_remaining=remaining,
                repo_root=str(args.get("repo_root") or ""),
                project_id=str(args.get("project_id") or "default"),
            )
            pulse_snap = None
            try:
                from navigation.coordination_intelligence.planning.inspiration_pulse_loop import (
                    schedule_inspiration_pulse,
                )

                pulse_snap = schedule_inspiration_pulse(
                    episode_id=episode_id,
                    session_id=str(session_id) if session_id else None,
                    query=intent,
                    face_class=face_class,
                    evidence_band=evidence_band,
                    repo_root=str(args.get("repo_root") or ""),
                    project_id=str(args.get("project_id") or "default"),
                )
            except Exception:
                pulse_snap = None
            if snap or pulse_snap:
                # Attach pending prefetch / continuous pulse onto the face for this turn.
                summary = envelope.setdefault("agent_summary", {})
                card = summary.get("card")
                if isinstance(card, dict):
                    if snap:
                        card["prefetch"] = snap
                        card["can_parallel"] = list(
                            dict.fromkeys(
                                list(snap.get("can_parallel") or []) + ["inspiration"]
                            )
                        )
                    if pulse_snap:
                        card["inspiration_pulse"] = pulse_snap
                        card["can_parallel"] = list(
                            dict.fromkeys(
                                list(card.get("can_parallel") or []) + ["inspiration"]
                            )
                        )
        except Exception:
            pass

    @staticmethod
    def _cancel_prefetch(
        *,
        episode_id: str | None,
        session_id: str | None,
    ) -> None:
        try:
            from navigation.coordination_intelligence.planning.episode_prefetch import (
                cancel_episode_prefetch,
            )

            cancel_episode_prefetch(episode_id, session_id=session_id)
        except Exception:
            pass
        try:
            from navigation.coordination_intelligence.planning.inspiration_pulse_loop import (
                cancel_inspiration_pulse,
            )

            cancel_inspiration_pulse(episode_id, session_id=session_id)
        except Exception:
            pass

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
        # Only reuse when THIS session already has an episode — never project/default.
        existing = self._bindings.resolve_session(session_id)
        if existing and self._service.runtime.get(existing):
            psm = self._service.runtime.require(existing)
            if website_url:
                psm.artifacts.website_url = website_url
            if repo_root:
                psm.artifacts.repo_root = repo_root
            psm.artifacts.session_id = session_id
            if intent:
                self._service.push_intent(existing, intent)
            else:
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

    def _attach_health_strategy(
        self,
        args: dict[str, Any],
        envelope: dict[str, Any],
    ) -> dict[str, Any]:
        from navigation.coordination_intelligence.planning.engineering_strategy import (
            compile_bootstrap_strategy,
            surface_engineering_strategy,
        )

        catalog = self._service.runtime.bundle.situation_policy_catalog or {}
        intent = args.get("intent")
        strategy = compile_bootstrap_strategy(catalog, intent=str(intent) if intent else None)
        return surface_engineering_strategy(envelope, strategy)


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
