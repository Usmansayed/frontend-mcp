# Session handoff — Frontend Perception MCP (laptop switch)

**Written:** 2026-08-04  
**Purpose:** Single context file so a new chat / other laptop can resume without the old Cursor panel.  
**Weight:** Current product state first; chat history second.

---

## 0. Open this first on the other laptop

```bash
cd <clone>
git fetch origin
git checkout exp/agent-face-simple
git pull origin exp/agent-face-simple
pip install -e . --upgrade
# Confirm VERSION file / package == 1.2.0.dev67
# Reload Cursor MCP (user-frontend-mcp)
```

**Repo:** https://github.com/Usmansayed/frontend-mcp.git  
**Local path (old laptop):** `C:\Users\usman\Projects\frontend-perception-engine`  
**Branch:** `exp/agent-face-simple`  
**Base:** `main`

**Read this file:** `docs/handoff/2026-08-04-CHAT-CONTEXT.md` (this document).

---

## 1. Current product state (authoritative)

### Versions in this arc

| Version | What it did | Status |
|---------|-------------|--------|
| `1.2.0.dev62–dev63` | Phase/packs, observe design packs, prefetch, soft-spot fixes | Earlier in arc |
| `1.2.0.dev64` | Inspiration digest / look_lock (multi-ref + structured borrow) | Shipped earlier |
| `1.2.0.dev65` | Continuous HTTP inspiration pulse | Shipped earlier |
| `1.2.0.dev66` | Chrome fidelity 80–90%, claim-sticky resources/consistency/fidelity, parallel_batch | Committed+pushed as `0b28b2c` |
| **`1.2.0.dev67`** | **P0s: `perception_step`, hard implement_blocked, health doctor** | **Must be on branch after this handoff commit** |

### Product thesis (unchanged)

- MCP = **deterministic evidence runtime** (no LLM inside). Host agent = brain.
- Face contract = **`agent_summary.card`** (`class`, `evidence_band`, `pack`, `phase`, `implement_blocked`, `next`, `next_args`, `owed`, `claim_ok`, `finish`, `can_parallel`, `parallel_batch`, `inspiration_pulse`, `creative_kit`, …).
- Goal of this arc: agents should **LOOK many visuals and ~80–90% copy** liked chrome (with taste tweaks), and **actually use** component / resources / design / consistency intel — **fast via parallel HTTP**, not serial ceremony. Soft “verify green” without chrome match is a fail.

### Intended host loop (current)

```
perception_health({url, intent})
  → read data.doctor.fix_commands if critical fails
→ perception_session_start({base_url, intent})
→ loop: perception_step({session_id})   # Tier-0 = run card.next
  → when card.can_parallel / parallel_batch: fire HTTP intel concurrently
     creative_assets ∥ select_component_foundation ∥ inspiration_pulse ∥
     design_graph_refresh / consistency_audit
  → browser tools stay ONE at a time (flight lock / queue)
→ VF purpose=inspiration: LOOK many blobs; primary_ref_ids + borrow[{ref_id,section,idea}]
→ implement chrome as near-copy + apply assets
→ VF purpose=design + chrome_fidelity[{zone:nav|aside|main|composer, fidelity, ref_id}]
→ consistency → verify (sections if required) → claim only if claim_ok
```

**Hotfix / forms:** lean path — no inspiration/fidelity ladder.

### What `dev66` enforces

- **Chrome fidelity:** zones `nav|aside|main|composer` (aliases header/sidebar/thread/…); mean ≥80; each ≥75; bind `ref_id`. Soft judgment=ok without zones → next_action attest; family `fidelity` unpaid.
- **Claim-sticky after verify:** `inspiration_extract`, `resources`, `consistency`, `fidelity` still block `claim_ok` if unpaid.
- **Pack critical** (greenfield/redesign heavy+): includes component, resources, consistency, fidelity (resources not optional-only).
- **Parallel HTTP:** `PARALLEL_INTEL_FAMILIES`; card surfaces `can_parallel` + `parallel_batch`.
- **Inspiration pulse:** background HTTP scout; `perception_inspiration_pulse` reads ring; pause after look_lock.

### What `dev67` enforces (experience-report P0s)

1. **`perception_step`** — executes `card.next` + merges `next_args` / overrides. Prefer over inventing nearby tools. Nested step refused. `dry_run` resolves only.
2. **Hard `implement_blocked`** — MCP refuses while blocked:
   - `perception_execute_script`
   - `perception_execute_actions`
   - `perception_integrate_component`
   - `perception_design_review(mode=ship)`
   Short error with `owed_top` + `next` / `next_args` (not an essay). Observe/verify/inspiration/resources still allowed. (Host IDE file edits cannot be blocked.)
3. **Health doctor** — `perception_health` → `data.doctor`:
   - checks: app_url, browser_use, chromium, node, repo_root, version_skew, browser_manager
   - `fix_commands` copy-paste list
   - `primary_browser: "perception"` (don’t dual-drive Cursor browser / Playwright MCP)

**Tests:** `tests/test_p0_step_block_doctor.py` (11 passed when shipped).  
**Research notes:**  
- `docs/research/2026-07-31-chrome-fidelity-parallel-intel.md`  
- `docs/research/2026-08-04-p0-step-block-doctor.md`  
- Also: pulse / look_lock / parallelism docs under `docs/research/2026-07-30-*.md`

---

## 2. Key code map (resume coding here)

| Concern | Path under `src/navigation/` |
|---------|------------------------------|
| Face card / claim_ok / finish | `coordination_intelligence/planning/coordinator_card.py` |
| Evidence packs / sticky / parallel families | `coordination_intelligence/planning/evidence_pack.py` |
| Chrome fidelity eval | `coordination_intelligence/planning/chrome_fidelity.py` |
| Inspiration look_lock | `coordination_intelligence/planning/inspiration_look_lock.py` |
| Inspiration pulse loop | `coordination_intelligence/planning/inspiration_pulse_loop.py` |
| Portfolio unpaid (resources/consistency/fidelity) | `coordination_intelligence/planning/episode_portfolio.py` |
| VF purpose schemas / fidelity next_actions | `visual_browser_intelligence/visual/visual_feedback_policy.py` |
| Hard implement gate | `execution_runtime/policies/implement_hard_gate.py` |
| Step resolver | `execution_runtime/policies/perception_step.py` |
| Executor hooks (gate + step) | `execution_runtime/executor.py` |
| Browser flight lock | `execution_runtime/policies/browser_flight.py` |
| Health doctor | `mcp/health_doctor.py` |
| Health handler | `mcp/handlers.py` (`handle_health`, `handle_step`) |
| Tool schemas | `mcp/tools.py` |
| Agent instructions | `mcp/instructions.py` |
| VERSION | repo `VERSION` + `pyproject.toml` |

Workspace agent rule (Cursor): `.cursor/rules/frontend-perception-mcp.mdc` — scoreboard loop for UI tasks.

---

## 3. Chat history (compressed — why we did the above)

### Problem you kept hitting
- One internet image + “build this” → coding agent makes a **pro near-copy**.
- Full MCP ladder → agents **call** inspiration/components/resources/verify, clear `claim_ok`, but **sidebar/header stay old**; LOOK only 1–2 of many refs; soft mood instead of chrome copy.
- MCP is excellent at preventing fake “done”; weaker as a **tasteful art director**. No LLM in MCP = it cannot invent “navbar looks old vs refs” unless the host files that in VF.

### Live redesign feedback (GPT Clone session, Jul 30–31)
- Used many intel families; verify rigorous; grade ~**B−** (outcome A−, process C+).
- Pros: evidence gates, section crops, assets when used.
- Cons: huge envelopes, sticky ceremony (initiative/very_heavy for polish), inspiration session drift, serial verifies, consistency = token math not taste.
- Ask that followed: **force 80–90% visual copy + force use of component/resources/design/consistency, fast/not serial** → `dev66`.

### Agent experience report (Aug 4)
File on old machine: `c:\Users\usman\Downloads\frontend-mcp-experience-report.md`  
(You can copy it into the repo if needed; not required for resume.)

Praised: deterministic MCP, card OS, observe→resolve→verify, claim discipline, parallel HTTP model.  
Hurt: tool sprawl, soft ceremony, fat envelopes, env footguns, scaffold looking like GA.  
Their P0s we implemented as **`dev67`:** Tier-0/`perception_step`, hard implement_blocked, health doctor.

### Size of codebase (approx, local Python count — no LLM)
- `src/**/*.py`: ~**81k LOC**, ~**662k** tiktoken cl100k tokens  
- Product Python (`src+tests+scripts+evals`): ~**1.06M** tokens  
- Full-repo multi-million line counts = artifacts/venvs/junk — ignore for “product size”

### Git note from this panel
- Pushed earlier: `0b28b2c` on `exp/agent-face-simple` (`dev66`).
- Left untracked on purpose (do **not** commit unless asked): `ForOpenCode/`, logs, marketing drafts, shortcuts, `evals/results/`, etc.
- Second “commit-and-push” action found **nothing new** at that moment (already synced); `dev67` was built after that.

---

## 4. Explicitly NOT done yet (next backlog)

From the experience report / your notes — still open:

| Priority | Item |
|----------|------|
| P1 | Slim envelopes: `card` always; large `data` on demand (`scan_get`-style) |
| P1 | Tool `maturity: ga \| beta \| scaffold` on schema + card; prefetch only GA/beta |
| P1 | Resolver eval CI (route→file, component→file) |
| P2 | Stronger Tier-0 surface (hide experimental SEO/Figma until connected) |
| P2 | Parallel batch *executor* tool (not just `can_parallel` hints) |
| P2 | Exclude `references/` / `research/` from default resolve/index |
| Soft | Right-size polish defaults (initiative/very_heavy too sticky for CSS tweaks) |
| Soft | Inspiration session ID drift (`inspiration_session_not_found`) reliability |

**Do not** add another intelligence module before thinning degrees of freedom.

---

## 5. How to talk to the next agent

Paste or `@` this file and say something like:

> Resume from `docs/handoff/2026-08-04-CHAT-CONTEXT.md`. We are on `exp/agent-face-simple` at `1.2.0.dev67`. Next: [slim envelopes | maturity flags | push/PR | live test perception_step]. Do not re-litigate the fidelity/pulse design unless broken.

### Smoke after MCP reload

1. `perception_health({url, intent})` → confirm `data.doctor` present.  
2. `perception_session_start({base_url, intent})` → read `agent_summary.card`.  
3. `perception_step({session_id})` → should run `card.next`.  
4. On greenfield/redesign with `implement_blocked=true`, try `perception_execute_script` → must get `implement_blocked` refuse with `owed_top`.

---

## 6. Related docs already in repo

- `docs/research/2026-07-30-continuous-inspiration-pulse.md`  
- `docs/research/2026-07-30-inspiration-digest-enforcement.md`  
- `docs/research/2026-07-30-mcp-parallelism-architecture.md`  
- `docs/research/2026-07-31-chrome-fidelity-parallel-intel.md`  
- `docs/research/2026-08-04-p0-step-block-doctor.md`  
- `docs/AGENT_FACE_COORDINATION.md`  

---

## 7. One-line memory

**Card-driven frontend agent OS:** evidence before claim, ~80–90% visual copy via fidelity + sticky resource/consistency, parallel HTTP intel, and as of **dev67** a **step tool + hard mutation block + health doctor** — next win is thinner envelopes and less tool sprawl, not more features.
