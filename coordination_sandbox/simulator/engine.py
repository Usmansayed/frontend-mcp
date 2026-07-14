"""Simulation engine — evaluates decisions without calling MCP tools."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from coordination_sandbox.brain.bootstrap import apply_capability_effects, bootstrap_project, load_catalog
from coordination_sandbox.brain.effort_allocator import (
    debit_budget,
    evaluate_allocation,
)
from coordination_sandbox.brain.engineering_strategy import compile_engineering_strategy
from coordination_sandbox.brain.playbook_plan import plan_for_scope
from coordination_sandbox.brain.situation_policy import derive_discriminators, match_policy


@dataclass
class DecisionRecord:
    step_index: int
    capability_id: str
    semantic_action: str
    plan_rationale: str
    recommend: bool
    action: str  # accept | skip | stop
    eqg: float
    cost: int
    roi: float
    roi_threshold: float
    budget_remaining: int
    budget_total: int
    estimated_latency_ms: int
    engineering_value: float
    stop_reason: str | None
    routing_rationale: str
    benefit_claim: str
    effects: list[str] = field(default_factory=list)
    policy_id: str = ""
    investment_band: str = ""
    visual_impact_ceiling: str = ""
    discriminators: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    prompt: str
    project_state: dict[str, Any]
    lifecycle_stage: str
    situation_policy_id: str
    initial_situation_policy_id: str
    investment_band: str
    engineering_investment_b_base: int
    visual_impact_ceiling: str
    budget_total: int
    budget_spent: int
    budget_remaining: int
    recommended_playbook: str
    playbook_reason: str
    recommended_capabilities: list[str]
    recommended_semantic_actions: list[str]
    skipped: list[dict[str, Any]]
    stop_recommendations: list[str]
    diminishing_returns: list[str]
    estimated_latency_ms_total: int
    estimated_engineering_value: float
    design_oriented: bool
    discriminators: dict[str, str]
    initial_discriminators: dict[str, str]
    decision_trace: list[dict[str, Any]]
    tech_lead_summary: str
    engineering_strategy_initial: dict[str, Any]
    engineering_strategy_final: dict[str, Any]
    influence_level_initial: str
    influence_level_final: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def simulate_prompt(
    prompt: str,
    *,
    catalog: dict[str, Any] | None = None,
    existing_product: bool | None = None,
    max_steps: int = 24,
) -> ScenarioResult:
    """Run a full coordination decision episode for one engineering prompt."""
    catalog = catalog or load_catalog()
    existing = (
        existing_product
        if existing_product is not None
        else any(k in prompt.lower() for k in ("existing", "improve this", "hotfix", "production"))
    )
    psm = bootstrap_project(prompt, existing_product=existing)

    disc0 = derive_discriminators(psm)
    policy0 = match_policy(catalog, disc0)
    inv0 = policy0.get("investment") or {}
    evaluate_allocation(psm, catalog, capability_id=None)
    strategy_initial = compile_engineering_strategy(psm, catalog).to_dict()

    plan = plan_for_scope(disc0["task_scope"], prompt)

    records: list[DecisionRecord] = []
    recommended_caps: list[str] = []
    recommended_actions: list[str] = []
    skipped: list[dict[str, Any]] = []
    stop_recs: list[str] = []
    dr_flags: list[str] = []
    value = 0.0
    latency_total = 0
    consecutive_skips = 0

    initial_policy_id = str(policy0.get("policy_id"))
    initial_b_base = int(inv0.get("B_base") or 14)
    initial_ceiling = str(inv0.get("visual_impact_ceiling") or "V3")
    initial_band = disc0["lifecycle_band"]

    for idx, step in enumerate(plan.steps[:max_steps], start=1):
        decision = evaluate_allocation(psm, catalog, capability_id=step.capability_id)
        action = "accept" if decision.recommend else "skip"

        # Hard STOP when verify already sufficient and remaining are polish
        if decision.stop_reason in (
            "verify_passed_sufficient",
            "budget_exhausted",
            "diminishing_returns_hard",
        ):
            action = "stop" if not decision.recommend else action
            stop_recs.append(f"{step.capability_id}: {decision.stop_reason}")

        if decision.stop_reason in ("roi_below_threshold", "diminishing_returns_soft", "diminishing_returns_hard"):
            dr_flags.append(f"{step.capability_id}: {decision.stop_reason}")

        effects: list[str] = []
        if action == "accept":
            debit_budget(psm, decision.cost, step.capability_id)
            effects = apply_capability_effects(psm, step.capability_id)
            recommended_caps.append(step.capability_id)
            recommended_actions.append(step.semantic_action)
            value += decision.eqg
            latency_total += decision.estimated_latency_ms
            consecutive_skips = 0
            # Refresh budget counters after debit
            spent = int(psm.episode.retry_counters.get("intelligence_spent") or 0)
            total = int(psm.episode.retry_counters.get("intelligence_budget_total") or 0)
            rem = max(0, total - spent)
        else:
            skipped.append(
                {
                    "capability_id": step.capability_id,
                    "semantic_action": step.semantic_action,
                    "reason": decision.stop_reason or "not_recommended",
                    "routing_rationale": decision.routing_rationale,
                    "eqg": decision.eqg,
                    "roi": round(decision.roi, 3),
                    "cost": decision.cost,
                }
            )
            consecutive_skips += 1
            spent = decision.budget_spent
            total = decision.budget_total
            rem = decision.budget_remaining

        records.append(
            DecisionRecord(
                step_index=idx,
                capability_id=step.capability_id,
                semantic_action=step.semantic_action,
                plan_rationale=step.rationale,
                recommend=decision.recommend,
                action=action,
                eqg=decision.eqg,
                cost=decision.cost,
                roi=round(decision.roi, 3),
                roi_threshold=decision.roi_threshold,
                budget_remaining=rem,
                budget_total=total,
                estimated_latency_ms=decision.estimated_latency_ms,
                engineering_value=decision.eqg if action == "accept" else 0.0,
                stop_reason=decision.stop_reason,
                routing_rationale=decision.routing_rationale,
                benefit_claim=decision.benefit_claim,
                effects=effects,
                policy_id=decision.policy_id,
                investment_band=decision.investment_band,
                visual_impact_ceiling=decision.visual_impact_ceiling,
                discriminators=dict(decision.discriminators),
            )
        )

        if action == "stop" or (
            psm.episode.verification_status == "passed" and consecutive_skips >= 2
        ):
            stop_recs.append("episode_stop: verification satisfied or stop bias")
            break

    # Final snapshot
    disc_f = derive_discriminators(psm)
    policy_f = match_policy(catalog, disc_f)
    spent_f = int(psm.episode.retry_counters.get("intelligence_spent") or 0)
    total_f = int(psm.episode.retry_counters.get("intelligence_budget_total") or 0)

    design_oriented = disc_f["task_scope"] in ("design_driven", "redesign", "system_setup") and any(
        c in recommended_caps
        for c in ("inspiration_workflow", "component_select", "design_review", "design_snapshot")
    )

    strategy_final = compile_engineering_strategy(psm, catalog).to_dict()

    summary = _tech_lead_summary(
        prompt=prompt,
        disc=disc_f,
        policy_id=str(policy_f.get("policy_id")),
        accepted=recommended_caps,
        skipped=skipped,
        budget_spent=spent_f,
        budget_total=total_f,
        value=value,
        design_oriented=design_oriented,
        stop_recs=stop_recs,
        strategy=strategy_final,
    )

    return ScenarioResult(
        prompt=prompt,
        project_state={
            "situation_class": psm.situation.situation_class,
            "project_maturity": psm.situation.project_maturity,
            "cluster_id": psm.situation.cluster_id,
            "verification_status": psm.episode.verification_status,
            "evidence_postures": {k: v.posture for k, v in psm.evidence.domains.items()},
            "scan_id": psm.artifacts.scan_id,
            "intent_stack": [f.intent for f in psm.episode.intent_stack],
        },
        lifecycle_stage=psm.situation.lifecycle_stage,
        situation_policy_id=str(policy_f.get("policy_id")),
        initial_situation_policy_id=initial_policy_id,
        investment_band=initial_band,
        engineering_investment_b_base=initial_b_base,
        visual_impact_ceiling=initial_ceiling,
        budget_total=total_f,
        budget_spent=spent_f,
        budget_remaining=max(0, total_f - spent_f),
        recommended_playbook=plan.playbook_id,
        playbook_reason=plan.reason,
        recommended_capabilities=recommended_caps,
        recommended_semantic_actions=recommended_actions,
        skipped=skipped,
        stop_recommendations=list(dict.fromkeys(stop_recs)),
        diminishing_returns=list(dict.fromkeys(dr_flags)),
        estimated_latency_ms_total=latency_total,
        estimated_engineering_value=round(value, 2),
        design_oriented=design_oriented,
        discriminators=disc_f,
        initial_discriminators=disc0,
        decision_trace=[r.to_dict() for r in records],
        tech_lead_summary=summary,
        engineering_strategy_initial=strategy_initial,
        engineering_strategy_final=strategy_final,
        influence_level_initial=strategy_initial.get("influence_level", "unknown"),
        influence_level_final=strategy_final.get("influence_level", "unknown"),
    )


def _tech_lead_summary(
    *,
    prompt: str,
    disc: dict[str, str],
    policy_id: str,
    accepted: list[str],
    skipped: list[dict[str, Any]],
    budget_spent: int,
    budget_total: int,
    value: float,
    design_oriented: bool,
    stop_recs: list[str],
    strategy: dict[str, Any] | None = None,
) -> str:
    skip_names = [s["capability_id"] for s in skipped]
    heavy_skipped = [
        c
        for c in ("inspiration_workflow", "design_review", "seo_evidence_collect", "resource_workflow")
        if c in skip_names
    ]
    parts = [
        f"For '{prompt}' scope={disc.get('task_scope')} band={disc.get('lifecycle_band')} policy={policy_id}.",
    ]
    if strategy:
        parts.append(
            f"Influence={strategy.get('influence_level')} phase={strategy.get('engineering_phase')}. "
            f"{strategy.get('summary', '')}"
        )
        unresolved = strategy.get("unresolved_decisions") or []
        if unresolved:
            parts.append(f"Top decision: {unresolved[0].get('title')}.")
    parts.extend([
        f"Invested {budget_spent}/{budget_total} intelligence units for ~{value:.1f} EQG.",
        (
            "Entered a design-oriented workflow."
            if design_oriented
            else "Stayed correctness / incremental (not design-heavy)."
        ),
    ])
    if heavy_skipped:
        parts.append(f"Suppressed expensive work: {', '.join(heavy_skipped)}.")
    if stop_recs:
        parts.append(f"STOP signals: {'; '.join(stop_recs[:3])}.")
    parts.append("Goal: maximum frontend quality per second, not maximum tool usage.")
    return " ".join(parts)
