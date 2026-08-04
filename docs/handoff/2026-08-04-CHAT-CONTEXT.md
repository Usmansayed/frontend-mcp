# Session handoff — Frontend Perception MCP (FULL chat context)

**Written:** 2026-08-04 (expanded pack)  
**Purpose:** Laptop switch / new chat resume with **product state + detailed conversation memory**.  
**Transcript id:** `c573bbec-56b1-4ce1-9d4f-eba50f9a5c08`  
**Stats:** 820 user messages · **696 unique** queries extracted into companion files.

| File | Role |
|------|------|
| **This file** | Product state, intended loop, code map, backlog, era narrative |
| `2026-08-04-CHAT-QUERY-INDEX.md` | All 696 unique user asks (first-seen order) |
| `2026-08-04-CHAT-RECENT-QUERIES.md` | Last 120 unique asks verbatim |

---

## 0. Open this first on the other laptop

```bash
cd <clone>
git fetch origin
git checkout exp/agent-face-simple
git pull origin exp/agent-face-simple
pip install -e . --upgrade
# Confirm VERSION / package == 1.2.0.dev67
# Reload Cursor MCP (user-frontend-mcp)
```

**Repo:** https://github.com/Usmansayed/frontend-mcp.git  
**Local path (old laptop):** `C:\Users\usman\Projects\frontend-perception-engine`  
**Branch:** `exp/agent-face-simple`  
**Base:** `main`

**Resume prompt for next agent:**

> @ docs/handoff/2026-08-04-CHAT-CONTEXT.md and the QUERY-INDEX / RECENT-QUERIES siblings.  
> We are on `exp/agent-face-simple` at **1.2.0.dev67**.  
> Next: [slim envelopes | maturity flags | live smoke of perception_step | push/PR].  
> Do not re-litigate fidelity/pulse unless broken.

---

## 1. Current product state (authoritative)

### Versions in this arc

| Version | What it did | Status |
|---------|-------------|--------|
| `1.2.0.dev62–dev63` | Phase/packs, observe design packs, prefetch, soft-spot fixes | Earlier in arc |
| `1.2.0.dev64` | Inspiration digest / look_lock (multi-ref + structured borrow) | Shipped earlier |
| `1.2.0.dev65` | Continuous HTTP inspiration pulse | Shipped earlier |
| `1.2.0.dev66` | Chrome fidelity 80–90%, claim-sticky resources/consistency/fidelity, parallel_batch | `0b28b2c` pushed |
| **`1.2.0.dev67`** | **P0s: `perception_step`, hard `implement_blocked`, health `data.doctor`** | **Current head of this handoff** |

### Product thesis (unchanged through the whole chat)

- MCP = **deterministic evidence runtime** (no LLM inside). Host coding agent = brain.
- Face contract = **`agent_summary.card`** (`class`, `evidence_band`, `pack`, `phase`, `implement_blocked`, `next`, `next_args`, `owed`, `claim_ok`, `finish`, `can_parallel`, `parallel_batch`, `inspiration_pulse`, `creative_kit`, …).
- Recurring user pain: with one internet image agents make a pro near-copy; with full MCP they clear verify/`claim_ok` without matching chrome, under-LOOK inspiration, underuse resources/consistency, drown in ceremony/huge envelopes.
- Desired outcome: **~80–90% visual copy** of liked refs + taste tweaks; **forced real use** of component/resources/design/consistency; **fast parallel HTTP** (not serial browser ceremony).

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
- **Pack critical** (greenfield/redesign heavy+): includes component, resources, consistency, fidelity.
- **Parallel HTTP:** `PARALLEL_INTEL_FAMILIES`; card surfaces `can_parallel` + `parallel_batch`.
- **Inspiration pulse:** background HTTP scout; `perception_inspiration_pulse` reads ring; pause after look_lock.

### What `dev67` enforces (experience-report P0s)

1. **`perception_step`** — executes `card.next` + merges `next_args` / overrides. Prefer over inventing nearby tools. Nested step refused. `dry_run` resolves only.
2. **Hard `implement_blocked`** — MCP refuses while blocked:
   - `perception_execute_script`
   - `perception_execute_actions`
   - `perception_integrate_component`
   - `perception_design_review(mode=ship)`
   Short error with `owed_top` + `next` / `next_args`. Observe/verify/inspiration/resources still allowed. (Host IDE file edits cannot be blocked.)
3. **Health doctor** — `perception_health` → `data.doctor`:
   - checks: app_url, browser_use, chromium, node, repo_root, version_skew, browser_manager
   - `fix_commands` copy-paste list
   - `primary_browser: "perception"` (don’t dual-drive Cursor browser / Playwright MCP)

**Tests:** `tests/test_p0_step_block_doctor.py` (11 passed when shipped).  
**Research notes:**  
- `docs/research/2026-07-31-chrome-fidelity-parallel-intel.md`  
- `docs/research/2026-08-04-p0-step-block-doctor.md`  
- Also: pulse / look_lock / parallelism under `docs/research/2026-07-30-*.md`

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

Workspace agent rule: `.cursor/rules/frontend-perception-mcp.mdc`.

---

## 3. Whole-chat narrative (eras)

This panel spans founding (**Jul 8**) through P0 doctor + handoff (**Aug 4**).  
**820** user messages · **696** unique asks. Verbatim wording: QUERY-INDEX + RECENT-QUERIES.

### Activity by day

| Day | User msgs |
|-----|----------:|
| 2026-07-08 | 17 |
| 2026-07-09 | 58 |
| 2026-07-10 | 45 |
| 2026-07-11 | 54 |
| 2026-07-12 | 68 |
| 2026-07-13 | 66 |
| 2026-07-14 | 42 |
| 2026-07-16 | 16 |
| 2026-07-17 | 43 |
| 2026-07-18 | 64 |
| 2026-07-19 | 25 |
| 2026-07-20 | 48 |
| 2026-07-21 | 1 |
| 2026-07-22 | 8 |
| 2026-07-23 | 33 |
| 2026-07-24 | 13 |
| 2026-07-25 | 43 |
| 2026-07-26 | 10 |
| 2026-07-27 | 38 |
| 2026-07-28 | 65 |
| 2026-07-29 | 11 |
| 2026-07-30 | 40 |
| 2026-07-31 | 5 |
| 2026-08-04 | 7 |


### Era story + representative asks

### Jul 8–9 — Founding + test harness app

**Tag:** `E01_founding_harness` · **unique asks:** 67

Started building a **frontend perception engine for coding agents** (Cursor/Claude), not another browser agent. Code Review Graph is a **library**, not a fork. Immediately asked for a complex navigable frontend-only test project (branches, buttons, forms) and to graph + test the tool against it.

**Representative asks:**

- (Wednesday, Jul 8, 2026, 2:11 PM (UTC+5:30)) We are building a frontend perception engine for coding agents (Cursor/Claude), not another browser agent.  Use Code Review Graph as a library, **not as a forked project**.  Repository: https://github.com/tirth8205/code-review-graph  ## Goal  Our architecture is:  Cursor / Claude…
- (Wednesday, Jul 8, 2026, 2:22 PM (UTC+5:30)) now write a simple but complex to navigate proejct frontend only we will use that to test our tool , it should have everthing branched navigation buttons forms ect ect :
- (Wednesday, Jul 8, 2026, 2:33 PM (UTC+5:30)) now graph it and test our tool we built :
- (Wednesday, Jul 8, 2026, 2:39 PM (UTC+5:30)) yes wirte this into our tool :
- (Thursday, Jul 9, 2026, 10:01 PM (UTC+5:30)) now lets log this changes to github so there might be a few git files if there are remove them so we have a clean setup then intialize and push the changes to https://github.com/Usmansayed/frontend-mcp.git
- (Thursday, Jul 9, 2026, 10:54 PM (UTC+5:30)) here is a new thing to add to you all in one mcp also make sure to document this in the documentation : # Framework Intelligence (v1)  The goal of this module is **not** to maintain framework knowledge. Its only responsibility is to detect the project, gather metadata, and provid…
- (Thursday, Jul 9, 2026, 11:02 PM (UTC+5:30)) yes do it have a proper hierarchy  strcuture we have divided you mcp in 7 parts; As we continue building the MCP, structure the codebase around **seven independent intelligence modules**. Each module should own its domain and expose a clean interface to the rest of the system. Sh…
- (Thursday, Jul 9, 2026, 11:47 PM (UTC+5:30)) Please remove the current Context7 integration and refactor the implementation to use a fork of Grounded Docs MCP instead. Keep the fork as close to upstream as possible and place all of our custom logic in an adapter layer so we can easily merge future upstream updates.  Tune th…


### Jul 10–14 — Browser evidence runtime core

**Tag:** `E02_browser_evidence_core` · **unique asks:** 235

Grew the MCP into a deterministic observe/verify/forms/guards runtime. Sessions, navigate_and_observe, probe_form, verify truthfulness (`data.verified`), and agent-facing summaries became the spine. Heavy iteration on making evidence usable by host agents.

**Representative asks:**

- (Friday, Jul 10, 2026, 12:08 AM (UTC+5:30)) so groudned docs mcp working or not did you test it
- (Friday, Jul 10, 2026, 12:14 AM (UTC+5:30)) so how does this work like this search using you framework intellegence : explain
- (Friday, Jul 10, 2026, 12:15 AM (UTC+5:30)) test it on latest udpates on useeffect from react
- (Friday, Jul 10, 2026, 12:16 AM (UTC+5:30)) do it now
- (Tuesday, Jul 14, 2026, 7:49 PM (UTC+5:30)) We found an important UX/runtime bug.  Frontend-mcp should behave like a professional desktop application.  Right now multiple headed Chromium windows are being created during one agent session (I observed three browsers). Some cannot even be closed by the user because the MCP st…
- (Tuesday, Jul 14, 2026, 8:09 PM (UTC+5:30)) commint and push the changes the build and update the frontend in pypi and insatll the update ;
- (Tuesday, Jul 14, 2026, 8:18 PM (UTC+5:30)) did you install it locally :
- (Tuesday, Jul 14, 2026, 8:23 PM (UTC+5:30)) i have restarted curosr try things out ;


### Jul 16–20 — Resolver, design graph, ForOpenCode UX KB

**Tag:** `E03_resolver_design_uxkb` · **unique asks:** 165

Wired code↔UI resolvers (`resolve_route` / `resolve_component` / …), design-graph + consistency tooling, and the **ForOpenCode** UX knowledge corpus (extracts, guides, runtime packs) for principle retrieval — separate from project design-graph standards.

**Representative asks:**

- (Thursday, Jul 16, 2026, 8:16 PM (UTC+5:30)) I think we've identified the next major improvement for Frontend MCP. This is not about adding more tools—it's about improving the quality of the engineering evidence and how the coordinator uses it.  Research first, then implement carefully. Preserve the current architecture whe…
- (Thursday, Jul 16, 2026, 9:07 PM (UTC+5:30)) I think we've identified the biggest reason Frontend MCP doesn't influence the final UI enough.  The problem is NOT the MCP.  The problem is that the host AI doesn't naturally use it throughout the engineering process.  Most coding agents do something like this:  Read prompt ↓  W…
- (Thursday, Jul 16, 2026, 9:09 PM (UTC+5:30)) can we have the rules in one file as it will be easy for the user to setup this :
- (Thursday, Jul 16, 2026, 9:11 PM (UTC+5:30)) first thing should be that if the prompt is related to frontend development or realted then it should evven read the rules ect so please add that too please take your time think of all the scenario and then write the rules file :
- (Monday, Jul 20, 2026, 6:33 PM (UTC+5:30)) is everthing ready to run the process :
- (Monday, Jul 20, 2026, 6:44 PM (UTC+5:30)) i told you we wont be usind embeddings in our mcp you dumb , i meant did you run the search and add priciples opeartions
- (Monday, Jul 20, 2026, 6:46 PM (UTC+5:30)) ok lets start the large operatoin
- (Monday, Jul 20, 2026, 8:09 PM (UTC+5:30)) for the failed scrapes try to do headed slow style scraping where try to not get anit bot flags can also use browser use tool of frontend-mcp using the pipeline + mcp setup , secondly try to get the samem content from a different source if another website is providing the same co…


### Jul 22–25 — Inspiration gallery + creative resources

**Tag:** `E04_inspiration_resources` · **unique asks:** 85

Added inspiration gallery flows and creative resource search (fonts/icons/photos/patterns). Focus: agents should LOOK many refs and actually apply assets — not soft-mood text.

**Representative asks:**

- (Tuesday, Jul 21, 2026, 8:47 PM (UTC+5:30)) yes lets move on
- (Wednesday, Jul 22, 2026, 9:19 PM (UTC+5:30)) so is everthing ready to be built into a mcp :
- (Wednesday, Jul 22, 2026, 9:23 PM (UTC+5:30)) ok do it but before that shouldnt you think that we should include this into the design intellegence :
- (Wednesday, Jul 22, 2026, 10:09 PM (UTC+5:30)) ok lets build it now wirte UX kn in design sense : like the way you recommended
- (Saturday, Jul 25, 2026, 5:46 PM (UTC)) see this is not easy to implement instead of using static things we should let the agent see the problem and decide how much efforts to but but we need to give me some help on how do decide what to do and how much to do ect keep it simple ai centric :
- (Saturday, Jul 25, 2026, 11:21 PM (UTC+5:30)) ok lets implement this too : and test it improvise if needed ;
- (Saturday, Jul 25, 2026, 11:36 PM (UTC+5:30)) run tests on it :
- (Saturday, Jul 25, 2026, 11:43 PM (UTC+5:30)) so should we publish the package :


### Jul 27–29 — Coordination face / card / hang fixes

**Tag:** `E05_coordination_face` · **unique asks:** 98

Built/hardened the **coordination face**: `agent_summary.card`, packs, phases, unpaid evidence, claim gates. Multiple hangs / slow executes blamed on coordination vs inspiration layers — you demanded fix coordination properly, then component-level tests, then full readiness (MCP + docs + rules + coordination).

**Representative asks:**

- (Sunday, Jul 26, 2026, 12:17 AM (UTC+5:30)) i want to like build a landing page for your frontend-mcp and the design is there but you only have to descibe what content should we have where , like we should have a landinage page some page about how to install it , the pip install frontend-mcp should be on the hero section r…
- (Sunday, Jul 26, 2026, 12:22 AM (UTC+5:30)) i just want you to write the md file instructing the ai agent what we are building what pages should we have what content it should have you dont need to use the mcp you will write the mcp realted inforation the other agent will design the website you just tell very basic thigns …
- (Sunday, Jul 26, 2026, 12:26 AM (UTC+5:30)) we can add more information like how things are so amazingly working ect like we need to showcase the intellegene working ect on specific pages on on teh landing one obviously so make it long in detial take your time :
- (Sunday, Jul 26, 2026, 12:32 AM (UTC+5:30)) we can still add a lot of information to it we are missing a lot of information secondly also provide the starter promt ;
- (Wednesday, Jul 29, 2026, 10:56 PM (UTC+5:30)) i want to increase how much the agent uses the mcp for every kind of class , and want to ship most things like integrated , becuase in one call it uses the preception engine in one call it uses the component intellgence , in one call is uses the design intellegnece but not all , …
- (Wednesday, Jul 29, 2026, 11:17 PM (UTC+5:30)) other then very deterministic quries like do this do that we will mostly be using the frontend-mcp heavily its more about medium use , heavy use and very heavy use not low use i think you get it second is integrating the service like , using ht e, component , consisstnecy , prece…
- (Wednesday, Jul 29, 2026, 11:34 PM (UTC+5:30)) ok lets research and plan it  :
- (Wednesday, Jul 29, 2026, 11:38 PM (UTC+5:30)) Evidence Pack Loop (use-band + integrated services)  Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.  To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting wi…


### Jul 30–31 — Live redesign grades + pulse/look_lock/fidelity (→dev66)

**Tag:** `E06_live_redesign_pulse_fidelity` · **unique asks:** 41

Live GPT-Clone-style redesign sessions graded ~B−: strong evidence, weak taste/chrome match, fat envelopes, sticky ceremony. Demanded **~80–90% visual copy**, forced use of component/resources/design/consistency, and **parallel HTTP** — shipped as look_lock, inspiration pulse, then **dev66** chrome fidelity + claim-sticky families + `can_parallel` / `parallel_batch`.

**Representative asks:**

- (Thursday, Jul 30, 2026, 12:09 AM (UTC+5:30)) we need to update andn install this for testing
- (Thursday, Jul 30, 2026, 12:13 AM (UTC+5:30)) realoaded :
- (Thursday, Jul 30, 2026, 11:37 AM (UTC+5:30)) i have reloaded the mcp check it out man :
- (Thursday, Jul 30, 2026, 11:51 AM (UTC+5:30)) lets test like the coordination layer docs part and see , like create a few test maybe 50 diff scnenario with ans and later we will test the coordination layer withit like is it doing what we want or no and if its making the same problem in patter we can fix it :
- (Friday, Jul 31, 2026, 1:03 AM (UTC+5:30)) heres a feedback see i dont understand when i get a image for my coding agent from the internet and tell him to build it ocmpletely builds a full proffesional copy but here with everthing also why are we not able to achive that , like why the fuck doesnt it ask question like lets…
- (Friday, Jul 31, 2026, 1:11 AM (UTC+5:30)) we need them to use more visuals and like try to replicate like 80-90% of it with some addional taste from other or like take pattersns from those searches or visuals and build things more like copy paste we need to do this and force the agent to not just call but use component ,…
- (Friday, Jul 31, 2026, 4:16 PM (UTC+5:30)) can yo give an extimate on a project like this how many loc do we have or maybe how many tokens , i want this no to test emebdding dotn use llm to do this shit instead you know use somepython code or something to give an approx :
- (Friday, Jul 31, 2026, 10:19 PM (UTC+5:30)) push the updates of this to github


### Aug 4 — Experience-report P0s (dev67) + laptop handoff

**Tag:** `E07_p0_doctor_handoff` · **unique asks:** 5

Agent experience report P0s implemented as **dev67**: `perception_step`, hard `implement_blocked` on mutation tools, health `data.doctor`. Asked for laptop-switch handoff with **full chat detail** (this pack).

**Representative asks:**

- (Tuesday, Aug 4, 2026, 2:02 AM (UTC+5:30)) c:\Users\usman\Downloads\frontend-mcp-experience-report.md so i worked on a project with the frontend-mcp and here is the feedback :
- (Tuesday, Aug 4, 2026, 2:09 AM (UTC+5:30)) ok so IT AND TEST IT :
- (Tuesday, Aug 4, 2026, 2:38 AM (UTC+5:30)) ok so i want you to write a summary of the chat we had int this pannel with more weight on the cuurent state so i can like switch to another laptop and remeber all the things :
- (Tuesday, Aug 4, 2026, 2:45 AM (UTC+5:30)) Okay, so basically, I'm gonna switch to another laptop, so you have to make sure that you, whatever chats we had, right, you have to transfer it into one file so that when I open in another laptop, right, we have all the context there, what we worked on and everything.
- (Tuesday, Aug 4, 2026, 2:49 AM (UTC+5:30)) i want it to be indetail like our whole chat context :



### Core problem restated in your words (recurring)

- One internet image + “build this” → coding agent makes a **pro near-copy**.
- Full MCP ladder → agents **call** inspiration/components/resources/verify, clear `claim_ok`, but **sidebar/header stay old**; LOOK only 1–2 of many refs; soft mood instead of chrome copy.
- MCP is excellent at preventing fake “done”; weaker as a **tasteful art director**. No LLM in MCP = it cannot invent “navbar looks old vs refs” unless the host files that in VF.

### Live redesign feedback (GPT Clone session, ~Jul 30–31)

- Used many intel families; verify rigorous; grade ~**B−** (outcome A−, process C+).
- Pros: evidence gates, section crops, assets when used.
- Cons: huge envelopes, sticky ceremony (initiative/very_heavy for polish), inspiration session drift, serial verifies, consistency = token math not taste.
- Ask that followed: **force 80–90% visual copy + force use of component/resources/design/consistency, fast/not serial** → `dev66`.

### Agent experience report (Aug 4)

File on old machine: `c:\Users\usman\Downloads\frontend-mcp-experience-report.md`

Praised: deterministic MCP, card OS, observe→resolve→verify, claim discipline, parallel HTTP model.  
Hurt: tool sprawl, soft ceremony, fat envelopes, env footguns, scaffold looking like GA.  
Their P0s we implemented as **`dev67`:** Tier-0/`perception_step`, hard implement_blocked, health doctor.

### Size of codebase (approx, local Python count — no LLM)

- `src/**/*.py`: ~**81k LOC**, ~**662k** tiktoken cl100k tokens  
- Product Python (`src+tests+scripts+evals`): ~**1.06M** tokens  
- Full-repo multi-million line counts = artifacts/venvs/junk — ignore for “product size”

### Git note from this panel

- Pushed: `0b28b2c` (`dev66`) on `exp/agent-face-simple`.
- `dev67` + this expanded handoff should be on the same branch after push.
- Do **not** casually commit: `ForOpenCode/`, logs, marketing drafts, shortcuts, `evals/results/`, `dist_locked_old/`, `.cache/`, etc.

---

## 4. Explicitly NOT done yet (next backlog)

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

Paste or `@` this file **plus** the query index if they need wording fidelity, and say:

> Resume from `docs/handoff/2026-08-04-CHAT-CONTEXT.md`. On `exp/agent-face-simple` at `1.2.0.dev67`. Next: [slim envelopes | maturity flags | push/PR | live test perception_step]. Do not re-litigate the fidelity/pulse design unless broken.

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

Local transcript (this machine only):  
`C:\Users\usman\.cursor\projects\c-Users-usman-Projects-frontend-perception-engine\agent-transcripts\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08.jsonl`

---

## 7. One-line memory

**Card-driven frontend agent OS:** evidence before claim, ~80–90% visual copy via fidelity + sticky resource/consistency, parallel HTTP intel, and as of **dev67** a **step tool + hard mutation block + health doctor** — next win is thinner envelopes and less tool sprawl, not more features.
