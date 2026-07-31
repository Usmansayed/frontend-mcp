# Agent face + coordination layer — operator guide

**Version:** `1.2.0.dev56` (ship target)  
**Audience:** Host agents (Cursor) and humans debugging MCP coordination.

## What you follow every turn

1. `perception_health({ url, intent })` → `perception_session_start({ base_url, intent })`
2. Read **`agent_summary.card`** (primary contract). If `card.conflict` is present, prefer gate + unpaid over `card.next` alone.
3. Call `card.next` with `card.next_args` (fill `<placeholders>` from intent)
4. Pay **entire** `card.owed` / `card.pack.critical` before large UI (not one silo)
5. While `card.implement_blocked`, gather pack evidence only — do not invent structural layout
6. Claim only when `data.verified=true` **and** `card.claim_ok`
7. Ignore `finish[]` items with `status=skip` (not required by gate)

Optional depth: `resources/read` → `card.resource` (`perception://spine/{class}`).

## Evidence Pack Loop (use-band)

Server owns the integrated loop. Agents do **not** pick a silo (browser **or** component **or** design).

| Band | Maps to | When |
|------|---------|------|
| `light` | touch_up | hotfix / forms / explicit surgical CSS-bug |
| `medium` | polish | explicit chrome/polish cues |
| `heavy` | feature | **default for normal UI** (observe + LOOK + verify; component if unpaid) |
| `very_heavy` | initiative | greenfield / redesign / sticky design |

Subtraction is server-owned (class × band × gate). Pass `effort_tier=light|touch_up` only for true surgical work.

## Card fields (contract)

| Field | Meaning |
|-------|---------|
| `class` | `greenfield` \| `redesign` \| `feature` \| `hotfix` \| `forms` |
| `depth` | `light` \| `standard` \| `full` — do not invent ceremony beyond `finish[]` |
| `evidence_band` | `light` \| `medium` \| `heavy` \| `very_heavy` |
| `pack` | `{ id, phases[], critical[], remaining[] }` — ordered unpaid families |
| `implement_blocked` | True while greenfield/redesign heavy+ still has structural critical unpaid |
| `next` | Exact tool to call; empty + `claim_ok` → stop and claim |
| `next_args` | Args template; may include `then` for a follow-up tool |
| `owed` | Unpaid families (≤3; ordered from pack; gate family ranks first) |
| `gate` | `blocked` \| `provisional` \| `maintenance` \| `ready` |
| `claim_ok` | False while verify unpaid, `claim_extra` non-empty, or pack `critical` unpaid |
| `claim_extra` | Remaining ceremony (sections / ship / spec revision) |
| `finish` | Checklist with `todo` / `done` / `skip` / `blocked` |
| `resource` | Short spine URI |
| `conflict` | Optional; present when class/owed still disagree with structural unpaid/gate |

Note: coordinator `confidence.band` ≠ face `evidence_band`.

## Hard fails

- `ok=true` ≠ `data.verified=true`
- Skip bootstrap on structural UI
- Tunnel past unpaid structural families / pack.critical
- Large UI while `implement_blocked`
- Claim while `claim_ok=false`
- Parallel browser batches on one `session_id`
- Decide redesign/polish from code alone without LOOK / `visual_feedback`
- Chase `finish.section_checklist=todo` when gate did not require it (should be `skip`)
- Force gallery inspiration on hotfix/forms

## Regression boards (must stay green)

```text
python -m pytest tests/test_coordinator_card.py tests/test_evidence_pack.py -q
python scripts/eval_agent_face_hard_matrix.py
python scripts/eval_coordination_pack_scenarios.py
python scripts/eval_agent_face_phase2_obedience.py
python scripts/eval_agent_face_discoverability.py
python scripts/eval_agent_face_phase3_reliability.py
python -u scripts/eval_agent_face_no_guide_e2e.py --cases forms,hotfix,greenfield,redesign,feature,polish,hotfix_stamped_feature,landing_signup_not_forms,checkout_feature_not_forms
python -m pytest tests/decision_lab/test_exp023_episode_card.py -q
python scripts/hard_done_ladder_sim.py
```

Scenario answer key: `docs/research/coordination_pack_scenarios.md` (~50 intents).  
**Live copy-kit (paste into another project):** `docs/research/coordination_pack_live_kit/` — includes `STARTER_PROMPT.md` + `ANSWER_KEY.md` + `SCENARIOS.json` + `SCORECARD.md`.

## Deep archives

- Spines: `perception://spine/*`
- Long guides: `perception://guide/*` / `perception://*-workflow`
- Design program: `docs/superpowers/specs/2026-07-28-coordination-perfection-design.md`
