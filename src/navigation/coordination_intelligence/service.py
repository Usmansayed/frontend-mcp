"""Coordination Intelligence service — advisory coordinator over PSM Runtime."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle, load_runtime_artifacts
from navigation.coordination_intelligence.models import (
    CompiledStep,
    CoordinatorBriefing,
    ProjectSituationModel,
)
from navigation.coordination_intelligence.planning.capability_router import CapabilityRouter
from navigation.coordination_intelligence.planning.cluster_resolver import ClusterResolver
from navigation.coordination_intelligence.planning.loop_governor import LoopGovernor
from navigation.coordination_intelligence.planning.playbook_selector import PlaybookSelector
from navigation.coordination_intelligence.planning.step_compiler import StepCompiler
from navigation.coordination_intelligence.psm.runtime import PSMRuntime
from navigation.coordination_intelligence.psm.signature import refresh_cluster_signature

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "form_invalid_criteria": {
        "text_contains": ["required", "invalid"],
    },
    "form_valid_criteria": {
        "text_absent": ["required", "invalid"],
    },
}


class CoordinationIntelligenceService:
    """Deterministic coordinator. Host LLM reasons; this orchestrates and advises."""

    def __init__(
        self,
        *,
        runtime: PSMRuntime | None = None,
        bundle: RuntimeArtifactBundle | None = None,
    ) -> None:
        self._bundle = bundle or load_runtime_artifacts()
        self._runtime = runtime or PSMRuntime(self._bundle)
        self._router = CapabilityRouter(self._bundle)
        self._selector = PlaybookSelector(self._bundle)
        self._compiler = StepCompiler(self._bundle)
        self._governor = LoopGovernor(self._bundle)
        self._cluster_resolver = ClusterResolver(self._bundle)

    @property
    def runtime(self) -> PSMRuntime:
        return self._runtime

    def episode_start(self, **kwargs: Any) -> ProjectSituationModel:
        psm = self._runtime.create_episode(**kwargs)
        self._cluster_resolver.resolve(psm)
        self._refresh_briefing(psm)
        self._runtime.save(psm)
        return psm

    def apply_envelope(
        self,
        episode_id: str,
        envelope: dict[str, Any],
        *,
        capability_id: str | None = None,
        step_context: dict[str, Any] | None = None,
    ) -> CoordinatorBriefing:
        tool_name = str(envelope.get("tool") or "")
        args: dict[str, Any] = {"step_context": step_context or {}}
        if capability_id:
            args["capability_id"] = capability_id
        self.on_tool_envelope(
            episode_id,
            tool_name,
            args,
            envelope,
            capability_hint=capability_id,
        )
        return self.briefing(episode_id, step_context=step_context)

    def on_tool_envelope(
        self,
        episode_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        envelope: dict[str, Any],
        *,
        capability_hint: str | None = None,
    ) -> dict[str, Any]:
        """Normalize tool envelope into PSM, resolve cluster, advance playbook, refresh briefing."""
        psm = self._runtime.require(episode_id)
        capability_id = capability_hint or self._bundle.tool_to_capability.get(tool_name)

        psm.episode.retry_counters["last_tool"] = tool_name
        if capability_id:
            psm.episode.retry_counters["last_capability"] = capability_id

        self._runtime.apply_envelope(episode_id, envelope, capability_id=capability_id)
        psm = self._runtime.require(episode_id)

        self._cluster_resolver.resolve(psm)
        self._governor.advance_if_satisfied(
            psm,
            capability_id=capability_id,
            envelope=envelope,
        )

        step_context = self._extract_step_context(arguments)
        self._refresh_briefing(psm, step_context=step_context)
        self._runtime.save(psm)

        briefing = self._to_briefing(psm)
        return self._enrich_envelope(envelope, briefing)

    def briefing(
        self,
        episode_id: str,
        *,
        step_context: dict[str, Any] | None = None,
    ) -> CoordinatorBriefing:
        psm = self._runtime.require(episode_id)
        self._cluster_resolver.resolve(psm)
        self._refresh_briefing(psm, step_context=step_context)
        self._runtime.save(psm)
        return self._to_briefing(psm)

    def get_psm(self, episode_id: str) -> dict[str, Any]:
        return self._runtime.require(episode_id).to_dict()

    @staticmethod
    def _extract_step_context(arguments: dict[str, Any]) -> dict[str, Any]:
        ctx = arguments.get("step_context")
        if isinstance(ctx, dict):
            out = dict(ctx)
        else:
            out = {}
        if "criteria" in arguments and "criteria" not in out:
            out["criteria"] = arguments["criteria"]
        return out

    @staticmethod
    def _enrich_envelope(
        envelope: dict[str, Any],
        briefing: CoordinatorBriefing,
    ) -> dict[str, Any]:
        data = envelope.setdefault("data", {})
        data["coordinator"] = {
            "episode_id": briefing.episode_id,
            "briefing": briefing.to_dict(),
            "integrated": True,
            "suggested_capability": briefing.suggested_capability,
            "suggested_semantic_action": briefing.suggested_semantic_action,
            "stop_reason": briefing.stop_reason,
            "psm_summary": briefing.psm_summary,
        }
        return envelope

    def _refresh_briefing(
        self,
        psm: ProjectSituationModel,
        *,
        step_context: dict[str, Any] | None = None,
    ) -> None:
        stop = self._governor.should_stop(psm)
        if stop:
            psm.briefing.stop_reason = stop
            psm.briefing.suggested_next_capability = None
            psm.briefing.suggested_semantic_action = None
            psm.briefing.compiled_step_preview = None
            return

        self._router.compute_capability_posture(psm)
        refresh_cluster_signature(psm)

        playbook_id = self._selector.select_playbook_id(psm)
        step = self._selector.current_step(psm)
        if not step:
            psm.briefing.stop_reason = "playbook_complete"
            psm.briefing.suggested_next_capability = None
            psm.briefing.suggested_semantic_action = None
            psm.briefing.compiled_step_preview = None
            return

        if step.get("host_llm_only"):
            psm.briefing.suggested_next_capability = None
            psm.briefing.suggested_semantic_action = step.get("semantic_action")
            psm.briefing.compiled_step_preview = None
            psm.briefing.stop_reason = None
            return

        capability_id = step.get("capability")
        semantic_action = step.get("semantic_action")
        if not capability_id or not semantic_action:
            return

        gate = self._router.gate(psm, capability_id)
        if not gate.allowed:
            psm.briefing.stop_reason = gate.reason
            psm.briefing.suggested_next_capability = gate.gather_first
            psm.briefing.suggested_semantic_action = None
            psm.briefing.compiled_step_preview = None
            return

        ctx = dict(step_context or {})
        ref = step.get("success_criteria_ref")
        if ref and "criteria" not in ctx:
            ctx["criteria"] = DEFAULT_CRITERIA.get(ref, {"ref": ref})

        compiled = self._compiler.compile_step(
            psm,
            semantic_action=semantic_action,
            capability_id=capability_id,
            step_id=step.get("step_id"),
            step_context=ctx,
            playbook_id=playbook_id,
        )

        psm.briefing.stop_reason = None
        psm.briefing.suggested_next_capability = capability_id
        psm.briefing.suggested_semantic_action = semantic_action
        psm.briefing.compiled_step_preview = compiled.to_dict() if compiled else None

    def _to_briefing(self, psm: ProjectSituationModel) -> CoordinatorBriefing:
        preview = psm.briefing.compiled_step_preview
        compiled = None
        if preview:
            compiled = CompiledStep(
                capability_id=preview["capability_id"],
                semantic_action=preview["semantic_action"],
                step_id=preview.get("step_id"),
                tools=preview.get("tools") or [],
                playbook_id=preview.get("playbook_id"),
            )
        return CoordinatorBriefing(
            episode_id=psm.episode_id,
            stop_reason=psm.briefing.stop_reason,
            suggested_capability=psm.briefing.suggested_next_capability,
            suggested_semantic_action=psm.briefing.suggested_semantic_action,
            compiled_step=compiled,
            psm_summary={
                "cluster_id": psm.situation.cluster_id,
                "lifecycle_stage": psm.situation.lifecycle_stage,
                "active_playbook_id": psm.episode.active_playbook_id,
                "active_step_id": psm.episode.active_step_id,
                "completed_step_ids": list(psm.episode.completed_step_ids),
                "verification_status": psm.episode.verification_status,
                "auth_status": psm.episode.auth_status,
                "blocking_count": len(psm.evidence.blocking),
                "last_capability": psm.episode.retry_counters.get("last_capability"),
            },
        )
