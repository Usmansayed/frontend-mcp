# Forest F02 — Design-Led Build

**Root:** S03 (design)
**Target leaves:** ~20
**Archetype coverage:** landing, marketing, saas, ecommerce, dssite. Origin any.

## Root decision points

1. **Figma connected?** yes → normalized context; no → is a PAT expected?
2. **Design system present?** none / captured-in-PDG / documented externally.
3. **Inspiration needed?** yes → discover → cleanup; no.
4. **Snapshot baseline available?** existing snapshots vs none.

## Notable branches

- Figma connected + PDG populated → `design_source: known`, `design_system: known` — proceed to S04.
- Figma expected but PAT invalid → `global.figma_connect_failed` (do not loop).
- Inspiration collected, blob session opened but not closed → recovery via forced `session_end`.
- Design system exists but out of date vs live UI → schedule discovery run before proceeding.
- Design signed off, no code yet → S04 architecture decisions.

## Pruning notes

- Variants where design decisions are already documented externally and the agent just reads them: merged into one "design_source: known, design_system: known" state.
- Multi-file Figma (roadmap gap) → `mcp_ready: false` branch marked.

## Cross-links out

- F03 (component search once design decided)
- F04 (implementation with design in hand)
- F08 (design-review of an existing snapshot as part of design phase)
- F12 (Figma degraded)
