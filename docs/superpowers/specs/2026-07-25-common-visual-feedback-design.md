# Common Visual Feedback Tool — Design

Date: 2026-07-25
Status: approved (chat), implementing

## Problem

Visual feedback (LOOK at rendered pixels → agent judgment → next steps) was bolted onto
four design/consistency tools only. Component, inspiration, hotfix, and forms work also
need a look before structural edits, and each intelligence duplicating `visual_feedback`
args + a private policy does not scale.

## Decision

One common MCP tool, **`perception_visual_feedback`**, built on existing perception
runtime (no new capture stack, no vision LLM inside the MCP). The LLM is the brain: the
tool captures the right pixels, attaches the right guide pointer, hands the agent a
purpose-shaped JSON schema to fill, and — when the agent returns judgment — emits
advisory `next_actions`. Deterministic hints only; the agent decides.

## Contract

Inputs (core): `session_id` (required for live capture), `purpose`
(`design | consistency | component | inspiration | hotfix | forms | general`),
`screenshot_pack` (`auto` default → resolved from purpose), `focus_sections`,
`screenshot_selector`, `max_sections`, `scan_id` (reuse stored screenshot when live
capture is unavailable), and optional `visual_feedback` judgment JSON
(`judgment: ok|needs_work|unclear`, `notes`, `focus_sections`, `focus_selector`,
`issues[]` + purpose extras).

Outputs: inline screenshots (same MCP image attachment path as observe),
`data.visual_evidence`, `data.purpose`, `data.recommended_resource`,
`data.feedback_schema` + `data.feedback_prompt` (LOOK phase — tells the agent what JSON
to fill for this purpose), and when judgment is present `data.visual_feedback`
(normalized) + advisory `data.next_actions`. `agent_summary.advisory` carries the loop:
LOOK → fill judgment → act → re-call.

## Purpose shaping

| purpose | pack default | feedback focus | typical next_actions |
|---|---|---|---|
| design | design | hierarchy, brand, density, first viewport | design_review / remeasure |
| consistency | design | token drift, spacing rhythm vs PDG | propose_fix / assess |
| component | viewport (+element) | fit, visual match to surrounding UI | select_foundation / search |
| inspiration | full | borrow[] / ignore[] (layout, type, color) | inspiration_collect / snapshot |
| hotfix | viewport/element | blast radius, before/after | verify / observe element / diff |
| forms | section/viewport | labels, errors, affordances | probe_form / verify invalid→valid |
| general | viewport | free notes + issues[] | observe / verify |

## Architecture (reuse-first)

- `visual_feedback_policy.py` (new, visual_browser_intelligence/visual): purpose
  registry (pack default, recommended_resource, feedback schema/prompt, extra feedback
  keys) + purpose-aware wrappers. Core normalize/pack/action logic stays in
  `design_evidence_policy.py` — one code path.
- `visual_feedback_handlers.py` (new, mcp): `run_visual_feedback(...)` shared runner
  (capture-or-reuse → attach → schema/prompt → feedback → next_actions) and
  `handle_visual_feedback(...)` for the new tool.
- `attach_design_visuals` becomes a thin wrapper: maps tool → purpose
  (design/consistency) and delegates to `run_visual_feedback`. The four
  design/consistency tools keep their `visual_feedback` args as compatible aliases.
- Capture: `capture_design_evidence` + `_capture_or_reuse_visuals` (existing).
  Images: `attach_visual_paths` / `envelope_to_mcp_contents` (existing).
- Section regions come from the design snapshot bound to the scan when available;
  otherwise pack degrades gracefully to viewport/full.

## Out of scope

Vision model inside MCP; embeddings; replacing `perception_observe`; SEO/Figma parked
work; removing the alias args from design/consistency tools (later cleanup).

## Testing

Unit: purpose registry (pack/resource/schema per purpose), purpose-shaped normalize
(extras preserved), purpose next_actions (inspiration→collect, forms→probe_form, ...).
Handler: LOOK phase attaches images + schema; judgment phase returns next_actions;
never raises on bad envelope; offline scan reuse. Aliases: existing
test_design_visual_evidence must keep passing unchanged.
