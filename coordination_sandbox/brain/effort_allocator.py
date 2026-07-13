"""Engineering Investment allocator — SANDBOX COPY.

Vendored from production planning/effort_allocator.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from coordination_sandbox.brain.models import ProjectSituationModel, posture_meets_min
from coordination_sandbox.brain.situation_policy import (
    capability_cost,
    derive_discriminators,
    match_policy,
)

VISUAL_RANK = {"V1": 1, "V2": 2, "V3": 3, "V4": 4}

_HEAVY_SET = frozenset(
    {
        "inspiration_workflow",
        "design_review",
        "design_consistency_audit",
        "seo_evidence_collect",
        "quality_audit",
        "resource_workflow",
        "design_snapshot",
    }
)

# Rough wall-clock latency estimates (ms) for decision reporting — not MCP execution.
_LATENCY_MS_PER_COST = 280


@dataclass
class AllocationDecision:
    policy_id: str
    discriminators: dict[str, str]
    budget_total: int
    budget_spent: int
    budget_remaining: int
    visual_impact_ceiling: str
    eqg: float
    cost: int
    roi: float
    roi_threshold: float
    recommend: bool
    stop_reason: str | None = None
    routing_rationale: str = ""
    benefit_claim: str = ""
    skip_condition: str = ""
    investment_band: str = "mid"
    policy: dict[str, Any] = field(default_factory=dict)
    estimated_latency_ms: int = 0

    @property
    def engineering_value(self) -> float:
        return self.eqg if self.recommend else 0.0


def evaluate_allocation(
    psm: ProjectSituationModel,
    catalog: dict[str, Any],
    *,
    capability_id: str | None,
) -> AllocationDecision:
    disc = derive_discriminators(psm)
    policy = match_policy(catalog, disc)
    investment = policy.get("investment") or {}
    b_base = int(investment.get("B_base") or 14)
    ceiling = str(investment.get("visual_impact_ceiling") or "V3")

    spent = int(psm.episode.retry_counters.get("intelligence_spent") or 0)
    total = int(psm.episode.retry_counters.get("intelligence_budget_total") or 0)
    if total <= 0:
        total = b_base
        psm.episode.retry_counters["intelligence_budget_total"] = total
    remaining = max(0, total - spent)

    forbid = set(investment.get("forbid_or_defer") or [])
    allow_heavy = set(investment.get("allow_heavy") or [])
    eqg_priors = policy.get("eqg_priors") or {}
    saturation = disc.get("polish_saturation") or "none"
    thresholds = catalog.get("roi_threshold_by_saturation") or {}
    roi_threshold = float(thresholds.get(saturation, 0.35))

    investment_band = disc.get("lifecycle_band") or "mid"
    policy_id = str(policy.get("policy_id") or "default.fallback")

    if not capability_id:
        return AllocationDecision(
            policy_id=policy_id,
            discriminators=disc,
            budget_total=total,
            budget_spent=spent,
            budget_remaining=remaining,
            visual_impact_ceiling=ceiling,
            eqg=0.0,
            cost=0,
            roi=0.0,
            roi_threshold=roi_threshold,
            recommend=False,
            routing_rationale=f"policy={policy_id}; waiting on host/playbook step",
            investment_band=investment_band,
            policy=policy,
            estimated_latency_ms=0,
        )

    cost = capability_cost(catalog, capability_id)
    if capability_id == "browser_observe" and _observe_satisfied(psm):
        cost = 0

    eqg = float(eqg_priors.get(capability_id, 4))
    eqg = _adjust_eqg(eqg, capability_id, psm, disc)
    roi = eqg / max(cost, 0.5)
    latency = int(cost * _LATENCY_MS_PER_COST)

    stop_reason: str | None = None
    recommend = True
    benefit = f"EQG≈{eqg:.1f} for {capability_id} under {policy_id}"
    skip = "Skip if host already has equivalent evidence in context."
    rationale_parts = [
        f"policy={policy_id}",
        f"band={investment_band}",
        f"scope={disc.get('task_scope')}",
        f"impact_ceiling={ceiling}",
        f"budget={remaining}/{total}",
        f"eqg={eqg:.1f}",
        f"cost={cost}",
        f"roi={roi:.2f}",
        f"threshold={roi_threshold:.2f}",
        f"est_latency_ms={latency}",
    ]

    stop_bias = policy.get("stop_bias") or ""
    if (
        stop_bias == "verify_passed_sufficient"
        and psm.episode.verification_status == "passed"
        and not psm.evidence.blocking
        and capability_id not in ("browser_verify", "browser_diff", "browser_observe")
    ):
        recommend = False
        stop_reason = "verify_passed_sufficient"
        rationale_parts.append("verify already passed; further design spend low ROI")

    if capability_id in forbid:
        recommend = False
        stop_reason = stop_reason or "policy_forbid_capability"
        rationale_parts.append(f"{capability_id} deferred/forbidden by policy")
        benefit = f"Avoid {capability_id} — low value in this situation"

    if (
        capability_id in _HEAVY_SET
        and capability_id not in allow_heavy
        and VISUAL_RANK.get(ceiling, 3) <= 2
    ):
        recommend = False
        stop_reason = stop_reason or "impact_ceiling_suppresses_heavy"
        rationale_parts.append(f"ceiling {ceiling} blocks heavy {capability_id}")

    if remaining < cost and cost > 0:
        recommend = False
        stop_reason = stop_reason or "budget_exhausted"
        rationale_parts.append("intelligence budget exhausted")

    if roi < roi_threshold and cost > 0:
        recommend = False
        stop_reason = stop_reason or "roi_below_threshold"
        rationale_parts.append("ROI below threshold (diminishing returns / low VoI)")

    if saturation == "hard" and capability_id in ("design_review", "inspiration_workflow"):
        recommend = False
        stop_reason = "diminishing_returns_hard"
        rationale_parts.append("polish saturation hard — stop design loops")

    if saturation == "soft" and capability_id == "inspiration_workflow":
        recommend = False
        stop_reason = stop_reason or "diminishing_returns_soft"
        rationale_parts.append("polish saturation soft — skip more inspiration")

    return AllocationDecision(
        policy_id=policy_id,
        discriminators=disc,
        budget_total=total,
        budget_spent=spent,
        budget_remaining=remaining,
        visual_impact_ceiling=ceiling,
        eqg=eqg,
        cost=cost,
        roi=roi,
        roi_threshold=roi_threshold,
        recommend=recommend,
        stop_reason=stop_reason,
        routing_rationale="; ".join(rationale_parts),
        benefit_claim=benefit,
        skip_condition=skip,
        investment_band=investment_band,
        policy=policy,
        estimated_latency_ms=latency,
    )


def _observe_satisfied(psm: ProjectSituationModel) -> bool:
    if not psm.artifacts.scan_id:
        return False
    ui = psm.evidence.domains.get("ui_runtime")
    return ui is not None and posture_meets_min(ui.posture, "partial")


def _adjust_eqg(
    eqg: float,
    capability_id: str,
    psm: ProjectSituationModel,
    disc: dict[str, str],
) -> float:
    attempts = psm.episode.retry_counters.get("capability_attempts") or {}
    n = int(attempts.get(capability_id, 0))
    if n >= 1:
        eqg *= 0.55 if n == 1 else 0.25
    if capability_id == "inspiration_workflow" and disc.get("design_reference_posture") in (
        "inspiration",
        "figma",
        "agreed_with_refs",
    ):
        eqg *= 0.15
    if capability_id == "design_review":
        reviews = int(attempts.get("design_review", 0))
        if reviews >= 2:
            eqg *= 0.3
        if not psm.artifacts.scan_id:
            eqg *= 0.2
    if capability_id == "browser_observe" and _observe_satisfied(psm):
        eqg *= 0.2
    return round(eqg, 2)


def debit_budget(psm: ProjectSituationModel, cost: int, capability_id: str | None) -> None:
    if cost <= 0:
        return
    spent = int(psm.episode.retry_counters.get("intelligence_spent") or 0)
    psm.episode.retry_counters["intelligence_spent"] = spent + cost
    if capability_id == "design_review":
        loops = int(psm.episode.retry_counters.get("polish_loops") or 0) + 1
        psm.episode.retry_counters["polish_loops"] = loops
        if loops >= 3:
            psm.episode.retry_counters["polish_saturation"] = "hard"
        elif loops >= 2:
            psm.episode.retry_counters["polish_saturation"] = "soft"
