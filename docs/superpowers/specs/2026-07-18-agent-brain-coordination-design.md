# Agent-Brain Coordination — Design (EXP-025)

**Date:** 2026-07-18  
**Status:** Experiment complete — **B wins**; freeze agent-brain contract  

**Stance:** Do **not** add more MCP gates / owed enforcers. Keep coordination as a **clean facts layer**. Put judgment in the **agent (LLM)**.

---

## 1. Problem

After Perfect Layer A–C, MCP already returns:

- gate, backlog.top, portfolio paid/unpaid, confidence, host_action, episode_card

Real agents still tunnel: they obey **one** `next_required_capability` / `recommended_evidence` and ignore unpaid families. Feedback sessions used only Design (or only Observe/Verify) when Inspiration + Component were also needed.

Adding more machinery (owed gates, multi-round inspiration mandates, supersede bars) increases complexity. Hypothesis: **better agent behavior beats more coordination code.**

---

## 2. Division of labor (frozen)

| Layer | Owns | Must not own |
|-------|------|----------------|
| **MCP Coordination** | Deterministic facts: gate, portfolio, backlog, confidence, cards, verify/ship signals | Multi-step “when to call which family” judgment |
| **Agent (LLM)** | Decide which unpaid families to pay, when enough evidence exists, when to skip with a reason | Inventing structural facts without `advancement_eligible` |

**MCP speaks. Agent decides. Agent must read the whole scoreboard — not only the next pitch.**

---

## 3. How we want coordination to work

### 3.1 Scoreboard (MCP — keep simple)

Every structural/balanced episode, agent reads from `episode_card` / strategy:

1. `host_action` — prose intent  
2. `gate` — hard stops (`blocked`, `claim_complete`, sections, ship)  
3. `portfolio.unpaid` — families still owed for honesty  
4. `backlog.top` — best single ROI next (hint, not tunnel)  
5. `confidence` — process completeness readout (not a gate)

Do **not** expand this set without a new experiment.

### 3.2 Brain loop (Agent — new contract)

```text
STRATEGIZE
  Read card: unpaid + gate + top
  Classify task: greenfield | redesign | feature | hotfix | polish
  Build a short owed plan (≤3 families) from unpaid ∩ task class
  Pick ONE next call from owed plan (prefer backlog.top if it is in owed)

EVIDENCE
  Pay that family until advancement_eligible or valid skip
  Re-read unpaid — do not lock UI while structural unpaid remain
  Inspiration (when owed): one progressive collect aiming 3–5 image refs
    — not ritual “run 2–3 times”; stop when usable or skip with reason

ACT
  Implement only decisions supported by paid evidence

VERIFY / LADDER
  data.verified=true → sections if required → ship if required → claim
```

### 3.3 Task → minimum families (agent judgment)

| Task class | Usually owe | Usually skip |
|------------|-------------|--------------|
| Greenfield / new landing | inspiration **or** snapshot, component foundation, observe, verify (+ ship if design_driven) | SEO, deep consistency tours |
| Redesign / mockup match | snapshot (+ SpecDiff), observe, verify, ship; inspiration only if direction still open | Re-running inspiration after Spec bound |
| Feature on existing UI | observe affected routes, resolve_* if owners unclear, verify | Greenfield inspiration |
| Hotfix / polish CSS | observe → fix → verify | Inspiration, foundation, ship (unless structure reopened) |

### 3.4 Anti-patterns (agent)

- Obey only `gate.next` while `portfolio.unpaid` still lists other structural families  
- Soft text verify as “done” for redesign  
- Jump to Design Review / Spec without paying inspiration **or** snapshot when `design_reference` is unpaid  
- Call every MCP family “to be thorough”

---

## 4. Experiment (EXP-025)

**A (control):** Current agent rule — singular next fields dominate.  
**B (treatment):** Agent-brain contract below — portfolio.unpaid binds; MCP unchanged.

**Eval:** Same redesign prompt (e.g. landing / mockup). Score:

| Metric | Pass |
|--------|------|
| Families paid when owed (insp **or** snap, component if foundation open, observe, verify) | ≥ owed set |
| Tunnel score (tools from only 1 family while unpaid ≥2) | Fail if true |
| Soft false-green (opacity/overlay class) | Fail if user-visible unchanged after claim |
| MCP complexity delta | **0** new gates in B |

---

## 5. Non-goals

- New claim gates for unpaid portfolio  
- Forcing N inspiration rounds  
- Parallel “AI coordinator” runtime inside MCP  
- Growing coordinator_card schema beyond a short `owed` hint (optional later; not required for B)

---

## 6. Success

If B reduces tunnel and false-green **without** new coordination code → freeze agent-brain contract; pause Perfect Layer feature growth.  
If B fails → then consider minimal owed hint on card (not new gates).
