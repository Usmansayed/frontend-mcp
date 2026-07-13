"""Sandbox playbook / capability candidate planner — not production playbooks.

Produces ordered candidate capabilities + semantic actions for simulation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateStep:
    capability_id: str
    semantic_action: str
    rationale: str


@dataclass(frozen=True)
class PlaybookPlan:
    playbook_id: str
    reason: str
    steps: tuple[CandidateStep, ...]


def plan_for_scope(task_scope: str, intent: str) -> PlaybookPlan:
    """Map task scope → advisory candidate sequence (host-oriented simulation)."""
    t = intent.lower()

    if task_scope == "surgical":
        return PlaybookPlan(
            playbook_id="observe_reason_act_verify.loop",
            reason="Tiny visual/copy tweak — observe, host implements, verify",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "Ground UI state before edit"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: should be skipped"),
                CandidateStep("design_review", "run_design_review", "Probe: should be skipped"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm surgical fix"),
            ),
        )

    if task_scope == "hotfix":
        return PlaybookPlan(
            playbook_id="observe_reason_act_verify.loop",
            reason="Production hotfix — correctness only, suppress design workflows",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "Capture failing UI"),
                CandidateStep("browser_diff", "diff_against_baseline", "Isolate regression"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: should be skipped"),
                CandidateStep("design_review", "run_design_review", "Probe: should be skipped"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm hotfix"),
            ),
        )

    if task_scope == "debug":
        return PlaybookPlan(
            playbook_id="observe_reason_act_verify.loop",
            reason="Bugfix — observe + diagnose, not redesign",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "Reproduce visually"),
                CandidateStep("runtime_diagnosis", "diagnose_runtime", "Trace console/network if needed"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: should be skipped"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm fix"),
            ),
        )

    if task_scope == "system_setup":
        return PlaybookPlan(
            playbook_id="component_foundation.select",
            reason="Foundation / library work — invest in selection + graph",
            steps=(
                CandidateStep("component_search_plan", "plan_component_search", "Plan foundation search"),
                CandidateStep("component_search", "search_components", "Search candidates"),
                CandidateStep("component_select", "select_component_foundation", "Choose foundation"),
                CandidateStep("design_graph_manage", "refresh_design_graph", "Update system graph"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Optional; ROI-gated"),
                CandidateStep("browser_verify", "verify_integration", "Smoke-check foundation"),
            ),
        )

    if task_scope in ("design_driven", "redesign"):
        playbook = (
            "inspiration.collect"
            if "landing" in t or "marketing" in t or "redesign" in t
            else "design_quality.review"
        )
        return PlaybookPlan(
            playbook_id=playbook,
            reason="High visual impact — allow heavy design investment early",
            steps=(
                CandidateStep("inspiration_workflow", "discover_or_search_assets", "Orient design language"),
                CandidateStep("component_select", "select_component_foundation", "Lock foundations"),
                CandidateStep("resource_workflow", "collect_selected_assets", "Assets after orientation"),
                CandidateStep("browser_observe", "observe_target_page", "See painted UI"),
                CandidateStep("design_snapshot", "build_design_snapshot", "Structure for critique"),
                CandidateStep("design_review", "run_design_review", "Critique after paint"),
                CandidateStep("design_review", "run_design_review_pass_2", "Probe diminishing returns"),
                CandidateStep("seo_evidence_collect", "collect_seo_evidence", "Probe: often deferred early"),
                CandidateStep("browser_verify", "verify_success_criteria", "Close the loop"),
            ),
        )

    if "accessib" in t:
        return PlaybookPlan(
            playbook_id="quality.audit",
            reason="Accessibility / quality pass — late-band ROI tools",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "Baseline UI"),
                CandidateStep("quality_audit", "run_quality_audit", "a11y/audit evidence"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: usually skip"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm a11y fixes"),
            ),
        )

    if "auth" in t or "login" in t:
        return PlaybookPlan(
            playbook_id="observe_reason_act_verify.loop",
            reason="Auth / gates — probe flows, minimal design",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "See auth surfaces"),
                CandidateStep("route_guards_probe", "probe_route_guards", "Understand guards"),
                CandidateStep("auth_gate", "detect_auth_gate", "Detect human gate"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: skip unless redesign"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm auth path"),
            ),
        )

    if "dark mode" in t or "theme" in t:
        return PlaybookPlan(
            playbook_id="design_quality.review",
            reason="Theme work — system + verify, limited inspiration",
            steps=(
                CandidateStep("browser_observe", "observe_current_page", "Current theme state"),
                CandidateStep("design_graph_manage", "refresh_design_graph", "Token/theme graph"),
                CandidateStep("design_review", "run_design_review", "Check contrast/hierarchy"),
                CandidateStep("inspiration_workflow", "discover_inspiration", "ROI-gated"),
                CandidateStep("browser_verify", "verify_success_criteria", "Confirm dark mode"),
            ),
        )

    # feature_incremental default
    return PlaybookPlan(
        playbook_id="observe_reason_act_verify.loop",
        reason="Incremental feature — balanced mid investment",
        steps=(
            CandidateStep("browser_observe", "observe_current_page", "Ground current UI"),
            CandidateStep("codebase_context", "gather_code_context", "Locate owners (host)"),
            CandidateStep("inspiration_workflow", "discover_inspiration", "Probe: usually deferred"),
            CandidateStep("design_review", "run_design_review", "ROI-gated polish"),
            CandidateStep("browser_verify", "verify_success_criteria", "Confirm change"),
        ),
    )
