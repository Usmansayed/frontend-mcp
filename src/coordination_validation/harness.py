"""Validation harness — run workflows through CoordinatorBridge and score."""

from __future__ import annotations

import time
from typing import Any

from navigation.coordination_intelligence.integration.bridge import CoordinatorBridge
from navigation.coordination_intelligence.integration.episode_binding import EpisodeBindingStore
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope

from coordination_validation.coordination_score import build_coordination_score
from coordination_validation.recorder import DecisionRecorder
from coordination_validation.scorer import WorkflowScorer
from coordination_validation.workflows import load_workflows, workflow_by_id


class ValidationHarness:
    """Execute validation workflows in simulate mode (deterministic envelope replay)."""

    def __init__(self, bridge: CoordinatorBridge | None = None) -> None:
        bindings = EpisodeBindingStore()
        service = CoordinationIntelligenceService()
        self._bridge = bridge or CoordinatorBridge(service=service, bindings=bindings)
        self._scorer = WorkflowScorer()

    def run_all(self, *, mode: str = "simulate") -> dict[str, Any]:
        workflows = load_workflows().get("workflows", [])
        results = []
        all_refinements: list[dict[str, Any]] = []
        for wf in workflows:
            result = self.run_workflow(wf["workflow_id"], mode=mode)
            results.append(result)
            all_refinements.extend(result.get("refinements") or [])

        passed = sum(1 for r in results if r["metrics"]["success"])
        n = len(results)
        report = {
            "suite_version": "1.0.0",
            "mode": mode,
            "workflows": results,
            "summary": {
                "total": n,
                "passed": passed,
                "failed": n - passed,
                "skipped": 0,
                "mean_cluster_accuracy": _mean(r["metrics"]["cluster_accuracy"] for r in results),
                "mean_playbook_accuracy": _mean(r["metrics"]["playbook_accuracy"] for r in results),
                "mean_capability_routing_accuracy": _mean(
                    r["metrics"]["capability_routing_accuracy"] for r in results
                ),
                "total_unnecessary_tool_calls": sum(
                    r["metrics"]["unnecessary_tool_calls"] for r in results
                ),
            },
            "coordination_score": build_coordination_score(results),
            "refinement_opportunities": _dedupe_refinements(all_refinements),
        }
        return report

    def run_workflow(self, workflow_id: str, *, mode: str = "simulate") -> dict[str, Any]:
        wf = workflow_by_id(workflow_id)
        if not wf:
            raise KeyError(f"Unknown workflow: {workflow_id}")

        if mode != "simulate":
            raise NotImplementedError("Live mode delegates to existing eval runners per workflow")

        return self._run_simulate(wf)

    def _run_simulate(self, workflow: dict[str, Any]) -> dict[str, Any]:
        # Fresh bridge per workflow for isolation
        bindings = EpisodeBindingStore()
        service = CoordinationIntelligenceService()
        bridge = CoordinatorBridge(service=service, bindings=bindings)

        recorder = DecisionRecorder()
        tools_executed: list[str] = []
        expected_caps = workflow.get("expected_capabilities") or []

        session_id = f"val_{workflow['workflow_id'].lower()}"
        start = time.perf_counter()

        for idx, step in enumerate(workflow.get("simulate_steps") or []):
            tool = step["tool"]
            ok = bool(step.get("ok", True))
            data = dict(step.get("envelope_data") or {})
            data.setdefault("agent_summary", {"blocking": [], "advisory": []})

            args: dict[str, Any] = {"session_id": session_id}
            if tool == "perception_session_start":
                args = {"base_url": "http://localhost:5173"}
            if tool in ("perception_detect_framework", "perception_framework_docs", "perception_code_context"):
                args = {"repo_root": "/tmp/val-repo", "session_id": session_id}

            envelope = make_envelope(tool, ok=ok, session_id=session_id, data=data)
            if tool == "perception_session_start" and ok:
                envelope["url"] = "http://localhost:5173"

            psm_before = {}
            episode_id = bindings.resolve(session_id=session_id)
            if episode_id:
                try:
                    completed_before = list(
                        service.runtime.require(episode_id).episode.completed_step_ids
                    )
                    psm_before = service.get_psm(episode_id)
                except KeyError:
                    completed_before = []
            else:
                completed_before = []

            out = bridge.process(tool, args, envelope)
            tools_executed.append(tool)

            episode_id = bindings.resolve(session_id=session_id)
            psm = service.get_psm(episode_id) if episode_id else {}
            completed_after = list((psm.get("episode") or {}).get("completed_step_ids") or [])
            governor_advanced = len(completed_after) > len(completed_before)

            expected_cap = service.runtime.bundle.tool_to_capability.get(tool)
            if expected_cap is None and idx < len(expected_caps):
                expected_cap = expected_caps[idx]

            actual_cap = service.runtime.bundle.tool_to_capability.get(tool)
            recorder.record(
                step_index=idx,
                tool=tool,
                envelope=out,
                psm=psm,
                expected_capability=expected_cap,
                capability_id=actual_cap,
                governor_advanced=governor_advanced,
            )

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        metrics, findings, refinements = self._scorer.score(
            workflow,
            recorder,
            elapsed_ms=elapsed_ms,
            tools_executed=tools_executed,
            mode="simulate",
        )

        return {
            "workflow_id": workflow["workflow_id"],
            "title": workflow.get("title"),
            "engineering_goal": workflow.get("engineering_goal"),
            "modules": workflow.get("modules"),
            "metrics": metrics,
            "decisions": [d.to_dict() for d in recorder.decisions],
            "findings": findings,
            "refinements": refinements,
            "psm_timeline": recorder.psm_timeline(),
            "cluster_transitions": [
                {"from": a, "to": b} for a, b in recorder.cluster_transitions()
            ],
        }


def _mean(values: Any) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 4)


def _dedupe_refinements(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = f"{item.get('workflow_id')}:{item.get('category')}:{item.get('description')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
