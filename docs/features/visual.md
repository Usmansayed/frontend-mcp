# Visual subsystem

**Status:** ✅ shipped (v0.2.0)

**Modules:**

- `perception/visual_capture.py` — screenshot capture
- `perception/visual_insights.py` — layout signals
- `perception/visual_diff.py` — comparison
- `mcp/visual_response.py` — MCP `ImageContent`

## Screenshot modes

| Mode | Description |
|------|-------------|
| `viewport` | Visible viewport |
| `full` | Full scrollable page |
| `element` | CSS selector crop |

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

## Future (backlog)

- Multi-viewport contact sheet
- Per-element heatmap region stats
- Visual criteria in `perception_verify`

## Tests

Contract tests: `inline_images`, `visual_diff`
