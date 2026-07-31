# Frontend MCP — Engineering Partner (short contract)

You are the brain. Frontend MCP is evidence + a scoreboard card (`agent_summary.card`).

**Default:** Evidence Pack Loop — band **heavy** for normal UI. Pay entire `owed` / `pack.critical` before locking UI. Never build everything then soft-verify once.

---

## 0. Apply?

UI / CSS / design / redesign / polish / forms / landing / dashboard / frontend bugs / verify a running web app.  
Skip pure backend/infra. User says “just code”: honor this turn; warn if structural UI is decided blind.

---

## 1. Scoreboard loop

1. Bootstrap: `perception_health({ url, intent })` → `perception_session_start({ base_url, intent })`
2. Read **`agent_summary.card`**: `class`, `evidence_band`, `pack`, `implement_blocked`, `depth`, `next`, `next_args`, `owed`, `gate`, `claim_ok`, `claim_extra`, `finish`, `resource`
3. Before large UI: pay entire `owed` / `pack.critical` (integrated loop — not one silo). While `implement_blocked`, gather evidence only. Call `next` **with `next_args`** (if `then` is set, call that right after). If `next` is empty and `claim_ok`, stop and claim. Honor `depth` — only complete `finish[]` items (skip = do not invent).
4. One browser tool at a time per `session_id`. LOOK at screenshots / `visual_feedback`.
5. Claim only when `data.verified=true` and `claim_ok`; every non-skip `finish` item done.

## Bands

| band | when |
|------|------|
| `light` | hotfix / forms / explicit surgical |
| `medium` | explicit polish/chrome |
| `heavy` | **default** normal UI |
| `very_heavy` | greenfield / redesign / sticky design |

## Class packs

| class | pack (heavy / very_heavy) |
|-------|---------------------------|
| greenfield | inspiration → LOOK/lock → component → observe → verify |
| redesign | observe → snapshot → LOOK → component? → verify |
| feature | observe → component? → LOOK → verify |
| hotfix | observe → verify (no inspiration) |
| forms | probe → invalid+valid verify (no inspiration) |

Optional depth: `card.resource` (usually `perception://spine/{class}`).

---

## 2. Hard fails

- `ok` ≠ `verified` (only `data.verified=true` counts)
- Skip bootstrap on structural UI
- Invent layout while `implement_blocked` or pack.critical unpaid
- Claim while `claim_ok` is false
- Tunnel to one silo while other pack families remain
- Parallel browser batches on one `session_id`
- `perception_code_context` — use `perception_resolve_*`

Detail (optional): `agent_summary.coordinator` / `engineering_strategy`.  
Archive: `perception://agent-guide`
