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

## Design / consistency evidence packs

Design intelligence and consistency tools **attach rendered screenshots by default** so the agent edits from appearance, not code alone.

| Pack (`screenshot_pack`) | Captures |
|--------------------------|----------|
| `auto` (default) | → `design` for snapshot / design_review / consistency_* |
| `design` | annotated viewport + full page + section crops |
| `viewport` | annotated viewport only |
| `full` | viewport + full page |
| `section` | viewport + full (for crops) + preferred section crops |
| `element` | viewport + element crop (`screenshot_selector`) |
| `none` | skip capture (`include_screenshots: false`) |

Section crops use layout region rects (`header` / `nav` / `main` / `footer` / …). Pass `focus_sections` or `visual_feedback.focus_sections` to prefer flagged blocks.

Tools: `perception_build_design_snapshot`, `perception_design_review`, `perception_consistency_review`, `perception_consistency_audit`.

### Visual feedback loop

1. Call a design/consistency tool → **LOOK** at inline images (`data.visual_evidence`).
2. Re-call with `visual_feedback` (or flat `visual_notes` / `visual_judgment` / `focus_sections`):
   - `judgment`: `ok` | `needs_work` | `unclear`
   - `notes`, `focus_sections`, `focus_selector`, `issues[]`
3. Read `data.next_actions` — ranked tool hints (`verify_section`, `propose_consistency_fix`, `edit_then_remeasure`, …).
4. Edit UI → remeasure with screenshots → repeat.

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
