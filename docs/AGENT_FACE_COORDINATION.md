# Agent face + coordination layer — operator guide

**Version:** `1.2.0.dev52` (ship target)  
**Audience:** Host agents (Cursor) and humans debugging MCP coordination.

## What you follow every turn

1. `perception_health({ url, intent })` → `perception_session_start({ base_url, intent })`
2. Read **`agent_summary.card`** only (primary contract)
3. Call `card.next` with `card.next_args` (fill `<placeholders>` from intent)
4. Pay `card.owed` (≤3) before large UI
5. Claim only when `data.verified=true` **and** `card.claim_ok`

Optional depth: `resources/read` → `card.resource` (`perception://spine/{class}`).

## Card fields (contract)

| Field | Meaning |
|-------|---------|
| `class` | `greenfield` \| `redesign` \| `feature` \| `hotfix` \| `forms` |
| `depth` | `light` \| `standard` \| `full` — do not invent ceremony beyond `finish[]` |
| `next` | Exact tool to call; empty + `claim_ok` → stop and claim |
| `next_args` | Args template; may include `then` for a follow-up tool |
| `owed` | Unpaid families (pay these) |
| `gate` | `blocked` \| `provisional` \| `maintenance` \| `ready` |
| `claim_ok` | False while verify unpaid or `claim_extra` non-empty |
| `claim_extra` | Remaining ceremony (sections / ship / spec revision) |
| `finish` | Checklist with `todo` / `done` / `skip` / `blocked` |
| `resource` | Short spine URI |

## Hard fails

- `ok=true` ≠ `data.verified=true`
- Skip bootstrap on structural UI
- Tunnel past unpaid structural families
- Claim while `claim_ok=false`
- Parallel browser batches on one `session_id`
- Decide redesign/polish from code alone without LOOK / `visual_feedback`

## Regression boards (must stay green)

```text
python -m pytest tests/test_coordinator_card.py -q
python scripts/eval_agent_face_hard_matrix.py
python scripts/eval_agent_face_phase2_obedience.py
python scripts/eval_agent_face_discoverability.py
python scripts/eval_agent_face_phase3_reliability.py
python -u scripts/eval_agent_face_no_guide_e2e.py --cases forms,hotfix,greenfield,redesign,feature,polish,hotfix_stamped_feature,landing_signup_not_forms,checkout_feature_not_forms
python -m pytest tests/decision_lab/test_exp023_episode_card.py -q
python scripts/hard_done_ladder_sim.py
```

## Deep archives

- Spines: `perception://spine/*`
- Long guides: `perception://guide/*` / `perception://*-workflow`
- Design program: `docs/superpowers/specs/2026-07-28-coordination-perfection-design.md`
