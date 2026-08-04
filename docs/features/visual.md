# Visual subsystem

**Status:** ✅ shipped  
**Modules:**

- `visual_browser_intelligence/visual/visual_capture.py` — screenshot capture + design evidence packs
- `visual_browser_intelligence/visual/design_evidence_policy.py` — pack policy + visual feedback → next_actions
- `visual_browser_intelligence/visual/visual_response.py` — MCP `ImageContent` attachments
- Design Sense heuristics `visual_insights` — layout signals

## Screenshot modes (observe / verify)

| Mode | Description |
|------|-------------|
| `viewport` | Visible viewport |
| `full` | Full scrollable page |
| `element` | CSS selector crop |

## Common visual feedback — `perception_visual_feedback`

ONE shared LOOK → judge → act loop for any UI work. `purpose` shapes the pack default,
the guide pointer (`recommended_resource`), the feedback JSON the agent fills
(`feedback_schema` / `feedback_prompt`), and the advisory `next_actions` routing:

| `purpose` | Pack default | Purpose extras in feedback |
|-----------|--------------|----------------------------|
| `design` | `design` | `hierarchy_issues[]` |
| `consistency` | `design` | `standard_hints[]` |
| `component` | `viewport` | `slot_notes` |
| `inspiration` | `full` | `borrow[]` / `ignore[]` |
| `hotfix` | `viewport` | `regression_watch[]` |
| `forms` | `section` | `field_issues[]` |
| `general` | `viewport` | — |

| Pack (`screenshot_pack`) | Captures |
|--------------------------|----------|
| `auto` (default) | → purpose default (`design` for design/consistency) |
| `design` | annotated viewport + full page + section crops |
| `viewport` | annotated viewport only |
| `full` | viewport + full page |
| `section` | viewport + full (for crops) + preferred section crops |
| `element` | viewport + element crop (`screenshot_selector`) |
| `none` | skip capture (`include_screenshots: false`) |

Section crops use layout region rects (`header` / `nav` / `main` / `footer` / …). Pass `focus_sections` or `visual_feedback.focus_sections` to prefer flagged blocks.

Thin aliases: `perception_build_design_snapshot`, `perception_design_review`, `perception_consistency_review`, `perception_consistency_audit` accept the same visual args and run the same shared code path (`purpose=design|consistency` implied).

### Visual feedback loop

1. Call `perception_visual_feedback` with `purpose` (or a design/consistency tool) → **LOOK** at inline images (`data.visual_evidence`); LOOK phase returns `feedback_schema` + `feedback_prompt`.
2. Re-call with `visual_feedback` (or flat `visual_notes` / `visual_judgment` / `focus_sections`):
   - `judgment`: `ok` | `needs_work` | `unclear`
   - `notes`, `focus_sections`, `focus_selector`, `issues[]` + purpose extras
3. Read `data.next_actions` — **advisory** tool hints (`verify_section`, `propose_consistency_fix`, `edit_then_remeasure`, `collect_inspiration`, `probe_form`, `diff_after_fix`, …). The agent decides.
4. Edit UI → re-LOOK → repeat.

## Annotations

Pillow overlays for:

- Interactive elements (from DOM scan)
- Layout issue highlights from `visual_insights`

## visual_insights signals

Deterministic checks (no LLM):

- Horizontal/vertical overflow
- Overlapping clickables
- Zero-size interactive elements
- Off-screen clickables
- Tiny touch targets (threshold)

Mapped to `agent_summary.visual` and optional `blocking`.

## Diff

`perception_diff` produces:

- `visual_diff.side_by_side` — combined image
- `visual_diff.heatmap` — pixel difference heatmap

Inline PNGs in MCP response.

## Resources

- `perception://scan/{id}/screenshot.png`
- `perception://scan/{id}/screenshot-annotated.png`
- `perception://scan/{id}/screenshot-crop.png`

## Tests

- `tests/test_design_visual_evidence.py` — pack capture + attach + feedback next_actions
- `tests/test_design_evidence_policy.py` — pack resolution + feedback normalization
- Live harness: `src/run_design_visual_smoke.py`
