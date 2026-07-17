"""Focused methodology resources for progressive MCP discovery."""
from __future__ import annotations


def _guide(title: str, use_when: str, decisions: str, evidence: str, boundary: str, done: str) -> str:
    return f"""# {title}

## Use when
{use_when}

## Decisions to resolve
{decisions}

## Minimum evidence
{evidence}

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
{boundary}

## Done condition
{done}
"""


METHODOLOGY_RESOURCES: dict[str, tuple[str, str]] = {
    "perception://getting-started": (
        "Getting Started",
        _guide(
            "Getting Started",
            "At the beginning of a frontend task.",
            "Task scope, influence level, and the first unresolved engineering decision.",
            "Call health with the real intent, then session_start when the runtime is available. Read the returned recommended resource and implementation gate.",
            "When blocked, only inspect, gather evidence, or scaffold/start the runtime. Claim-done follows the Done ladder in perception://verification-guide.",
            "The coordinator identifies the correct workflow resource and required capability.",
        ),
    ),
    "perception://frontend-methodology": (
        "Frontend Methodology",
        _guide(
            "Frontend Methodology",
            "For any frontend change when no more specific workflow is recommended.",
            "What evidence materially changes the next implementation decision.",
            "Engineering Strategy first; targeted intelligence second; browser verification after action.",
            "Do not maximize calls. Do not lock structural decisions from degraded evidence.",
            "Required decisions are resolved; data.verified=true; section checklist complete when required; Ship Council clear when required.",
        ),
    ),
    "perception://design-workflow": (
        "Greenfield Design Workflow",
        _guide(
            "Greenfield Design Workflow",
            "Building a new product, page, dashboard, landing page, or visual foundation.",
            "Design direction, information hierarchy, component foundation, tokens, and responsive composition.",
            "Usable reference evidence plus Component Intelligence selection. A measured Engineering Spec must harden soft inspiration priors.",
            "Broad visual implementation is prohibited while the structural gate is blocked. Runtime scaffolding is allowed.",
            "Reference and foundation decisions are usable, the draft is remeasured, SpecDiff is honored, "
            "each section_checklist block is observed+verified, Ship Council is clear, and data.verified=true.",
        ),
    ),
    "perception://redesign-workflow": (
        "Redesign Workflow",
        _guide(
            "Redesign Workflow",
            "Changing the visual system or full-page composition of an existing interface.",
            "Current baseline, target reference, intentional changes, and preserved behavior.",
            "Observe and build a Design Snapshot; bind/measure the target; use SpecDiff and Design Review.",
            "Do not rewrite the full UI before the current and target evidence are measurable.",
            "Required revisions are applied, remeasured, section checklist complete, Ship Council clear, and verified.",
        ),
    ),
    "perception://bugfix-workflow": (
        "Bugfix Workflow",
        _guide(
            "Bugfix Workflow",
            "A surgical UI bug, responsive defect, broken flow, or production hotfix.",
            "Reproduction, owning component, smallest safe correction, and regression criteria.",
            "Observe blocking evidence, resolve route/component ownership when unclear, then verify the exact symptom.",
            "Avoid inspiration, redesign, and broad structural changes unless the bug proves they are necessary.",
            "The original symptom is covered by a passing verification with no new blocking issue.",
        ),
    ),
    "perception://engineering-strategy": (
        "Engineering Strategy",
        _guide(
            "Engineering Strategy",
            "When reading coordinator strategy or deciding whether evidence is worth collecting.",
            "Influence level, unresolved decisions, ROI, allowed actions, and stop conditions.",
            "Use strategy fields as a decision contract, especially implementation_gate and evidence_plan.",
            "Recommended evidence is required when the gate says blocked; it is optional only when the gate permits implementation.",
            "The next action matches the gate and the highest-impact unresolved decision.",
        ),
    ),
    "perception://decision-ledger": (
        "Decision and Evidence Ledger",
        _guide(
            "Decision and Evidence Ledger",
            "When tracking evidence outcomes or Ship Council challenge dispositions.",
            "Whether evidence succeeded, provisional, failed, or noop; ship lifecycle phases.",
            "Inspect coordination_evidence and decision_ledger entries on the PSM.",
            "Lifecycle: Decision → Evidence → Challenge → Disposition → Verification → Closed.",
            "Every structural decision and ship challenge resolves to a closed ledger entry or open challenge.",
        ),
    ),
    "perception://ship-council": (
        "Ship Council",
        _guide(
            "Ship Council",
            "After section checklist is complete on structural/balanced UI — before claiming done.",
            "Top 3–5 ROI-ranked ship decisions to challenge; dispositions revised, accepted, or ask_user.",
            "perception_design_review(mode=\"ship\") with snapshot; optional dispositions array.",
            "Agent revises convention gaps; accept requires concrete engineering rationale; ask_user only for brand/subjective conflicts.",
            "Section checklist complete, ship_gate.council_clear is true, and ship_summary reflects dispositions.",
        ),
    ),
    "perception://verification-guide": (
        "Verification Guide",
        _guide(
            "Verification Guide",
            "After an implementation action or when the strategy enters verification.",
            "User-visible success criteria, each layout section, responsive behavior, blocking runtime issues, and Spec drift.",
            "Require data.verified=true (transport ok is not a pass). When section_checklist_required: observe→look→perception_verify(section_id) for each block. Then remeasure Spec and honor spec_revision_gate.",
            "Page verify alone is not claim-done for design_driven/redesign/structural drafts. Complete section checklist, then perception_design_review(mode=\"ship\") when ship_council_required.",
            "data.verified=true, blocking empty, section_checklist complete when required, ship_gate.council_clear when required, Spec revisions cleared.",
        ),
    ),
    "perception://browser-lifecycle": (
        "Browser Lifecycle",
        _guide(
            "Browser Lifecycle",
            "When using browser, inspiration fallback, navigation, or recovering a manually closed browser.",
            "Single owner, live URL truth, app origin, session reuse, and restoration correctness.",
            "One Browser Session Manager owns Chromium; verify the live URL after restore.",
            "Guest tools must park and restore the app URL and never report restored from metadata alone.",
            "Session metadata matches the live browser and external pages are not left active.",
        ),
    ),
}
