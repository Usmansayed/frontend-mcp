# Forest F08 — Design Review & Consistency

**Root:** S09 consistency
**Target leaves:** ~16
**Archetype coverage:** all UI projects, especially design_system_site, saas_dashboard, component_library.

## Root decision points

1. **PDG state** — empty vs partially seeded vs mature.
2. **Design source** — codebase-only vs +Figma vs +tokens files.
3. **Review type** — Design Sense (heuristic critique) vs Consistency Audit (standard-based) vs both.
4. **Fix path** — propose fix vs open issue vs accept deviation.

## Notable branches

- PDG empty → refresh discovery (multi-source) → summary → then audit.
- Snapshot exists, Design Sense produces critiques → advisory queue.
- Consistency assess: selector matches token deviation → propose fix → verify after apply.
- Exception documented (`consistency exception`) → state tagged `verified` for that rule.
- Design system evolves (new tokens) → schedule PDG refresh → invalidate prior audits.

## Pruning notes

- Individual rule types (spacing vs color vs typography) merged; behavior branches only.
- Scaffolded PDG validators marked `mcp_ready: false`.

## Cross-links out

- F03 (replace non-conforming component)
- F04 (apply proposed fix)
- F02 (design source needs update)
- F12 (PDG refresh fails)
