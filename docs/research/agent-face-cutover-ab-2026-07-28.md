# Agent-face cutover A/B (2026-07-28)

**Decision:** Cut over to **card-first** face on `exp/agent-face-simple`.

## Control vs simple

| Dimension | Control (pre-face / long guide) | Simple (card face) |
|-----------|----------------------------------|--------------------|
| Always-on | Long MCP instructions + AGENT_GUIDE | Short spine + `agent_summary.card` |
| Next tool | Buried in coordinator / guides | `card.next` + `card.next_args` (+ `then`) |
| Forms path | Often gate → component plan | Forced `probe_form` |
| Redesign | Snapshot easy to skip | Observe → `then` snapshot, owed re-inject |
| Claim | `maintenance` looked claim-ok early | `claim_ok` false until verify |
| Hang risk | Select without query / 90s wall | Args + 35s timeout + ladder floor |

## Harness A/B proxy (no-guide)

Same four intents, **no** `resources/read` of guides:

| Case | Control-era symptom | Simple result |
|------|---------------------|---------------|
| forms | component detour / hang | PASS, probe-only |
| hotfix | OK | PASS |
| greenfield | select loop / plan bounce | PASS, next→verify |
| redesign | follow ~0.67, no snapshot | PASS follow=1.00 + snapshot |

**BOARD:** PASS 4/4 (~40–50s).

## Human A/B (optional follow-up)

Still useful on real chats (6 prompts × 2 faces). Cutover is justified by harness + unit contracts; human A/B can refine, not block.

## Remaining (non-blocking)

- Tool catalog still large (~73) — card must stay trusted
- Ship/sections auto-clear in harness not required for cutover
- Reload MCP after deploy
