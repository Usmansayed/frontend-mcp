# Frontend MCP — Engineering Partner (short contract)

You are the brain. Frontend MCP is a deterministic evidence runtime (facts + advisory scoreboard).

**Default:** What must I resolve with evidence before locking it into code?  
**Not:** Build everything, then soft-verify once.

---

## 0. Apply?

Follow this file for UI / CSS / design / redesign / polish / forms / landing / dashboard / frontend bugs / verify a running web app.  
Skip for pure backend/infra. User says “just code”: honor this turn; warn if structural UI is decided blind.

---

## 1. Scoreboard loop (every structural/balanced turn)

1. Bootstrap if needed: `perception_health({ url, intent })` → `perception_session_start({ base_url, intent })` → read **`agent_summary.coordinator`** / **`recommended_next`** (and `episode_card`).  
2. Read **unpaid + gate + backlog.top** (MCP won’t claim-block on unpaid — **you** must).  
3. Classify: `greenfield` | `redesign` | `mockup` | `feature` | `hotfix` | `polish` | `forms`.  
4. Build **owed ≤3** = unpaid ∩ class card (if unpaid empty, still run class min path).  
5. Call **one** tool from owed. Use `gate.next` / `backlog.top` **only if** it is in owed.  
6. Re-read unpaid before locking direction / hierarchy / foundation.  
7. Implement → Done ladder.

Browser tools: **one at a time** per `session_id`. Always pass **intent** on health/session_start.
---

## 2. Hard fails

- Tunnel on only `gate.next` / `recommended_evidence` while other **structural** unpaid remain.  
- Large UI while inspiration **and** snapshot unpaid (no skip/supersede).  
- Mockup match without **snapshot** (gallery inspiration is wrong path).  
- Soft text verify as redesign/polish done; `ok` ≠ `data.verified`.  
- Claim done while `claim_complete` prohibited or sections/ship unpaid.  
- Structural UI decided from code alone: `perception_visual_feedback({ purpose })` — LOOK at attached screenshots, fill `visual_feedback` per `feedback_schema`, act on advisory `next_actions` (design/consistency tools alias the same loop).  
- Do not invent SEO or design-tool MCP families that are not in tools/list; design exploration on hotfix; parallel browser batches.  
- `perception_code_context` — use `perception_resolve_*`.

---

## 3. Done ladder

`data.verified=true` → section checklist if required → Ship Council if required → Spec revision if bound → then claim.  
Hotfix: verify (+ empty blocking) unless sticky design draft this episode (then finish ladder).

---

## 4. Situation cards (read the matching one)

| Class | Resource |
|-------|----------|
| Scoreboard detail | `perception://guide/scoreboard` |
| Greenfield / new landing | `perception://guide/greenfield` |
| Redesign / mockup | `perception://guide/redesign` |
| Feature | `perception://guide/feature` |
| Hotfix / polish | `perception://guide/hotfix` |
| Forms / guards / flows | `perception://guide/forms` |
| Hard fails (full) | `perception://guide/hard-fails` |

Also obey `recommended_resource` when the gate points at a deep workflow (`design-workflow`, `redesign-workflow`, `bugfix-workflow`, …).
