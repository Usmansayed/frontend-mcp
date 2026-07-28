# Phase 3 — Latency / reliability SLOs

**Date:** 2026-07-28
**Board:** `scripts/eval_agent_face_phase3_reliability.py`

## Tool wall-clock SLOs (local sandbox)

| Tool | SLO (ms) |
|------|----------|
| `perception_health` | 5000 |
| `perception_session_start` | 20000 |
| `perception_navigate_and_observe` | 25000 |
| `perception_probe_form` | 20000 |
| `perception_verify` | 20000 |
| `perception_inspiration_collect` | 60000 |
| `perception_select_component_foundation` | 15000 |
| `perception_visual_feedback` | 15000 |
| `path_forms` | 120000 |
| `path_hotfix` | 90000 |
| `path_feature` | 90000 |
| `path_greenfield_light` | 180000 |

## Pass criteria

1. `path_forms` / `path_hotfix` / `path_feature` → `data.verified=true`
2. No false-green (`ok` without `verified` on required verify)
3. `inspiration_bounded` / `select_bounded` return within SLO (hang = FAIL)
4. Soak ≥3 sequential sessions without crash
5. Feature class stable across observe (no host_action polish flip)

## Non-goals

- Inspiration provider perfection (degraded-but-bounded is OK)
- Shrinking the 73-tool catalog

