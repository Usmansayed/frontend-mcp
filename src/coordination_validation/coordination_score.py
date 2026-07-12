"""Aggregate Coordination Score across validation workflows."""

from __future__ import annotations

from typing import Any

RELEASE_TARGETS = {
    "cluster_accuracy": 0.95,
    "capability_routing_accuracy": 0.95,
    "playbook_selection_accuracy": 0.95,
    "step_compilation_accuracy": 0.95,
    "recovery_quality": 0.95,
    "replanning_quality": 0.95,
    "tool_efficiency": 0.95,
    "overall_workflow_success": 0.95,
    "max_unnecessary_tool_rate": 0.05,
    "critical_recovery_failures": 0,
}


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _tool_efficiency(workflows: list[dict[str, Any]]) -> float:
    total_calls = sum(w["metrics"]["total_tool_calls"] for w in workflows)
    unnecessary = sum(w["metrics"]["unnecessary_tool_calls"] for w in workflows)
    if total_calls <= 0:
        return 1.0
    return round(1.0 - (unnecessary / total_calls), 4)


def _critical_recovery_failures(workflows: list[dict[str, Any]]) -> int:
    failures = 0
    for wf in workflows:
        metrics = wf["metrics"]
        if metrics.get("failure_recovery_attempted") and metrics.get("recovery_score", 1.0) < 0.8:
            failures += 1
    return failures


def _mean_optional(values: list[Any]) -> float | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def build_coordination_score(workflows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute global coordination score from per-workflow metrics."""
    if not workflows:
        return {
            "categories": {},
            "composite": 0.0,
            "release_targets": RELEASE_TARGETS,
            "release_targets_met": False,
            "critical_recovery_failures": 0,
        }

    categories = {
        "cluster_accuracy": _mean([w["metrics"]["cluster_accuracy"] for w in workflows]),
        "capability_routing_accuracy": _mean(
            [w["metrics"]["capability_routing_accuracy"] for w in workflows]
        ),
        "playbook_selection_accuracy": _mean(
            [w["metrics"]["playbook_accuracy"] for w in workflows]
        ),
        "step_compilation_accuracy": _mean_optional(
            [w["metrics"].get("step_compilation_accuracy") for w in workflows]
        ),
        "recovery_quality": _mean([w["metrics"]["recovery_score"] for w in workflows]),
        "replanning_quality": _mean([w["metrics"]["replanning_quality"] for w in workflows]),
        "tool_efficiency": _tool_efficiency(workflows),
        "overall_workflow_success": round(
            sum(1 for w in workflows if w["metrics"]["success"]) / len(workflows),
            4,
        ),
    }

    scored_categories = {k: v for k, v in categories.items() if v is not None}
    composite = round(
        sum(scored_categories.values()) / len(scored_categories),
        4,
    ) if scored_categories else 0.0

    unnecessary_rate = 1.0 - categories["tool_efficiency"]
    critical_failures = _critical_recovery_failures(workflows)

    release_targets_met = (
        categories["cluster_accuracy"] >= RELEASE_TARGETS["cluster_accuracy"]
        and categories["capability_routing_accuracy"]
        >= RELEASE_TARGETS["capability_routing_accuracy"]
        and categories["playbook_selection_accuracy"]
        >= RELEASE_TARGETS["playbook_selection_accuracy"]
        and categories["overall_workflow_success"] >= RELEASE_TARGETS["overall_workflow_success"]
        and unnecessary_rate <= RELEASE_TARGETS["max_unnecessary_tool_rate"]
        and critical_failures <= RELEASE_TARGETS["critical_recovery_failures"]
    )

    return {
        "categories": categories,
        "composite": composite,
        "measurement_scope": {
            "step_compilation_accuracy": "not_scored_in_simulate_host_driven_replay",
            "cluster_accuracy": "simulate_outcome_weighted_when_applicable",
            "cluster_sequence_accuracy": "raw_telemetry_sequence_membership_per_workflow",
        },
        "release_targets": RELEASE_TARGETS,
        "release_targets_met": release_targets_met,
        "critical_recovery_failures": critical_failures,
        "unnecessary_tool_rate": round(unnecessary_rate, 4),
    }
