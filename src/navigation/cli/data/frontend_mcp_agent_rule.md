# Frontend MCP — Engineering Partner

You are the brain. Frontend MCP is a deterministic evidence runtime (no LLM inside it).
Facts only — you decide. Goal: MCP shapes **engineering decisions**, not call count.

**Default question:** What must I resolve with evidence before locking it into code?  
**Not:** Build everything, then observe/verify once.

---

## 0. Apply?

Classify every turn. **Follow this whole file** if the task touches any of:

- UI pages/screens/components/layouts/CSS · visual design/branding/tokens/theming
- Landing/dashboard/design-system work · frontend bugs/layout/responsive/regressions
- Forms, client routing, auth **UI**, multi-step flows · Figma/inspiration **for UI**
- On-page a11y/SEO · “check the page” / polish / verify a running web app

**Full-stack:** apply to the UI half (screens + verify).  
**Skip this file:** pure backend/API/DB/infra/CI, non-web clients, docs/scripts with no frontend outcome. Mixed → apply to the UI portion only.

User says skip MCP / “just code”: honor for this turn; still warn if structural UI is decided blind.

When this file applies: **must** follow it. End-of-task MCP-only is a process fail.

---

## 1. Session order (non-negotiable)

**Failure mode to stop:** code the UI from taste → one soft verify (or none) → claim done.
False-green: text matches while sticky/overflow/hierarchy/shell are wrong.

Before substantial UI (new screen, redesign, full-viewport, dashboard/landing draft):

| Step | Action |
|------|--------|
| 1 | `resources/read` → `perception://getting-started` |
| 2 | `perception_health({ url, intent })` — **real user intent**, not a stub |
| 3 | If reachable: `perception_session_start({ base_url, intent })` → save `session_id` |
| 4 | Read `agent_summary.engineering_strategy` |
| 5 | Obey `implementation_gate` (see §3) |
| 6 | `resources/read` → `engineering_strategy.recommended_resource` |
| 7 | Minimum evidence for **unresolved** decisions only (§4) → then implement |
| 8 | After ACT: Done ladder (§6) |

If steps 1–6 are not done this session for an applicable task → **stop coding and bootstrap**.  
Browser tools: **one at a time** per `session_id` (no parallel batches).

Surgical hotfix already mid-debug: may start at observe → fix → verify; still require `data.verified=true`.

---

## 2. Fields that bind you

After health/session_start/observe, read these — not vibes:

| Field | You must |
|-------|----------|
| `engineering_strategy.influence_level` | Size evidence budget (§4) |
| `engineering_strategy.unresolved_decisions` | Resolve these before broad code |
| `engineering_strategy.recommended_resource` | Read that methodology URI next |
| `engineering_strategy.recommended_evidence` / `suggested_queries` | Prefer these calls |
| `implementation_gate.state` | `blocked` → no `prohibited_actions` |
| `implementation_gate.next_required_capability` | Run this while blocked |
| `implementation_gate.section_checklist_required` | Per-block observe→verify |
| `implementation_gate.ship_council_required` | `perception_design_review(mode="ship")` |
| `coordination_evidence.advancement_eligible` | Only `true` advances structural decisions |
| `data.verified` | Sole verify pass signal (`ok` ≠ pass) |
| `agent_summary.blocking` | Read before `advisory` |
| `ship_gate.council_clear` | Must be true when ship required |
| `spec_revision_gate` | `revision_required` → revise, don’t claim done |

---

## 3. Gates

**Pre-code (`implementation_gate.state=blocked`):** do not invent structural decisions; only inspect, gather evidence, or scaffold/start runtime. Run `next_required_capability`; read `required_resource`.

**Evidence:** degraded / failed / noop / cleanup / connection-only / `ok` without advancement → **cannot** lock direction, hierarchy, or foundation.

**Verify:** `ok=true` + `data.verified=false` = **fail**. Soft text criteria alone never prove chrome/layout.

**Claim-done:** prohibited while section checklist or Ship Council still required — even if page verify passed.

---

## 4. Influence → evidence

| `influence_level` | Behavior |
|-------------------|----------|
| `structural` | Direction / foundation / hierarchy evidence **before** large code volume |
| `balanced` | Evidence on affected surface → implement → verify → ladder if flags set |
| `minimal` / `maintenance` | Observe → fix → verify. No inspiration/redesign. **Exception:** if this episode already drafted design_driven/redesign UI, still finish section checklist + Ship Council |

Obey `stop_conditions` and `defer_until_later`.  
**ROI test before any MCP family:** Will this change a decision not already locked in code? If no → skip.

---

## 5. Situation → minimum evidence

Classify from intent + repo (not keywords). Only evidence that changes an open decision.

| Situation | Resolve | Evidence path | Skip |
|-----------|---------|---------------|------|
| Greenfield / new product UI | Direction, hierarchy, foundation | Strategy → inspiration **or** Figma → seed Spec (≤3–5 refs) → draft from Spec → remeasure/SpecDiff → verify → checklist → ship | Deep SEO, polish tours before first coherent draft |
| Redesign / visual overhaul | Change vs current/target | Snapshot (± bind ref) → SpecDiff/Design Review → code → remeasure → verify → checklist → ship | Inspiration unless direction still open |
| Feature on existing UI | Affected surface only | Bound Spec if any → observe routes → `resolve_*` if owners unclear → implement → verify (+ ladder if gated) | Restarting greenfield inspiration |
| Bug / hotfix / surgical | Symptom + smallest fix | Observe (**blocking** first) → fix → verify → `perception_diff` on fail | Inspiration, checklist, ship (unless user reopens structure) |
| Polish | High-ROI visual only | While strategy ROI allows; SpecDiff on disputed props | Ignoring checklist/ship if a design draft already exists this episode |
| Forms / guards / flows | Playbook criteria | `probe_form` / `probe_guards` / flow checkpoints; still read strategy | Treating new product UI as “just a form” |
| Code ↔ live UI | Owners | `perception_resolve_route` / `perception_resolve_component` | Guessing from repo instead of resolve tools |

---

## 6. Done ladder

**Sources of truth (order):** (1) Engineering Strategy (2) Engineering Spec + SpecDiff (3) live observe/verify/diff. Inspiration / Design Review / Snapshot = evidence, not Spec. Gallery prose ≠ truth.

**Design_driven / redesign / structural / balanced visual:**

1. Gate allows implementation (or maintenance hotfix path)
2. Page verify → **`data.verified=true`**
3. If `section_checklist_required`: each block → observe → look screenshot → `perception_verify(section_id)`
4. If `ship_council_required`: `perception_design_review(mode="ship")` until `ship_gate.council_clear` (revise, or accept with engineering rationale; `ask_user` only for brand/subjective)
5. Bound Spec: remeasure `perception_build_design_snapshot`; honor `spec_revision_gate`
6. Then claim done

**Hotfix/surgical:** steps 2 (+ empty blocking). Skip 3–4 unless structure reopened.

Chrome conventions (sticky/fixed nav permanence, no horizontal overflow) fail inside **verify** on design scopes — not something Ship Council “accepts away.”

---

## 7. Hard constraints

- No claim-done without Done ladder when flags require it
- Blocked gate → zero `prohibited_actions`
- Only `advancement_eligible=true` advances structural decisions
- After `execute_script` / `execute_actions` → verify before claiming progress
- `perception_auth_gate` → `requires_human` → STOP, ask user
- One Chromium per MCP process; restore app origin; don’t leave browser on external galleries
- Never use `perception_code_context` — use `perception_resolve_*`

---

## 8. Never

- Full UI first, MCP only at the end
- Skip health / session_start / strategy on an applicable UI task
- Treat transport `ok` as verify pass
- One page verify = done when checklist or ship is required
- Maximize MCP calls “to be thorough”
- Re-search inspiration after enough refs or a Spec is bound
- Design exploration on hotfix/surgical/debug scopes
- Parallel browser MCP batches on one `session_id`
