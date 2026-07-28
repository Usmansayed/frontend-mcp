# Hard / adversarial agent-face tests — 2026-07-28

## Why
Happy boards (obedience 6/6, early no-guide 4/4) were not enough. Harder matrix + expanded live E2E found real classifier bugs.

## Boards

| Board | Result |
|-------|--------|
| `scripts/eval_agent_face_hard_matrix.py` | **PASS 22/22** (after fixes) |
| Unit `tests/test_coordinator_card.py` | **36 passed** |
| Phase 2 obedience | **PASS 6/6** |
| Hard done-ladder sim | **PASS** |
| Discoverability | **0.95** (known fail: 73 tools) |
| Expanded no-guide E2E (9 cases) | first run **7/9**; feature flip fixed in classify — recheck |

## Bugs found by harder tests (not on happy path)

1. **Forms over-capture** — soft keywords `checkout|signup|login|auth` stole:
   - landing + signup → forms (want greenfield)
   - “pricing feature … checkout page” → forms (want feature)
   - “fix checkout copy” → forms (want hotfix)
2. **Redesign + checkout** → forms (redesign must beat soft forms keywords)
3. **Feature face flips after observe** — two causes:
   - `task_scope=debug` (cluster.debug) collapsed face to hotfix; feature intent must win
   - **`host_action` “RIGHT-SIZE POLISH …” matched polish cues** and flipped feature→hotfix even when `task_scope=feature_incremental` and intent was clearly a feature (live dump confirmed this)

## Fixes (`coordinator_card.classify_agent_face`)

- Hard forms = `/forms/` + probe/validation language; soft keywords yield to landing/feature/fix cues
- Redesign check **before** soft forms
- Feature intent language wins over bare `scope=debug`
- Explicit hotfix/surgical + intent fix cues still beat feature
- **Do not classify from `host_action`** — advisory polish/right-size text must not reclassify the face

## Boards (after fixes)

| Board | Result |
|-------|--------|
| Hard matrix | **PASS 23/23** |
| Unit card | **37 passed** |
| Obedience | **PASS 6/6** |
| Hard done-ladder | **PASS** |
| Discoverability | **0.95** (73 tools) |
| Expanded no-guide E2E (9) | **PASS 9/9** |

## Remaining gaps (not claimed perfect)

- Discoverability tool volume (73 tools)
- Phase 3 reliability (latency / soak / inspiration) not started
- Live Cursor MCP must be **reloaded** after classify fixes
