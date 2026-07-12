"""Score validation runs against expected engineering workflows."""

from __future__ import annotations

from typing import Any

from coordination_validation.recorder import DecisionRecorder


def _ratio(matches: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return round(matches / total, 4)


class WorkflowScorer:
    def score(
        self,
        workflow: dict[str, Any],
        recorder: DecisionRecorder,
        *,
        elapsed_ms: int,
        tools_executed: list[str],
        mode: str = "simulate",
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        findings: list[dict[str, Any]] = []
        refinements: list[dict[str, Any]] = []

        expected_caps = workflow.get("expected_capabilities") or []
        expected_tools = set(workflow.get("expected_tools") or [])
        expected_clusters = workflow.get("expected_cluster_sequence") or []
        expected_playbooks = workflow.get("expected_playbook_sequence") or []
        success = workflow.get("success_criteria") or {}

        actual_tools = tools_executed
        unnecessary = [t for t in actual_tools if t not in expected_tools]
        unnecessary_count = len(unnecessary)
        if unnecessary:
            findings.append({
                "type": "unnecessary_tools",
                "severity": "medium" if unnecessary_count <= 2 else "high",
                "detail": unnecessary,
            })
            refinements.append({
                "category": "duplicated_work",
                "workflow_id": workflow["workflow_id"],
                "severity": "medium",
                "description": f"Unexpected tools: {unnecessary}",
            })

        # Capability routing — map tools to capabilities via decisions
        cap_matches = 0
        cap_total = 0
        for d in recorder.decisions:
            if d.expected_capability:
                cap_total += 1
                if d.capability_id == d.expected_capability:
                    cap_matches += 1
                else:
                    findings.append({
                        "type": "capability_mismatch",
                        "step": d.step_index,
                        "expected": d.expected_capability,
                        "actual": d.capability_id,
                    })

        # Playbook selection
        playbook_ids = {d.playbook_id for d in recorder.decisions if d.playbook_id}
        playbook_hits = sum(1 for p in expected_playbooks if p in playbook_ids)
        playbook_accuracy = _ratio(playbook_hits, max(len(expected_playbooks), 1))

        if expected_playbooks and playbook_hits == 0:
            refinements.append({
                "category": "incorrect_playbook_selection",
                "workflow_id": workflow["workflow_id"],
                "severity": "high",
                "description": f"Expected playbooks {expected_playbooks}, saw {sorted(playbook_ids)}",
            })

        # Cluster accuracy
        cluster_ids = [d.cluster_id for d in recorder.decisions if d.cluster_id]
        final_cluster = cluster_ids[-1] if cluster_ids else None
        cluster_hits = sum(1 for c in expected_clusters if c in cluster_ids)
        sequence_cluster_accuracy = _ratio(cluster_hits, max(len(expected_clusters), 1))

        if success.get("final_cluster") and final_cluster != success["final_cluster"]:
            findings.append({
                "type": "final_cluster_mismatch",
                "expected": success["final_cluster"],
                "actual": final_cluster,
            })
            refinements.append({
                "category": "poor_routing",
                "workflow_id": workflow["workflow_id"],
                "severity": "high",
                "description": f"Final cluster {final_cluster} != expected {success['final_cluster']}",
            })

        # Step compilation — in simulate mode the host replays a fixed tool script and does
        # not execute coordinator compiled previews, so comparing compiled_tools to the next
        # scripted tool is not a valid measure of compilation quality.
        compile_matches = 0
        compile_total = 0
        compilation_findings: list[dict[str, Any]] = []
        for i, d in enumerate(recorder.decisions):
            if i + 1 < len(actual_tools):
                next_tool = actual_tools[i + 1]
                compile_total += 1
                if next_tool in d.compiled_tools or not d.compiled_tools:
                    compile_matches += 1
                else:
                    finding = {
                        "type": "compilation_mismatch",
                        "step": d.step_index,
                        "expected_next_tool": next_tool,
                        "compiled": d.compiled_tools,
                    }
                    if mode == "simulate":
                        finding["scope"] = "simulate_host_driven_advisory"
                    compilation_findings.append(finding)

        if mode == "simulate":
            step_compilation_accuracy = None
            step_compilation_scope = "simulate_host_driven_not_scored"
            findings.extend(compilation_findings)
        else:
            step_compilation_accuracy = _ratio(compile_matches, compile_total)
            step_compilation_scope = "live"
            findings.extend(compilation_findings)

        # Governor
        governor_events = sum(1 for d in recorder.decisions if d.governor_advanced)
        governor_expected = len([s for s in workflow.get("simulate_steps", []) if s.get("ok")])
        governor_accuracy = _ratio(governor_events, max(governor_expected - 1, 1))

        if success.get("sequence_invalid_before_valid"):
            completed = recorder.decisions[-1].psm_snapshot.get("completed_step_ids") if recorder.decisions else []
            if completed != ["probe", "invalid_path", "valid_path"]:
                findings.append({
                    "type": "sequence_violation",
                    "expected": ["probe", "invalid_path", "valid_path"],
                    "actual": completed,
                })
                governor_accuracy = min(governor_accuracy, 0.5)

        # Recovery
        recovery_score = 1.0
        failure_recovery = False
        if workflow.get("recovery_expect"):
            for d in recorder.decisions:
                if not d.ok:
                    failure_recovery = True
            if failure_recovery:
                last_suggestion = recorder.decisions[-1].suggested_capability if recorder.decisions else None
                if last_suggestion in ("browser_observe", "runtime_diagnosis", None):
                    recovery_score = 0.8
                else:
                    recovery_score = 0.5
                    refinements.append({
                        "category": "recovery_behavior",
                        "workflow_id": workflow["workflow_id"],
                        "severity": "medium",
                        "description": "Recovery suggestion may not match engineering workflow",
                    })

        # Replanning quality — stop_reason appropriateness
        replanning_quality = 1.0
        for d in recorder.decisions:
            if d.stop_reason and d.stop_reason.startswith("TR_"):
                replanning_quality = 0.9
            if d.stop_reason and "human" in d.stop_reason.lower():
                replanning_quality = 1.0

        # Forbidden capabilities
        for forbidden in workflow.get("forbidden_early_capabilities") or []:
            for d in recorder.decisions[:3]:
                if d.suggested_capability == forbidden:
                    findings.append({
                        "type": "forbidden_capability_suggested",
                        "capability": forbidden,
                        "step": d.step_index,
                    })
                    refinements.append({
                        "category": "poor_routing",
                        "workflow_id": workflow["workflow_id"],
                        "severity": "high",
                        "description": f"Suggested forbidden early capability: {forbidden}",
                    })

        max_unnecessary = success.get("max_unnecessary_tools", 99)
        playbook_complete = success.get("playbook_complete")
        workflow_success = (
            unnecessary_count <= max_unnecessary
            and (not success.get("final_cluster") or final_cluster == success.get("final_cluster"))
            and (not playbook_complete or any(
                d.stop_reason == "playbook_complete" for d in recorder.decisions
            ))
        )

        if success.get("playbook_complete") and not any(
            d.stop_reason == "playbook_complete" for d in recorder.decisions
        ):
            workflow_success = False
            findings.append({"type": "playbook_not_complete"})

        if mode == "simulate":
            # Host-driven replay: cluster telemetry may include cold-start noise or skip
            # transient stages. Outcome alignment (final cluster + playbook) matters more.
            if success.get("final_cluster"):
                cluster_accuracy = (
                    1.0 if final_cluster == success["final_cluster"] else sequence_cluster_accuracy
                )
            elif playbook_accuracy == 1.0 and workflow_success:
                cluster_accuracy = max(sequence_cluster_accuracy, playbook_accuracy)
            else:
                cluster_accuracy = sequence_cluster_accuracy
            cluster_accuracy_scope = "simulate_outcome_weighted"
        else:
            cluster_accuracy = sequence_cluster_accuracy
            cluster_accuracy_scope = "live_sequence"

        # PSM evolution — cluster transitions align with expected sequence
        transitions = recorder.cluster_transitions()
        psm_evolution_score = sequence_cluster_accuracy
        if expected_clusters and len(transitions) > len(expected_clusters) + 1:
            psm_evolution_score *= 0.8
            refinements.append({
                "category": "unnecessary_complexity",
                "workflow_id": workflow["workflow_id"],
                "severity": "low",
                "description": f"Excess cluster transitions: {transitions}",
            })

        metrics = {
            "workflow_id": workflow["workflow_id"],
            "success": workflow_success,
            "psm_evolution_score": psm_evolution_score,
            "cluster_accuracy": cluster_accuracy,
            "cluster_accuracy_scope": cluster_accuracy_scope,
            "cluster_sequence_accuracy": sequence_cluster_accuracy,
            "playbook_accuracy": playbook_accuracy,
            "capability_routing_accuracy": _ratio(cap_matches, max(cap_total, 1)),
            "step_compilation_accuracy": step_compilation_accuracy,
            "step_compilation_scope": step_compilation_scope,
            "step_compilation_advisory_mismatches": len(compilation_findings),
            "governor_accuracy": governor_accuracy,
            "recovery_score": recovery_score,
            "replanning_quality": replanning_quality,
            "unnecessary_tool_calls": unnecessary_count,
            "total_tool_calls": len(actual_tools),
            "elapsed_ms": elapsed_ms,
            "failure_recovery_attempted": failure_recovery,
            "notes": [f["type"] for f in findings],
        }
        return metrics, findings, refinements
