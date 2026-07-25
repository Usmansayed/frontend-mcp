# Coordination Initiative & Residue — Implementation Plan

> **For agentic workers:** Implement task-by-task. Prefer TDD for pure functions first.

**Goal:** Episode-level coordination (surface type, ROI backlog, evidence terminals, one-pass residue, advisory initiative, episode confidence) for design-scope work only.

**Architecture:** Extend `EpisodeState`, `compile_engineering_strategy`, `compile_implementation_readiness`, and Ship Council detectors. No new MCP tools.

**Tech Stack:** Python, existing PSM / pytest.

---

## File map

| File | Responsibility |
|------|----------------|
| `models.py` | `EpisodeState.surface_type`; persist full useful `retry_counters` |
| `planning/surface_type.py` | Derive + sticky apply surface type |
| `planning/episode_backlog.py` | ROI-ranked backlog |
| `planning/evidence_plan_status.py` | completed / skipped / superseded helpers |
| `planning/episode_confidence.py` | score + contributors |
| `planning/implementation_readiness.py` | Gate: residue + evidence terminals |
| `planning/engineering_strategy.py` | Wire backlog, initiative, confidence, surface |
| `planning/ship_council.py` | Surface-gated signals + residue flag interaction |
| `planning/situation_policy.py` | Expose surface_type in discriminators |
| `tests/test_coordination_initiative.py` | Focused unit suite |

---

### Task 1: Models + surface_type pure functions

- [x] Add `surface_type: str = "unknown"` to `EpisodeState` + `to_dict`
- [x] Preserve `evidence_plan_status` and `residue_scan` in `retry_counters` serialization
- [x] Write `surface_type.py` with `derive_surface_type(intent, snapshot=None) -> str` and `apply_surface_type(psm, …)` sticky rules
- [x] Tests: settings/dashboard/auth/marketing intents

### Task 2: Evidence plan terminals

- [x] `evidence_plan_status.py`: get/set status; `VALID_SKIP_REASONS`; `plan_item_terminal`; `open_evidence_plan_items`
- [x] Auto-supersede map: e.g. figma/design_snapshot success can supersede inspiration for `design_reference`
- [x] Tests: skip valid/invalid; superseded; open blocks

### Task 3: Backlog + confidence

- [x] `episode_backlog.py`: `compile_episode_backlog(...)` → `{top, items, answered_next}`
- [x] `episode_confidence.py`: `compile_episode_confidence(...)` → `{score, band, contributors}`
- [x] Tests: top = max ROI; confidence contributors sign

### Task 4: Gate + strategy wire

- [x] `compile_implementation_readiness`: design-scope only — residue_required, evidence_plan_incomplete
- [x] `compile_engineering_strategy`: set surface, backlog, initiative, confidence on strategy dict
- [x] Hotfix unaffected test

### Task 5: Ship surface signals + residue

- [x] Settings measure / footer signals when `surface_type == settings_form`
- [x] Skip equal_weight_kpi on settings_form
- [x] Residue: require one snapshot rebuild when thin/zero-challenge dense; set completed after
- [x] Tests

### Task 6: Methodology one-liners + version bump note

- [x] Update `perception://engineering-strategy` / ship-council briefly
- [ ] Leave publish to user request (`1.2.0.dev11`)
