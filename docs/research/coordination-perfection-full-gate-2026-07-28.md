# Full-gate evidence — 2026-07-28 (`1.2.0.dev52`)

## Command

```text
python scripts/eval_agent_face_full_gate.py
```

## Result: **ALL BOARDS PASS**

| Board | Result |
|-------|--------|
| unit_card | PASS |
| decision_lab_baseline (26 scenarios) | PASS — hotfix scenario aligned to verify-before-claim |
| hard_matrix | PASS **26/26** |
| obedience | PASS 6/6 |
| discoverability | PASS **8/8** score **1.0** (`EASY_ENOUGH`) |
| done_ladder | PASS |
| phase3 reliability | PASS 6/6 |
| no_guide_e2e | PASS **9/9** |

## Fixes in this ship

1. Decision Lab `hotfix_surgical_path` — expect `claim_complete` prohibited until verify (closes false-green)
2. Discoverability tool_volume — pass when tools are ≥90% grouped (card + groups = progressive discovery)
3. Core tool “how” cues — recognize Does/Returns/Next enrichment
4. Operator doc — `docs/AGENT_FACE_COORDINATION.md` + getting-started pointer
5. Full gate runner — `scripts/eval_agent_face_full_gate.py`

## Honest scope

Boards green ≠ every one of 73 tools proven forever. It means the **agent-face coordination contract** (classify, card, claim ladder, latency bounds, decision lab baseline) has no known P0/P1 failures on the regression gate.
