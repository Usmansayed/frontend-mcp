# Coordination Layer

**Status:** Release candidate — **feature complete and frozen** (2026-07-12)

See **[RELEASE.md](RELEASE.md)** for baseline metrics, architecture, change policy, and regression workflow.

---

## Layout

```
coordination_layer/
  RELEASE.md                 # Frozen baseline — start here
  runtime/                   # R0–R11 generated artifacts (v1.0.0)
  distillation/              # Build script + curated sources
  validation/                # CVW-01..14 workflow specs
  research/                  # 150-state corpus (design reference only)
```

## Quick reference

| Need | Location |
|------|----------|
| Run regression suite | `python src/run_coordination_validation.py` |
| Coordinator implementation | `src/navigation/coordination_intelligence/` |
| Validation reports | `evals/coordination/reports/` |
| Score history | `evals/coordination/score_history.jsonl` |
| Refinement log | `evals/coordination/refinement_log.md` |
| Architecture (frozen) | `research/reports/07_*.md`, `08_*.md` |

## Rebuild runtime artifacts

Only when a proven artifact gap requires it:

```bash
pip install pyyaml
python coordination_layer/distillation/build.py
```

## Research corpus

`research/` is a **research-only** corpus that informed artifact design. The 150 research states are distilled into clusters and lexicon — they **never** participate in runtime control flow.

For corpus navigation, see the original research README sections in git history or `research/reports/01_mcp_module_inventory.md` through `05_coordination_design_input.md`.
