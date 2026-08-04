# 02 — Failure Modes (with evidence)

## F1 — Tunnel on singular next

**Behavior:** Agent calls only `implementation_gate.next_required_capability` or `recommended_evidence`, ignores other unpaid families.

**Evidence:**
- EXP-025 design: agents ignore portfolio while Perfect Layer already exposes unpaid  
- EXP-026: Arm A (singular top/next) → **2/48**; Hard pack → **0/24**  
- Portfolio note in code already warns: *“Do not tunnel on one family”* (`episode_portfolio.py`)  
- PrimeStay / flow-craft feedback (external): Design snapshot schema fetched but not executed; mockup matched via taste + soft verify  

**Guide requirement:** Owed plan ≤3 from unpaid ∩ class; `gate.next` only if inside plan.

---

## F2 — Skip design reference (inspiration AND snapshot)

**Behavior:** Large UI code before paying inspiration **or** snapshot/figma while `design_reference` unpaid.

**Evidence:**
- Portfolio sets both inspiration and snapshot unpaid for `design_reference` (`episode_portfolio.py`)  
- Snapshot **can supersede** inspiration once paid  
- Greenfield methodology requires usable reference + foundation  

**Guide requirement:** Explicit “pay reference family before locking hierarchy”; allow insp **or** snap **or** figma.

---

## F3 — Mockup path wrong (inspiration instead of snapshot)

**Behavior:** User uploads mockup / reference image; agent runs gallery inspiration or only observe/verify.

**Evidence:**
- Redesign workflow: snapshot + SpecDiff, not gallery-first  
- EXP-026 H01/H07/H12/H24: inspiration bait while snapshot unpaid  
- Flow-craft Prompt 3: mockup match without `build_design_snapshot`  

**Guide requirement:** Mockup/redesign → snapshot first; inspiration only if direction still open.

---

## F4 — Soft false-green verify

**Behavior:** `data.verified=true` on text/structure criteria; visual claim (opacity, wash, hierarchy) unchanged.

**Evidence:**
- Flow-craft opacity: image opacity changed, overlay wash dominated; user saw no change  
- Rule §3: soft text never proves chrome/layout  
- Verification guide: chrome conventions on design scopes  

**Guide requirement:** Visual claims → JS/computed-style criteria; measure competing layers (overlays).

---

## F5 — Claim-done before Done ladder

**Behavior:** Page verify pass treated as done while sections or ship unpaid.

**Evidence:**
- Rule §6 Done ladder  
- Portfolio unpaid `sections` / `design_review` when flags set  
- Gate prohibits `claim_complete`  

**Guide requirement:** Checklist → ship → then claim; never equate page verify with done when flags set.

---

## F6 — Hotfix/polish reopens structural gates

**Behavior:** Micro CSS tweak; agent blocked on foundation / inspiration.

**Evidence:**
- Flow-craft Prompt 7 feedback: foundation gate sticky on polish  
- Situation policy: surgical keywords → `surgical` scope  
- EXP-026 H02/H09/H18  

**Guide requirement:** Hotfix/polish → observe → fix → hard verify; skip foundation/insp/ship unless sticky design episode reopened structure.

---

## F7 — Thoroughness spam / SEO bait

**Behavior:** Call SEO or every family “to be thorough.”

**Evidence:**
- Portfolio `deferred: seo` by default  
- Rule §8 never maximize calls  
- EXP-026 H06/H15/H23  

**Guide requirement:** ROI test; SEO only if user asks or decision open.

---

## F8 — Wrong app / wrong port

**Behavior:** Health reachable on wrong product; verify wrong UI.

**Evidence:**
- Flow-craft: `:5173` Maze vs `:5174` app  
- Health = HTTP reachability, not brand fingerprint (known gap)  

**Guide requirement:** Observe screenshot must match user product before structural claims; prefer user-stated port.

---

## F9 — Skip resolve_* for owners

**Behavior:** Grep/Read instead of `perception_resolve_*` when ownership unpaid/unclear.

**Evidence:**
- Rule §7 never `perception_code_context`  
- Bugfix/feature paths call for resolve when unclear  
- Flow-craft feedback: resolver underused  

**Guide requirement:** Feature/hotfix with unclear owners → resolve before large edits.

---

## F10 — Ritual inspiration loops

**Behavior:** Re-run discover/collect 2–3 times after usable refs or Spec bound.

**Evidence:**
- Rule §2b / §8  
- Inspiration guide: progressive collect 3–5 refs, stop when usable  

**Guide requirement:** One progressive collect; stop at 3–5 usable; skip after Spec/mockup bound.

---

## F11 — Envelope archaeology

**Behavior:** Huge envelopes → agent shells out to extract gate; may skip tools that feel heavy.

**Evidence:**
- Flow-craft feedback: inspiration/coordinator payloads huge  
- Perfect Layer: slim `episode_card` / coordinator card intended to fix this  

**Guide requirement:** Teach “read episode_card first” (unpaid+gate+top); ignore catalog noise.

---

## F12 — End-of-task MCP only

**Behavior:** Code full UI from taste; MCP only at the end as QA.

**Evidence:** Rule §0–§1; getting-started production rule; AGENT_GUIDE false-green warning.

**Guide requirement:** Bootstrap before substantial UI; “end-of-task MCP” = process fail.

---

## F13 — Parallel browser tools on one session

**Behavior:** Batch multiple browser MCP calls; hangs / confused state.

**Evidence:** `evals/V1.1.5_AGENT_EVALUATION.md`; rule §1/§8.

**Guide requirement:** One browser tool at a time per `session_id`.

---

## Priority for new guides

| Priority | Failures |
|----------|----------|
| P0 | F1 tunnel, F2 skip reference, F3 mockup, F4 false-green, F5 claim-done |
| P1 | F6 polish reopen, F7 spam, F8 wrong app, F12 end-of-task |
| P2 | F9 resolve, F10 ritual insp, F11 envelope noise, F13 parallel |
