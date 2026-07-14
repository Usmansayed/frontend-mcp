"""Engineering Strategy — decision-centric coordinator output (deterministic, no LLM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from navigation.coordination_intelligence.models import ProjectSituationModel, posture_meets_min
from navigation.coordination_intelligence.planning.effort_allocator import evaluate_allocation
from navigation.coordination_intelligence.planning.situation_policy import (
    derive_discriminators,
    lifecycle_band,
    match_policy,
)

INFLUENCE_LEVELS = ("structural", "balanced", "minimal", "maintenance")

ENGINEERING_PHASES = (
    "design_orientation",
    "architecture",
    "implementation",
    "verification",
    "quality",
    "polish",
    "hotfix_remediation",
    "maintenance",
)

AppliesFn = Callable[[dict[str, str], ProjectSituationModel], bool]


@dataclass
class UnresolvedDecision:
    decision_id: str
    title: str
    why_it_matters: str
    evidence_domain: str
    posture: str
    priority: int
    resolving_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "why_it_matters": self.why_it_matters,
            "evidence_domain": self.evidence_domain,
            "posture": self.posture,
            "priority": self.priority,
            "resolving_capabilities": list(self.resolving_capabilities),
        }


@dataclass
class EngineeringStrategy:
    influence_level: str
    influence_score: float
    engineering_phase: str
    policy_id: str
    task_scope: str
    lifecycle_stage: str
    lifecycle_band: str
    summary: str
    host_action: str
    what_matters_now: list[str]
    unresolved_decisions: list[dict[str, Any]]
    risks_if_proceeding: list[str]
    defer_until_later: list[str]
    effort_guidance: str
    stop_conditions: list[str]
    investment: dict[str, Any] | None = None
    recommended_evidence: dict[str, Any] | None = None
    playbook_id: str | None = None
    active_step_id: str | None = None
    engineering_spec: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "influence_level": self.influence_level,
            "influence_score": self.influence_score,
            "engineering_phase": self.engineering_phase,
            "policy_id": self.policy_id,
            "task_scope": self.task_scope,
            "lifecycle_stage": self.lifecycle_stage,
            "lifecycle_band": self.lifecycle_band,
            "summary": self.summary,
            "host_action": self.host_action,
            "what_matters_now": list(self.what_matters_now),
            "unresolved_decisions": list(self.unresolved_decisions),
            "risks_if_proceeding": list(self.risks_if_proceeding),
            "defer_until_later": list(self.defer_until_later),
            "effort_guidance": self.effort_guidance,
            "stop_conditions": list(self.stop_conditions),
            "investment": dict(self.investment) if self.investment else None,
            "recommended_evidence": (
                dict(self.recommended_evidence) if self.recommended_evidence else None
            ),
            "playbook_id": self.playbook_id,
            "active_step_id": self.active_step_id,
            "engineering_spec": dict(self.engineering_spec) if self.engineering_spec else None,
        }


def _intent_text(psm: ProjectSituationModel) -> str:
    return " ".join(f.intent for f in psm.episode.intent_stack).lower()


def _domain_posture(psm: ProjectSituationModel, domain: str) -> str:
    state = psm.evidence.domains.get(domain)
    return state.posture if state else "unknown"


def _applies_design_reference(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["task_scope"] not in ("design_driven", "redesign"):
        return False
    return disc["design_reference_posture"] in ("none", "agreed_no_refs")


def _applies_foundation(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["task_scope"] not in ("design_driven", "redesign", "system_setup", "feature_incremental"):
        return False
    if disc["task_scope"] == "feature_incremental" and disc["lifecycle_band"] != "early":
        return False
    return disc["foundation_posture"] == "unknown"


def _applies_design_system(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["system_posture"] != "no_ds":
        return False
    return disc["task_scope"] in ("design_driven", "redesign", "system_setup") or (
        disc["maturity_band"] == "greenfield" and disc["lifecycle_band"] == "early"
    )


def _applies_ui_baseline(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["task_scope"] in ("hotfix", "surgical", "debug"):
        return False
    ui = _domain_posture(psm, "ui_runtime")
    return not posture_meets_min(ui, "partial")


def _applies_codebase_context(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["task_scope"] in ("hotfix",):
        return False
    code = _domain_posture(psm, "codebase")
    if posture_meets_min(code, "partial"):
        return False
    return not getattr(psm.artifacts, "repo_root", None) and disc["task_scope"] != "surgical"


def _applies_seo(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    intent = _intent_text(psm)
    if not any(k in intent for k in ("seo", "lighthouse", "cwv", "meta tag", "search ranking")):
        return False
    return not posture_meets_min(_domain_posture(psm, "seo"), "partial")


def _applies_accessibility(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    intent = _intent_text(psm)
    if not any(k in intent for k in ("accessibility", "a11y", "wcag", "screen reader")):
        return False
    quality = _domain_posture(psm, "quality")
    return not posture_meets_min(quality, "partial")


def _applies_verification(disc: dict[str, str], psm: ProjectSituationModel) -> bool:
    if disc["task_scope"] in ("hotfix", "debug", "surgical"):
        return psm.episode.verification_status != "passed"
    return (
        psm.episode.verification_status != "passed"
        and disc["lifecycle_band"] in ("mid", "late", "production")
        and posture_meets_min(_domain_posture(psm, "ui_runtime"), "partial")
    )


_DECISION_RULES: list[dict[str, Any]] = [
    {
        "decision_id": "design_reference",
        "title": "Design reference and information hierarchy",
        "why_it_matters": (
            "Visual hierarchy, layout rhythm, and reference direction determine component "
            "structure, spacing tokens, and implementation order. Coding before this is "
            "settled creates expensive rework."
        ),
        "evidence_domain": "design_source",
        "posture_field": "design_reference_posture",
        "priority": 10,
        "structural": True,
        "applies": _applies_design_reference,
        "resolving_capabilities": ["inspiration_workflow", "figma_integration", "design_snapshot"],
        "defer_when_scope": ("hotfix", "surgical", "debug"),
    },
    {
        "decision_id": "component_foundation",
        "title": "Component foundation selection",
        "why_it_matters": (
            "The UI foundation (library, tokens, primitives) constrains every subsequent "
            "component decision. Changing foundation mid-build is high-cost."
        ),
        "evidence_domain": "design_system",
        "posture_field": "foundation_posture",
        "priority": 9,
        "structural": True,
        "applies": _applies_foundation,
        "resolving_capabilities": ["component_search_plan", "component_select", "design_graph_manage"],
        "defer_when_scope": ("hotfix", "surgical", "debug"),
    },
    {
        "decision_id": "design_system_posture",
        "title": "Design system posture",
        "why_it_matters": (
            "Whether to extend an existing system, introduce tokens, or stay ad-hoc affects "
            "consistency work and review scope for the whole surface."
        ),
        "evidence_domain": "design_system",
        "posture_field": "system_posture",
        "priority": 8,
        "structural": True,
        "applies": _applies_design_system,
        "resolving_capabilities": ["design_graph_manage", "design_consistency_assess"],
        "defer_when_scope": ("hotfix", "surgical", "debug"),
    },
    {
        "decision_id": "ui_baseline",
        "title": "Live UI baseline",
        "why_it_matters": (
            "Without a current UI snapshot, fixes and features risk targeting the wrong DOM "
            "state or missing regressions."
        ),
        "evidence_domain": "ui_runtime",
        "posture_field": "ui_runtime",
        "priority": 7,
        "structural": False,
        "applies": _applies_ui_baseline,
        "resolving_capabilities": ["browser_observe"],
        "defer_when_scope": (),
    },
    {
        "decision_id": "codebase_context",
        "title": "Codebase routing context",
        "why_it_matters": (
            "Route and component resolution reduces guesswork about where to edit and which "
            "patterns the repo already uses."
        ),
        "evidence_domain": "codebase",
        "posture_field": "codebase",
        "priority": 6,
        "structural": False,
        "applies": _applies_codebase_context,
        "resolving_capabilities": ["codebase_context"],
        "defer_when_scope": ("surgical",),
    },
    {
        "decision_id": "seo_baseline",
        "title": "SEO evidence baseline",
        "why_it_matters": (
            "Meta structure, crawlability, and CWV gaps should be measured before optimizing "
            "copy or layout for search."
        ),
        "evidence_domain": "seo",
        "posture_field": "seo",
        "priority": 7,
        "structural": False,
        "applies": _applies_seo,
        "resolving_capabilities": ["seo_readiness", "seo_evidence_collect"],
        "defer_when_scope": ("hotfix", "surgical"),
    },
    {
        "decision_id": "accessibility_baseline",
        "title": "Accessibility quality baseline",
        "why_it_matters": (
            "WCAG gaps and keyboard/screen-reader failures should be measured before "
            "declaring accessibility work complete."
        ),
        "evidence_domain": "quality",
        "posture_field": "quality",
        "priority": 7,
        "structural": False,
        "applies": _applies_accessibility,
        "resolving_capabilities": ["quality_audit"],
        "defer_when_scope": ("hotfix", "surgical"),
    },
    {
        "decision_id": "verification_outcome",
        "title": "Verification outcome",
        "why_it_matters": (
            "Implementation is not complete until deterministic verify passes against the "
            "intended criteria."
        ),
        "evidence_domain": "ui_runtime",
        "posture_field": "verification_status",
        "priority": 8,
        "structural": False,
        "applies": _applies_verification,
        "resolving_capabilities": ["browser_verify", "browser_observe"],
        "defer_when_scope": (),
    },
]


def _collect_unresolved(
    psm: ProjectSituationModel,
    disc: dict[str, str],
) -> list[UnresolvedDecision]:
    scope = disc["task_scope"]
    out: list[UnresolvedDecision] = []
    for rule in _DECISION_RULES:
        defer_scopes = rule.get("defer_when_scope") or ()
        if scope in defer_scopes:
            continue
        applies: AppliesFn = rule["applies"]
        if not applies(disc, psm):
            continue
        posture_field = rule.get("posture_field") or rule["evidence_domain"]
        if posture_field == "design_reference_posture":
            posture = disc.get("design_reference_posture", "none")
        elif posture_field == "foundation_posture":
            posture = disc.get("foundation_posture", "unknown")
        elif posture_field == "system_posture":
            posture = disc.get("system_posture", "no_ds")
        elif posture_field == "verification_status":
            posture = psm.episode.verification_status
        else:
            posture = _domain_posture(psm, posture_field)
        out.append(
            UnresolvedDecision(
                decision_id=str(rule["decision_id"]),
                title=str(rule["title"]),
                why_it_matters=str(rule["why_it_matters"]),
                evidence_domain=str(rule["evidence_domain"]),
                posture=posture,
                priority=int(rule["priority"]),
                resolving_capabilities=list(rule.get("resolving_capabilities") or []),
            )
        )
    out.sort(key=lambda d: d.priority, reverse=True)
    return out


def _derive_engineering_phase(disc: dict[str, str], psm: ProjectSituationModel) -> str:
    scope = disc["task_scope"]
    band = disc["lifecycle_band"]
    stage = psm.situation.lifecycle_stage

    if scope in ("hotfix",):
        return "hotfix_remediation"
    if scope in ("debug",):
        return "implementation"
    if scope == "surgical":
        return "implementation"

    if psm.episode.verification_status == "passed" and band in ("late", "production"):
        return "maintenance"

    if stage in ("S01_intent", "S02_discovery", "S03_design") or band == "early":
        if scope in ("design_driven", "redesign"):
            return "design_orientation"
        if scope == "system_setup":
            return "architecture"
        if scope in ("S03_design",):
            return "design_orientation"
        return "design_orientation" if band == "early" else "implementation"

    if stage in ("S04_architecture",) or scope == "system_setup":
        return "architecture"
    if stage in ("S07_verification",) or psm.episode.verification_status == "pending":
        if posture_meets_min(_domain_posture(psm, "ui_runtime"), "partial"):
            return "verification"
    if stage in ("S08_quality", "S09_consistency", "S10_release"):
        return "quality"
    if disc.get("polish_saturation") in ("soft", "hard"):
        return "polish"
    if band == "production":
        return "maintenance"
    return "implementation"


def _derive_influence_level(
    disc: dict[str, str],
    psm: ProjectSituationModel,
    unresolved: list[UnresolvedDecision],
) -> tuple[str, float]:
    scope = disc["task_scope"]
    band = disc["lifecycle_band"]
    structural = [d for d in unresolved if d.priority >= 8]

    if scope in ("hotfix", "surgical", "debug"):
        return "minimal", 0.15
    if band == "production":
        return "maintenance", 0.2
    if disc.get("polish_saturation") == "hard":
        return "minimal", 0.25
    if (
        psm.episode.verification_status == "passed"
        and not psm.evidence.blocking
        and scope in ("feature_incremental",)
    ):
        return "balanced", 0.45
    if psm.episode.verification_status == "passed" and not psm.evidence.blocking:
        return "maintenance", 0.3

    if len(structural) >= 2 and band == "early":
        return "structural", 0.9
    if scope in ("design_driven", "redesign", "system_setup") and band == "early":
        if structural:
            return "structural", 0.85
    if structural and band == "early":
        return "structural", 0.75

    if scope in ("design_driven", "redesign") and band in ("early", "mid"):
        return "balanced", 0.6
    return "balanced", 0.5


def _build_priorities(
    unresolved: list[UnresolvedDecision],
    disc: dict[str, str],
    phase: str,
) -> list[str]:
    priorities: list[str] = []
    for decision in unresolved[:3]:
        priorities.append(f"Resolve: {decision.title}")
    if not priorities:
        if phase == "verification":
            priorities.append("Confirm criteria and run verify before claiming done")
        elif phase == "hotfix_remediation":
            priorities.append("Minimize scope; observe, fix, verify, ship")
        elif disc["task_scope"] in ("surgical",):
            priorities.append("Single targeted change; verify immediately")
        else:
            priorities.append("Implement with verify loop; avoid speculative design spend")
    return priorities


def _build_risks(
    unresolved: list[UnresolvedDecision],
    influence_level: str,
    disc: dict[str, str],
) -> list[str]:
    if influence_level not in ("structural", "balanced"):
        return []
    risks: list[str] = []
    structural = [d for d in unresolved if d.priority >= 8]
    for decision in structural[:2]:
        risks.append(
            f"Proceeding without '{decision.title}' may force rework and inconsistent UI."
        )
    if disc["task_scope"] in ("design_driven", "redesign") and influence_level == "structural":
        risks.append(
            "Implementing layout/components before hierarchy is settled often wastes a full iteration."
        )
    return risks


def _build_deferrals(disc: dict[str, str], psm: ProjectSituationModel, phase: str) -> list[str]:
    defer: list[str] = []
    scope = disc["task_scope"]
    if scope in ("hotfix", "surgical", "debug"):
        defer.extend(
            [
                "Design inspiration and consistency audits",
                "SEO deep audits unless directly related to the fix",
            ]
        )
    if phase in ("design_orientation", "architecture"):
        defer.append("Production polish and micro-interactions until core structure is verified")
    if disc.get("polish_saturation") in ("soft", "hard"):
        defer.append("Further design review loops — diminishing returns reached")
    if psm.episode.verification_status != "passed" and scope not in ("hotfix",):
        defer.append("Declaring task complete before perception_verify passes")
    return defer


def _build_stop_conditions(
    psm: ProjectSituationModel,
    disc: dict[str, str],
    briefing_stop: str | None,
    investment: dict[str, Any] | None,
) -> list[str]:
    stops: list[str] = []
    if briefing_stop:
        stops.append(briefing_stop)
    if psm.episode.verification_status == "passed" and not psm.evidence.blocking:
        stops.append("verify_passed_sufficient — stop when criteria met")
    if investment:
        remaining = int(investment.get("budget_remaining") or 0)
        if remaining <= 2:
            stops.append("intelligence budget nearly exhausted — prefer host reasoning")
    if disc.get("polish_saturation") == "hard":
        stops.append("diminishing_returns_hard — suppress design loops")
    policy_stop = (psm.episode.retry_counters.get("situation_policy_id") or "")
    if "hotfix" in policy_stop or "surgical" in policy_stop:
        stops.append("scope-limited task — avoid expanding into design exploration")
    return list(dict.fromkeys(stops))


def _pick_recommended_evidence(
    psm: ProjectSituationModel,
    catalog: dict[str, Any],
    unresolved: list[UnresolvedDecision],
    *,
    fallback_capability: str | None,
) -> dict[str, Any] | None:
    candidates: list[tuple[float, str, UnresolvedDecision, Any]] = []
    for decision in unresolved[:4]:
        for cap_id in decision.resolving_capabilities:
            decision_eval = evaluate_allocation(psm, catalog, capability_id=cap_id)
            if decision_eval.recommend:
                score = decision_eval.roi * decision_eval.eqg
                candidates.append((score, cap_id, decision, decision_eval))

    if not candidates and fallback_capability:
        decision_eval = evaluate_allocation(psm, catalog, capability_id=fallback_capability)
        if decision_eval.recommend:
            return {
                "for_decision": None,
                "capability_id": fallback_capability,
                "rationale": decision_eval.benefit_claim,
                "routing_detail": decision_eval.routing_rationale,
            }
        return None

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, cap_id, decision, decision_eval = candidates[0]
    return {
        "for_decision": decision.decision_id,
        "for_decision_title": decision.title,
        "capability_id": cap_id,
        "rationale": (
            f"Resolves '{decision.title}': {decision_eval.benefit_claim}"
        ),
        "routing_detail": decision_eval.routing_rationale,
    }


def _effort_guidance(influence_level: str, disc: dict[str, str], investment: dict[str, Any] | None) -> str:
    ceiling = (investment or {}).get("visual_impact_ceiling", "V3")
    band = disc.get("lifecycle_band", "mid")
    if influence_level == "structural":
        return (
            f"Invest in structural decisions first (band={band}, ceiling={ceiling}). "
            "Evidence serves decisions — not the reverse."
        )
    if influence_level == "minimal":
        return "Keep MCP lightweight: observe, fix, verify. Skip design exploration."
    if influence_level == "maintenance":
        return "Production posture: verify correctness; defer net-new design investment."
    return f"Balanced influence (band={band}): gather missing evidence, then implement with verify."


def _build_summary(
    influence_level: str,
    phase: str,
    unresolved: list[UnresolvedDecision],
    disc: dict[str, str],
) -> str:
    if not unresolved:
        if phase == "hotfix_remediation":
            return "Hotfix mode: minimal frontend influence — observe, patch, verify."
        if phase == "maintenance" or influence_level == "maintenance":
            return "Maintenance mode: verify and ship; defer structural design work."
        return "Core decisions settled — proceed with implementation and verify loop."

    top = unresolved[0]
    return (
        f"{top.title} is unresolved ({influence_level} influence, {phase} phase). "
        f"Scope={disc.get('task_scope')} — address this before broad implementation."
    )


def _host_action(
    influence_level: str,
    unresolved: list[UnresolvedDecision],
    recommended: dict[str, Any] | None,
    stop_conditions: list[str],
) -> str:
    if stop_conditions and any("verify_passed" in s for s in stop_conditions):
        return "Verification satisfied — stop unless user requests more scope."
    if not unresolved:
        return "Read blocking issues, implement, and run perception_verify."
    top = unresolved[0]
    if influence_level == "structural":
        action = f"Decide {top.title} before writing substantial UI code."
    elif influence_level == "minimal":
        action = f"Keep scope tight; only resolve {top.title} if it blocks the fix."
    else:
        action = f"Resolve {top.title}, then implement."
    if recommended and recommended.get("capability_id"):
        action += (
            f" Optional evidence: {recommended['capability_id']} "
            f"({recommended.get('rationale', '')})."
        )
    return action


def compile_engineering_strategy(
    psm: ProjectSituationModel,
    catalog: dict[str, Any],
) -> EngineeringStrategy:
    """Compile decision-centric engineering strategy from live PSM + R12."""
    disc = derive_discriminators(psm)
    policy = match_policy(catalog, disc)
    policy_id = str(policy.get("policy_id") or "default.fallback")

    allocation = evaluate_allocation(psm, catalog, capability_id=None)
    if psm.briefing.investment:
        investment = dict(psm.briefing.investment)
    else:
        investment = {
            "policy_id": allocation.policy_id,
            "band": allocation.investment_band,
            "budget_total": allocation.budget_total,
            "budget_spent": allocation.budget_spent,
            "budget_remaining": allocation.budget_remaining,
            "visual_impact_ceiling": allocation.visual_impact_ceiling,
            "discriminators": allocation.discriminators,
        }

    unresolved = _collect_unresolved(psm, disc)
    influence_level, influence_score = _derive_influence_level(psm=psm, disc=disc, unresolved=unresolved)
    phase = _derive_engineering_phase(disc, psm)
    priorities = _build_priorities(unresolved, disc, phase)
    risks = _build_risks(unresolved, influence_level, disc)
    defer = _build_deferrals(disc, psm, phase)
    stops = _build_stop_conditions(
        psm,
        disc,
        psm.briefing.stop_reason,
        investment,
    )
    recommended = _pick_recommended_evidence(
        psm,
        catalog,
        unresolved,
        fallback_capability=psm.briefing.suggested_next_capability,
    )
    summary = _build_summary(influence_level, phase, unresolved, disc)
    host_action = _host_action(influence_level, unresolved, recommended, stops)

    # Coordinator reads Spec coverage/impact — does not compile measurement decisions.
    # V1: empty Spec until snapshot/inspiration feeds the Knowledge Compiler.
    from navigation.engineering_knowledge import EngineeringKnowledgeCompiler

    eng_spec = EngineeringKnowledgeCompiler().empty_spec(
        source_kind="strategy_bootstrap",
        provenance={"episode_id": psm.episode_id, "task_scope": disc.get("task_scope")},
    )
    # Prefer Spec impact ordering for what_matters when influence is structural/balanced
    spec_dict = eng_spec.to_dict()
    if influence_level in ("structural", "balanced") and spec_dict.get("unresolved_by_impact"):
        top = spec_dict["unresolved_by_impact"][:3]
        priorities = [
            f"Resolve: {d['decision_id']} (impact={d['impact_weight']})"
            for d in top
        ] + [p for p in priorities if not p.startswith("Resolve:")]

    return EngineeringStrategy(
        influence_level=influence_level,
        influence_score=influence_score,
        engineering_phase=phase,
        policy_id=policy_id,
        task_scope=disc.get("task_scope", "feature_incremental"),
        lifecycle_stage=psm.situation.lifecycle_stage,
        lifecycle_band=disc.get("lifecycle_band") or lifecycle_band(psm.situation.lifecycle_stage),
        summary=summary,
        host_action=host_action,
        what_matters_now=priorities,
        unresolved_decisions=[d.to_dict() for d in unresolved],
        risks_if_proceeding=risks,
        defer_until_later=defer,
        effort_guidance=_effort_guidance(influence_level, disc, investment),
        stop_conditions=stops,
        investment=investment,
        recommended_evidence=recommended,
        playbook_id=psm.episode.active_playbook_id,
        active_step_id=psm.episode.active_step_id,
        engineering_spec={
            "catalog_version": spec_dict.get("catalog_version"),
            "coverage": spec_dict.get("coverage"),
            "unresolved_by_impact": spec_dict.get("unresolved_by_impact"),
            "source_kind": spec_dict.get("source_kind"),
        },
    )


def compile_bootstrap_strategy(
    catalog: dict[str, Any],
    *,
    intent: str | None = None,
) -> dict[str, Any]:
    """Strategy stub for health / pre-session — full strategy needs session + intent."""
    if not intent:
        return {
            "influence_level": "unknown",
            "influence_score": 0.0,
            "engineering_phase": "unknown",
            "summary": (
                "Provide intent on perception_session_start for a full Engineering Strategy."
            ),
            "host_action": (
                "Call perception_session_start({ base_url, intent: '<task description>' }). "
                "Read agent_summary.engineering_strategy before planning."
            ),
            "what_matters_now": [
                "Bootstrap session with intent describing the engineering task",
            ],
            "unresolved_decisions": [],
            "risks_if_proceeding": [],
            "defer_until_later": [],
            "effort_guidance": "Intent unlocks R12 policy matching and influence level.",
            "stop_conditions": [],
            "investment": None,
            "recommended_evidence": None,
        }

    from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
    from navigation.coordination_intelligence.planning.situation_policy import intent_suggests_stage

    psm = ProjectSituationModel()
    psm.episode.intent_stack.append(IntentFrame(intent=intent, pushed_at=_utc_now()))
    hinted = intent_suggests_stage(intent)
    if hinted:
        psm.situation.lifecycle_stage = hinted
    if any(k in intent.lower() for k in ("hotfix", "production incident")):
        psm.situation.situation_class = "hotfix"
    elif any(k in intent.lower() for k in ("bug", "fix responsive", "debug")):
        psm.situation.situation_class = "functional_bug"
    elif any(k in intent.lower() for k in ("landing", "dashboard", "redesign", "marketing")):
        psm.situation.situation_class = "inspiration_needed"

    strategy = compile_engineering_strategy(psm, catalog)
    out = strategy.to_dict()
    out["bootstrap"] = True
    out["host_action"] = (
        f"{out['host_action']} Start session to refresh strategy as evidence accumulates."
    )
    return out


def surface_engineering_strategy(envelope: dict[str, Any], strategy: dict[str, Any]) -> dict[str, Any]:
    """Promote engineering strategy to top-level data and agent_summary."""
    data = envelope.setdefault("data", {})
    data["engineering_strategy"] = strategy
    agent_summary = envelope.setdefault("agent_summary", {})
    agent_summary["engineering_strategy"] = strategy
    headline = strategy.get("summary")
    if headline:
        agent_summary["coordinator_headline"] = headline
    return envelope
