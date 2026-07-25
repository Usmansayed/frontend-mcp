# Design Sense Roadmap — Progress

## Target architecture

```text
perception_observe
        ↓
perception_build_design_snapshot
        ↓
perception_design_review
        ↓
perception_consistency_review
```

## Status

| Priority | Item | Status |
|----------|------|--------|
| P1 | MCP `perception_build_design_snapshot` | ✅ |
| P1 | MCP `perception_design_review` | ✅ |
| P1 | MCP `perception_consistency_review` | ✅ |
| P1 | Auto snapshot from `scan_id` | ✅ |
| P1 | Inline screenshots + visual_feedback → next_actions | ✅ |
| P2 | Contrast matrix, layout tree in snapshot | ✅ v1 |
| P2 | Typography hierarchy, spacing rhythm | ✅ v1 |
| P3 | Designlang optional augment (`DESIGNLANG_ENABLED`) | ✅ scaffold |
| P3 | Designlang MCP integration | 🔲 future |
| P4 | Reference registry seeds (Stripe, Linear, …) | ✅ fixture seeds |
| P4 | Live reference capture | 🔲 future |
| P5 | Consensus engine (dedupe, merge, prioritize) | ✅ v1 |
| P6 | Actionable findings (evidence, confidence, confirmed) | ✅ v1 |
| P6 | Suppress generic "Verify:" when snapshot present | ✅ |
| P7 | Benchmark metrics (actionable, generic, confirmed) | ✅ |

## Default agent workflow

1. `perception_session_start`
2. `perception_navigate_and_observe` → save `scan_id`
3. `perception_build_design_snapshot` / `perception_design_review` with `{ "scan_id", "user_task" }`
   — **LOOK** at attached viewport / full / section screenshots
4. Pass `visual_feedback` (`judgment`, `notes`, `focus_sections`) → follow `next_actions`
5. Optional: `perception_consistency_review` with same `scan_id` + visual feedback loop
6. Edit → remeasure with screenshots → Done ladder (verify → sections → Ship)

No manual `ReviewRequest` construction required.

## Visual evidence

Design/consistency tools default to `screenshot_pack: design` (viewport + full + sections).
Details: [visual.md](./visual.md).

## Next steps toward 80%+

- Auto-call snapshot build after observe (optional flag on observe)
- Capture live reference snapshots for registry catalog URLs
- Designlang MCP merge into snapshot sections
- Responsive viewport snapshots
- Benchmark precision/recall labels on synthetic cases
