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
        """# Getting Started

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
   (`intent` is required for useful greenfield vs hotfix routing)
4. Read **`agent_summary.coordinator`** and **`recommended_next`** first (slim briefing);
   then `engineering_strategy` / `episode_card` for gate, unpaid, influence, resources
5. `resources/read` the `recommended_resource`
6. Gather only evidence that changes an unresolved decision; then implement
7. After ACT: Done ladder in `perception://verification-guide`
   (`data.verified=true` → section checklist if required → Ship Council if required)

Situation cards (short): `perception://guide/scoreboard`, `greenfield`, `redesign`,
`feature`, `hotfix`, `forms`, `hard-fails` — also see always-on agent rule.

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
""",
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
            "Observe and build a Design Snapshot; bind/measure the target; use SpecDiff and Design Review. "
            "build_design_snapshot / design_review / consistency tools now inline rendered screenshots "
            "(viewport + full page + section crops) — after every UI change, re-run the tool and LOOK at the images.",
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
            "Influence level, surface_type, episode_backlog, episode_portfolio, episode_confidence, unresolved decisions, ROI, allowed actions, and stop conditions. "
            "`data.coordinator` is slim `coordinator_card.v1` (host_action, gate, portfolio ids, confidence, evidence_quality_alerts); full strategy lives under `agent_summary.engineering_strategy`.",
            "Use strategy as a decision contract — implementation_gate ladder (sections → residue → ship → evidence terminals), backlog.top for ROI next, portfolio for unpaid families. Initiative is advisory only. "
            "Prefer `agent_summary.episode_card` (`episode_card.v1`) as the single readout: gate, portfolio, confidence, alerts, what_matters. "
            "You (the agent) coordinate: build a ≤3 unpaid owed plan from portfolio — do not tunnel on gate.next alone. "
            "See `perception://agent-coordination` and `perception://guide/*` situation cards.",
            "Recommended evidence is required when the gate says blocked; residue is one remasure pass only. Skip evidence with a valid reason rather than ritual tool calls.",
            "Next action matches gate.next as the immediate pitch, but unpaid structural families still bind the brain; confidence is a readout, not a gate.",
        ),
    ),
    "perception://agent-coordination": (
        "Agent-Brain Coordination",
        """# Agent-Brain Coordination

## Use when
Every structural / balanced / redesign UI episode — after reading `episode_card` or engineering strategy.
MCP stays a **facts scoreboard**. You decide which families to pay.

## Decisions to resolve
Which unpaid families are owed for *this* task class (≤3), which single tool to call next,
and when evidence is enough to lock UI direction (or skip with a valid reason).

## Minimum evidence
1. Read `episode_card`: unpaid + gate + backlog.top (+ confidence).
2. Classify: greenfield | redesign | mockup | feature | hotfix | polish | forms.
3. Read the matching `perception://guide/*` card; build owed ≤3 from unpaid ∩ class.
4. One tool from owed (`gate.next` / `backlog.top` only if inside owed); re-read unpaid before locking UI.
5. If unpaid is empty (outside design initiative), still run the class minimum path.

## Implementation boundary
Do not invent new MCP gates. Do not call every family. Do not obey only `gate.next`
while other structural unpaid remain. Soft text verify is not redesign-done.
Primary short contract: always-on agent rule. Situation cards: `perception://guide/*`.

## Done condition
Gate allows claim; structural unpaid cleared (paid / skip / supersede); Done ladder if required.
""",
    ),
    "perception://guide/scoreboard": (
        "Guide: Scoreboard",
        _guide(
            "Guide: Scoreboard",
            "Every structural/balanced turn — before locking UI direction.",
            "Which unpaid families bind, whether gate blocks claim, and which single tool is next inside the owed plan.",
            "Read episode_card unpaid + gate + backlog.top. Build owed ≤3 from unpaid ∩ task class. "
            "Prefer backlog.top only if it is already in owed. Re-read unpaid after each evidence call. "
            "If unpaid empty, still run class min path (feature/hotfix often have empty portfolio).",
            "Do not treat gate.next or recommended_evidence as the whole plan. Confidence is a readout, not a gate.",
            "Owed plan clear; next call is from owed; structural locks only after advancement_eligible evidence.",
        ),
    ),
    "perception://guide/greenfield": (
        "Guide: Greenfield",
        _guide(
            "Guide: Greenfield",
            "New product UI / landing / no mockup yet (maps to design_driven).",
            "Design reference (inspiration or snapshot), component foundation, live baseline, then verify.",
            "Pay inspiration **or** snapshot while design_reference unpaid (one progressive collect 3–5 refs — stop when usable). "
            "Pay component if foundation unpaid. Observe, then implement, then data.verified=true; sections/ship if gated.",
            "Skip SEO, ritual 2–3 inspiration loops, and ship before reference+foundation are paid/skipped.",
            "Reference + foundation settled (or valid skip); draft remeasured if Spec bound; Done ladder clear.",
        ),
    ),
    "perception://guide/redesign": (
        "Guide: Redesign / Mockup",
        _guide(
            "Guide: Redesign / Mockup",
            "Visual overhaul, rebrand, or user-uploaded mockup/reference image.",
            "Measured baseline/target (snapshot), intentional changes, verify, ship when gated.",
            "Mockup or redesign with snapshot unpaid → perception_build_design_snapshot (bind) first — not gallery inspiration. "
            "Inspiration only if direction still open and snapshot not the path. Observe correct port/app. "
            "After draft: SpecDiff / remeasure; hard verify; sections then ship if required. "
            "Dashboard ship may challenge equal-weight KPIs; settings/auth use form/footer signals — do not force KPI fixes on settings.",
            "Do not match a mockup with soft text verify alone. Do not re-run inspiration after Spec/mockup bound.",
            "Snapshot/Spec path honored; data.verified=true; checklist/ship clear when required.",
        ),
    ),
    "perception://guide/feature": (
        "Guide: Feature",
        _guide(
            "Guide: Feature",
            "Add or change a feature on an existing surface (not full redesign).",
            "Affected routes, owners if unclear, and verification of the change.",
            "Observe affected routes. If owners unclear → perception_resolve_route / perception_resolve_component "
            "(even when resolve is not listed in unpaid). Implement. Verify with data.verified=true. "
            "Ladder only if gate flags sections/ship.",
            "Skip greenfield inspiration and new foundation selection unless unpaid and truly required.",
            "Change verified; no open claim prohibition.",
        ),
    ),
    "perception://guide/hotfix": (
        "Guide: Hotfix / Polish",
        _guide(
            "Guide: Hotfix / Polish",
            "Bug, surgical CSS, blur/opacity nudge, or micro polish (maps to hotfix/surgical/debug).",
            "Symptom reproduction, smallest fix, hard verification.",
            "Observe live page on the correct port (blocking first). Smallest fix. "
            "Verify with hard criteria (computed style / JS). For opacity/blur “looks the same,” measure competing overlays/washes.",
            "Skip inspiration, foundation, and ship — **unless** this episode already drafted design_driven/redesign UI (sticky design): then finish section checklist + Ship Council. "
            "If unpaid includes sections or residue, pay those ladder families before claim (sections/residue outrank class tables).",
            "data.verified=true for the symptom; ladder complete only when sticky design / gate requires it.",
        ),
    ),
    "perception://guide/forms": (
        "Guide: Forms / Guards / Flows",
        _guide(
            "Guide: Forms / Guards / Flows",
            "Form validation, auth gates, multi-step flows — not a full marketing landing.",
            "Playbook criteria, invalid then valid paths, guard boundaries.",
            "Read strategy. Use perception_probe_form / perception_probe_guards / flow checkpoints as appropriate. "
            "Still verify with data.verified=true. Do not treat a new product landing as “just a form.”",
            "Avoid greenfield inspiration tours unless the surface is actually new marketing UI.",
            "Probe criteria covered; verify passed; auth requires_human stops for the user.",
        ),
    ),
    "perception://guide/hard-fails": (
        "Guide: Hard Fails",
        _guide(
            "Guide: Hard Fails",
            "Any UI episode — memorize these process fails.",
            "Whether the agent is about to tunnel, skip reference, false-green, or claim early.",
            "Stop if: (1) only gate.next while other structural unpaid remain; "
            "(2) large UI with inspiration and snapshot both unpaid; "
            "(3) mockup without snapshot; (4) soft text verify for visual claims; "
            "(5) claim while claim_complete prohibited or sections/ship unpaid; "
            "(6) SEO/thoroughness spam; (7) wrong port/product; "
            "(8) foundation reopen on 2-line polish; (9) parallel browser tools on one session_id; "
            "(10) end-of-task MCP only after coding the full UI.",
            "These are host process fails — MCP may still return ok. Do not rationalize past them.",
            "No hard-fail pattern present before claim-done.",
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
            "Top 3–5 ROI-ranked ship decisions gated by surface_type (dashboard vs settings_form vs auth vs marketing). Settings prefer form measure / footer rhythm; skip equal-weight KPI on settings. Not sticky/overflow conventions (those fail in verify).",
            "perception_design_review(mode=\"ship\") with snapshot; optional dispositions array. "
            "Obey revise_guidance / anti_patterns on each challenge — e.g. equal_weight_kpi_cluster must NOT be fixed with col-span that breaks equal columns. Thin or empty-dense clears may require one residue remasure.",
            "Agent revises high-ROI design challenges; accept requires concrete engineering rationale; ask_user only for brand/subjective conflicts.",
            "Section checklist complete, residue closed when required, ship_gate.council_clear is true, and ship_summary reflects dispositions.",
        ),
    ),
    "perception://verification-guide": (
        "Verification Guide",
        _guide(
            "Verification Guide",
            "After an implementation action or when the strategy enters verification.",
            "User-visible success criteria, each layout section, responsive behavior, blocking runtime issues, and Spec drift.",
            "Require data.verified=true (transport ok is not a pass). When section_checklist_required: observe→look→perception_verify(section_id) for each block. Then remeasure Spec and honor spec_revision_gate.",
            "On design_driven/redesign with a snapshot, verify also enforces objective chrome conventions (sticky/fixed primary nav/sidebar, no horizontal overflow). Page verify alone is not claim-done — complete section checklist, then perception_design_review(mode=\"ship\") when ship_council_required.",
            "data.verified=true (including chrome conventions), blocking empty, section_checklist complete when required, ship_gate.council_clear when required, Spec revisions cleared.",
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
