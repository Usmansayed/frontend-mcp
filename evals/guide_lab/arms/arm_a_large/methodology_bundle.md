# Getting Started

URI: perception://getting-started

# Getting Started

## Production rule
If this is a UI / frontend / visual / redesign / polish / form / dashboard / landing /
layout / CSS task and you have not called `perception_health` (and
`perception_session_start` when reachable) with the **real user intent**, stop coding
and bootstrap now. End-of-task MCP is how false-green UIs ship.

## Use when
At the beginning of every applicable frontend task — before planning large UI code.

## Decisions to resolve
Task scope, influence level, implementation_gate, and the first unresolved
engineering decision.

## Minimum evidence (mandatory order)
1. `resources/read` → `perception://getting-started` (this page)
2. `perception_health({ url, intent })` with the real task wording
3. If reachable: `perception_session_start({ base_url, intent })` → save `session_id`
4. Read `agent_summary.engineering_strategy` (influence, unresolved_decisions,
   recommended_resource, recommended_evidence, implementation_gate)
5. `resources/read` the `recommended_resource`
6. Gather only evidence that changes an unresolved decision; then implement
7. After ACT: Done ladder in `perception://verification-guide`
   (`data.verified=true` → section checklist if required → Ship Council if required)

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.
Transport `ok=true` with `data.verified=false` is a verify **fail**.

## Implementation boundary
When blocked, only inspect, gather evidence, or scaffold/start the runtime.
Do not draft a full viewport while the structural gate is blocked.
Claim-done follows the Done ladder — never from a single soft page verify.

## Done condition
The coordinator identifies the correct workflow resource and required capability;
you have obeyed the gate; claim-done only after the Done ladder clears.


---

# Frontend Methodology

URI: perception://frontend-methodology

# Frontend Methodology

## Use when
For any frontend change when no more specific workflow is recommended.

## Decisions to resolve
What evidence materially changes the next implementation decision.

## Minimum evidence
Engineering Strategy first; targeted intelligence second; browser verification after action.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Do not maximize calls. Do not lock structural decisions from degraded evidence.

## Done condition
Required decisions are resolved; data.verified=true; section checklist complete when required; Ship Council clear when required.


---

# Greenfield Design Workflow

URI: perception://design-workflow

# Greenfield Design Workflow

## Use when
Building a new product, page, dashboard, landing page, or visual foundation.

## Decisions to resolve
Design direction, information hierarchy, component foundation, tokens, and responsive composition.

## Minimum evidence
Usable reference evidence plus Component Intelligence selection. A measured Engineering Spec must harden soft inspiration priors.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Broad visual implementation is prohibited while the structural gate is blocked. Runtime scaffolding is allowed.

## Done condition
Reference and foundation decisions are usable, the draft is remeasured, SpecDiff is honored, each section_checklist block is observed+verified, Ship Council is clear, and data.verified=true.


---

# Redesign Workflow

URI: perception://redesign-workflow

# Redesign Workflow

## Use when
Changing the visual system or full-page composition of an existing interface.

## Decisions to resolve
Current baseline, target reference, intentional changes, and preserved behavior.

## Minimum evidence
Observe and build a Design Snapshot; bind/measure the target; use SpecDiff and Design Review.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Do not rewrite the full UI before the current and target evidence are measurable.

## Done condition
Required revisions are applied, remeasured, section checklist complete, Ship Council clear, and verified.


---

# Bugfix Workflow

URI: perception://bugfix-workflow

# Bugfix Workflow

## Use when
A surgical UI bug, responsive defect, broken flow, or production hotfix.

## Decisions to resolve
Reproduction, owning component, smallest safe correction, and regression criteria.

## Minimum evidence
Observe blocking evidence, resolve route/component ownership when unclear, then verify the exact symptom.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Avoid inspiration, redesign, and broad structural changes unless the bug proves they are necessary.

## Done condition
The original symptom is covered by a passing verification with no new blocking issue.


---

# Engineering Strategy

URI: perception://engineering-strategy

# Engineering Strategy

## Use when
When reading coordinator strategy or deciding whether evidence is worth collecting.

## Decisions to resolve
Influence level, surface_type, episode_backlog, episode_portfolio, episode_confidence, unresolved decisions, ROI, allowed actions, and stop conditions. `data.coordinator` is slim `coordinator_card.v1` (host_action, gate, portfolio ids, confidence, evidence_quality_alerts); full strategy lives under `agent_summary.engineering_strategy`.

## Minimum evidence
Use strategy as a decision contract — implementation_gate ladder (sections → residue → ship → evidence terminals), backlog.top for ROI next, portfolio for unpaid families. Initiative is advisory only. Prefer `agent_summary.episode_card` (`episode_card.v1`) as the single readout: gate, portfolio, confidence, alerts, what_matters. You (the agent) coordinate: build a ≤3 unpaid owed plan from portfolio — do not tunnel on gate.next alone. See `perception://agent-coordination`.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Recommended evidence is required when the gate says blocked; residue is one remasure pass only. Skip evidence with a valid reason rather than ritual tool calls.

## Done condition
Next action matches gate.next as the immediate pitch, but unpaid structural families still bind the brain; confidence is a readout, not a gate.


---

# Agent-Brain Coordination

URI: perception://agent-coordination

# Agent-Brain Coordination

## Use when
Every structural / balanced / redesign UI episode — after reading `episode_card` or engineering strategy.
MCP stays a **facts scoreboard**. You decide which families to pay.

## Decisions to resolve
Which unpaid families are owed for *this* task class (≤3), which single tool to call next,
and when evidence is enough to lock UI direction (or skip with a valid reason).

## Minimum evidence
1. Read `episode_card`: unpaid + gate + backlog.top (+ confidence).
2. Classify: greenfield | redesign/mockup | feature | hotfix | polish.
3. Owed plan from unpaid ∩ class (inspiration **or** snapshot; component if foundation unpaid; observe; verify / ship when gated).
4. One tool call from the plan; re-read unpaid before locking hierarchy/foundation.
5. Inspiration when owed: one progressive collect → 3–5 image refs; stop when usable.

## Implementation boundary
Do not invent new MCP gates. Do not call every family. Do not obey only `gate.next`
while other structural unpaid remain. Soft text verify is not redesign-done.

## Done condition
Gate allows claim; structural unpaid cleared (paid / skip / supersede); Done ladder if required.


---

# Decision and Evidence Ledger

URI: perception://decision-ledger

# Decision and Evidence Ledger

## Use when
When tracking evidence outcomes or Ship Council challenge dispositions.

## Decisions to resolve
Whether evidence succeeded, provisional, failed, or noop; ship lifecycle phases.

## Minimum evidence
Inspect coordination_evidence and decision_ledger entries on the PSM.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Lifecycle: Decision → Evidence → Challenge → Disposition → Verification → Closed.

## Done condition
Every structural decision and ship challenge resolves to a closed ledger entry or open challenge.


---

# Ship Council

URI: perception://ship-council

# Ship Council

## Use when
After section checklist is complete on structural/balanced UI — before claiming done.

## Decisions to resolve
Top 3–5 ROI-ranked ship decisions gated by surface_type (dashboard vs settings_form vs auth vs marketing). Settings prefer form measure / footer rhythm; skip equal-weight KPI on settings. Not sticky/overflow conventions (those fail in verify).

## Minimum evidence
perception_design_review(mode="ship") with snapshot; optional dispositions array. Obey revise_guidance / anti_patterns on each challenge — e.g. equal_weight_kpi_cluster must NOT be fixed with col-span that breaks equal columns. Thin or empty-dense clears may require one residue remasure.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Agent revises high-ROI design challenges; accept requires concrete engineering rationale; ask_user only for brand/subjective conflicts.

## Done condition
Section checklist complete, residue closed when required, ship_gate.council_clear is true, and ship_summary reflects dispositions.


---

# Verification Guide

URI: perception://verification-guide

# Verification Guide

## Use when
After an implementation action or when the strategy enters verification.

## Decisions to resolve
User-visible success criteria, each layout section, responsive behavior, blocking runtime issues, and Spec drift.

## Minimum evidence
Require data.verified=true (transport ok is not a pass). When section_checklist_required: observe→look→perception_verify(section_id) for each block. Then remeasure Spec and honor spec_revision_gate.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
On design_driven/redesign with a snapshot, verify also enforces objective chrome conventions (sticky/fixed primary nav/sidebar, no horizontal overflow). Page verify alone is not claim-done — complete section checklist, then perception_design_review(mode="ship") when ship_council_required.

## Done condition
data.verified=true (including chrome conventions), blocking empty, section_checklist complete when required, ship_gate.council_clear when required, Spec revisions cleared.


---

# Browser Lifecycle

URI: perception://browser-lifecycle

# Browser Lifecycle

## Use when
When using browser, inspiration fallback, navigation, or recovering a manually closed browser.

## Decisions to resolve
Single owner, live URL truth, app origin, session reuse, and restoration correctness.

## Minimum evidence
One Browser Session Manager owns Chromium; verify the live URL after restore.

## Failure and fallback
A completed tool call is not automatically usable evidence. Read `coordination_evidence`
and `implementation_gate`; if evidence is failed or provisional, follow the returned
`next_required_capability` instead of inventing the unresolved decision.

## Implementation boundary
Guest tools must park and restore the app URL and never report restored from metadata alone.

## Done condition
Session metadata matches the live browser and external pages are not left active.


---
