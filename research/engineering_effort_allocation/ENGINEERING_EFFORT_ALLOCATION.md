# Engineering Effort Allocation for Frontend Perception MCP

**Status:** Research only — **not approved for implementation**  
**Date:** 2026-07-14  
**Extends:** Design-driven workflow proposal (session research); Coordination Intelligence Report 07; runtime artifacts R0–R11  
**Audience:** Product + architecture review before any code

---

## Executive summary

The prior proposal answered: **when** should the coordinator intervene for design-driven work?

This document answers a harder twin question: **how much intelligence should we spend** on the next decision?

A senior frontend tech lead does not allocate equal effort to layout and to 1px padding. They maximize **quality per unit cost**, respect **diminishing returns**, and push **judgment** to the strongest reasoning substrate available — today, the **host frontier LLM**.

**One-line model:**

```text
Intelligence Budget  ×  Visual Leverage  ×  Expected Quality Gain
───────────────────────────────────────────────────────────────────  →  Recommend next step OR STOP
                    Cost (latency · side effects · token load)
```

**Frozen constraints (do not violate):**

1. Host LLM = sole reasoner (design briefs, tradeoffs, implementation).
2. MCP = deterministic evidence + validation + advisory recommendations.
3. Coordinator remains advisory — never mandatory; never maximize tool calls.
4. No new major architecture; extend PSM / heuristics / briefing / playbook composition.

---

## 1. Problem framing

### 1.1 Two orthogonal questions

| Question | Failure mode if ignored |
|----------|-------------------------|
| **When to intervene?** (scope / playbook) | Surgical tasks get expensive inspiration loops |
| **How much to spend?** (effort allocation) | Even correct playbooks overspend — 4th design review on a button |

Intervention without budgeting creates **coordination theater**: many MCP calls, little UI improvement.

### 1.2 Objective function (what we maximize)

```text
maximize:  ΔPerceived_UI_Quality  +  ΔEngineering_Correctness  −  λ · Cost
subject to:
  - Host remains reasoner
  - Episode Intelligence Budget not exceeded without justification
  - Advisory only (host may skip)
  - Prefer reuse of existing evidence over new collection
```

“Perceived UI Quality” is user/agent-facing: hierarchy, clarity, correctness, trust.  
“Engineering Correctness” is verify/blocking empty, routes/components resolved, licenses ok.  
Cost = wall latency + chrome/process load + response payload size + opportunity cost of delaying implementation.

### 1.3 Related work (outside MCP)

| Domain | Insight we borrow |
|--------|-------------------|
| **Law of diminishing returns** (econ → SE) | Later optimisations yield smaller marginal gains; know when to stop |
| **Engineering ROI triangulation** | Prefer more than one rough method; when methods disagree, surfaces load-bearing assumptions |
| **Pareto / leverage** | A minority of decisions drive most outcomes (layout ≫ padding) |
| **Human decision making under uncertainty** | Invest in information only when EV(info) > cost (value of information) |
| **Agent orchestration** | Separate planner (budgeted) from actor; use tools for evidence, LLM for synthesis |
| **Design critique practice** | Early critiques change structure; late critiques change polish — different budgets |
| **Report 07 (this repo)** | Coordinator is *intelligence for the brain*, not a replacement brain |

---

## 2. Host LLM vs MCP responsibility boundaries

### 2.1 Amplify, don’t compete

The host agent (Cursor / Claude / GPT) is the highest-capability reasoning engine in the system. The MCP must **never** duplicate frontier-model reasoning.

**Continuous MCP question:**

> “What deterministic frontend evidence can I provide that lets the host LLM make a *much better* decision?”

If the answer is “none that’s cheaper than the host guessing from code already in context,” **do not call an expensive module**.

### 2.2 Responsibility matrix

| Responsibility | Owner | MCP role |
|----------------|-------|----------|
| Intent interpretation | Host | Optional intent strings into episode |
| Design brief / mood narrative | Host | Provide inspiration URLs, screenshots, PDG summary as inputs |
| Layout & hierarchy decisions | Host | Inspiration, snapshots, visual_insights, screenshots |
| Implementation strategy & code | Host | Resolve route/component; dry-run integrate plans |
| Tradeoffs (speed vs polish) | Host | Expose costs + ROI in briefing |
| Browser truth | MCP | Observe, screenshots, console/network |
| Inspiration / resources (fetch) | MCP | Deterministic providers + licenses |
| Component foundations (search) | MCP | Registries + consults → candidates |
| Design snapshot / review metrics | MCP | Measured facts + ranked findings (not “pick a layout”) |
| Consistency metrics | MCP | Graph drift / standards |
| Verification / validation | MCP | Criteria pass/fail |
| Effort allocation / STOP | Coordinator (advisory) | Budget + ROI gates |

### 2.3 Anti-patterns (LLM duplication)

| Anti-pattern | Why wrong |
|--------------|-----------|
| MCP LLM that writes design briefs | Competes with host; latency + cost + architectural betrayal |
| Coordinator mandatory multi-step “think” loops | Host already reasons between tool calls |
| Re-summarizing the same screenshot five times | Zero new evidence |
| Suggesting design review to “decide aesthetics” without metrics | Host aesthetics ≫ MCP heuristics for taste |

### 2.4 Amplification pattern (preferred)

```text
MCP: gather_evidence(E)           # cheap / high leverage
Host: reason(E) → decision(D)     # frontier model
Host: implement(D)                # code
MCP: verify / observe → E'        # truth
Coordinator: ROI(E'|budget) → next evidence OR STOP
```

See also: [`diagrams/host_mcp_responsibility.mmd`](diagrams/host_mcp_responsibility.mmd)

---

## 3. Visual Impact estimation

### 3.1 Leverage tiers (frontend UI)

Invest MCP intelligence proportional to **how much of the user’s first impression and task success** the decision controls.

| Tier | Impact | Decision domains | Typical MCP spend |
|------|--------|------------------|-------------------|
| **V4 Very High** | Changes “what product this is” | Layout, navigation IA, information hierarchy, design language / inspiration, component foundations, responsive structure, design-system tokens | Inspiration, component select, PDG summary, then observe+review after v0 |
| **V3 High** | Changes major surfaces | Charts, cards, forms structure, spacing *system* (scale), page sections | Component search, form probe, design snapshot/review once |
| **V2 Medium** | Local refinement | Icon families, typography polish, animation, consistency drift | Resource search, consistency audit (if PDG exists), light review |
| **V1 Low** | Pixel-level cosmetic | 14px vs 15px padding, micro kerning, one-off color tweak | **Do not escalate**; observe + verify only if claimed broken |

### 3.2 Mapping leverage → capabilities (existing graph)

| Capability / workflow | Default max tier it may unlock |
|-----------------------|--------------------------------|
| `inspiration_workflow` | V4 |
| `resource_workflow` (fonts for brand) | V3–V4 |
| `resource_workflow` (single icon) | V2 |
| `component_select` / foundations | V4 |
| `design_snapshot` + `design_review` | V3–V4 (post-paint) |
| `design_consistency_audit` | V2–V3 |
| `browser_observe` / `browser_verify` | All tiers (truth + stop condition) |
| `browser_act` for repro | V1–V3 as needed for bugs |

### 3.3 Estimating visual impact for the *current* decision

Deterministic signals (no LLM):

```text
visual_impact =
  base_tier(task_scope, project_archetype)
  × surface_weight(route / IA centrality)
  × novelty(refs_missing, foundations_unselected, first_paint)
  × (1 − polish_saturation)   # after N polish loops, shrinks
```

| Factor | High when… | Low when… |
|--------|------------|-----------|
| `task_scope` | design_driven / redesign / system_setup | surgical / debug |
| `surface_weight` | `/`, marketing hero, primary nav | settings sub-row, toast |
| `novelty` | No inspiration, no PDG, blank page | Refs collected; component known |
| `polish_saturation` | 0 after first paint | Rises after each review with only medium/low findings |

---

## 4. Expected Quality Gain (EQG) estimation

### 4.1 Definition

**Expected Quality Gain** of recommending capability `C` given PSM `S`:

```text
EQG(C | S) ≈ P(new_evidence_useful | S) × Value(evidence_class(C)) × (1 − redundancy(C, S))
```

| Term | Meaning |
|------|---------|
| `P(new_evidence_useful)` | Probability host’s next decision changes for the better |
| `Value(evidence_class)` | Tied to visual impact tier of that evidence |
| `redundancy` | 1 if equivalent artifact already in PSM (fresh scan, refs collected, foundations selected) |

### 4.2 Evidence class values (relative units)

Use **unitless relative scores** (0–10), not dollars — triangulation, not false precision.

| Evidence class | Typical Value | Notes |
|----------------|---------------|-------|
| First inspiration set (greenfield landing) | 9 | High VoI before layout lock-in |
| Figma context (if available) | 9 | Often *replaces* inspiration |
| Component foundation shortlist | 8 | Prevents wrong primitive |
| Design graph / token constraints (repo) | 7 | Cheap repo path |
| First post-v0 design review | 8 | Structural findings |
| Second design review (after host applied blocking fixes) | 5 | |
| Third+ design review | 1–3 | Diminishing hard |
| Consistency audit (mature PDG) | 6 | |
| Consistency on empty PDG | 2 | Prefer build graph / ship v0 first |
| Observe/verify on surgical fix | 8 | Correctness leverage |
| Inspiration on surgical button color | 0–1 | Near-zero VoI |

### 4.3 Value of information (VoI) principle

From decision analysis: buy information only if:

```text
EV(best action | with info) − EV(best action | without info)  >  Cost(info)
```

In MCP terms: if the host already has a clear Figma frame and component list in chat, **EQG(inspiration) ≈ 0** even on a landing page.

---

## 5. Cost model

### 5.1 Cost dimensions

| Dimension | Measured by | Examples |
|-----------|-------------|----------|
| **Latency** | Tool `latency_ms` / class | Inspiration collect, design review, SEO pro |
| **Process cost** | Browser launch / network | Headed providers |
| **Payload cost** | Response size / images | Full observe + annotated screenshots |
| **Episode budget units** | Intelligence Budget points | See §6 |
| **Opportunity cost** | Delaying host implement | Every pre-paint tool postpones code |

### 5.2 Suggested cost classes (align with existing Performance taxonomy)

| Class | Budget units (proposal) | Capabilities (examples) |
|-------|-------------------------|-------------------------|
| **Instant** | 0–1 | health, resolve_*, design_graph_summary, verify |
| **Fast** | 2–3 | observe summary, probe_form, component plan |
| **Medium** | 4–6 | component search/select, design snapshot, design review |
| **Heavy** | 8–12 | inspiration collect multi-provider, full audits, SEO pro |

Reuse / skip rules set **effective cost = 0** when evidence already satisfies.

---

## 6. Intelligence Budget model

### 6.1 Episode budget

Every coordination episode allocates a finite **Intelligence Budget** `B`.

```text
B_total = B_base(task_scope) + B_bonus(visual_impact_ceiling) − B_penalty(debug/blocking)
```

| `task_scope` | Suggested `B_base` (units) | Intent |
|--------------|----------------------------|--------|
| surgical | 6–10 | Observe + verify + maybe one resolve |
| feature_incremental | 12–18 | ORAV + selective consult |
| design_driven | 28–40 | Orient + one critique cycle |
| redesign | 32–45 | Orient (possibly skip inspiration if Figma) + critique |
| system_setup | 24–36 | Component + PDG + light observe |
| debug | 10–16 | Blocking-first; suppress design Heavy |

### 6.2 Spend ledger (PSM fields — additive)

Proposed PSM extensions (research schema only):

```text
episode.intelligence_budget:
  total: number
  spent: number
  remaining: number
  ledger: [{ capability, units, eqg_estimated, rationale, at }]

situation.effort:
  task_scope: surgical|...
  visual_impact_ceiling: V1|V2|V3|V4
  polish_loops: number
  diminishing_returns: none|soft|hard
```

Existing hooks: `retry_counters.capability_attempts`, playbook `retry_budget`, `H_VERIFY_BUDGET` — budget generalizes those ideas beyond verify.

### 6.3 Spend rule

```text
IF estimated_cost(C) > remaining_budget:
  recommend STOP or cheaper substitute
ELIF EQG(C)/cost(C) < ROI_threshold:
  recommend STOP or host-only reason
ELSE:
  suggest C; debit budget on successful tool completion
```

`ROI_threshold` is stricter as `polish_loops` increase (diminishing returns).

### 6.4 What “STOP” means

`stop_reason` already exists. Add soft reasons (advisory):

| `stop_reason` (proposal) | When |
|--------------------------|------|
| `budget_exhausted` | Remaining < cheapest useful step |
| `roi_below_threshold` | Next C fails EQG/cost |
| `diminishing_returns_hard` | Polish saturation |
| `playbook_complete` | Existing |
| `verify_passed_sufficient` | Surgical/debug success |

Host may continue; briefing should say *why* stopping is rational.

---

## 7. Engineering ROI model

### 7.1 Core formula

```text
ROI(C | S) = EQG(C | S) / max(cost(C | S), ε)
```

Recommend `C*` that maximizes ROI among **eligible** capabilities (gated by CapabilityRouter + scope).

### 7.2 Triangulation (avoid single-metric lies)

Run two coarse checks before Heavy spend:

1. **Leverage check:** Is `visual_impact` of the *decision* ≥ V3? If no → forbid Heavy design gather.  
2. **Payback check:** Will evidence change the *next host commit’s structure* (layout/components), or only cosmetics? Structure → proceed; cosmetics → host-only.

If leverage says yes and payback says no → **prefer cheaper evidence** (repo PDG, one screenshot) over inspiration collect.

### 7.3 Tech-lead heuristics (compiled)

| Situation | High-ROI move | Low-ROI move |
|-----------|---------------|--------------|
| Blank landing, no Figma | Inspiration discover (Fast/Medium) | Immediate design review (no UI) |
| Figma connected | Figma context + component select | Inspiration |
| Button color bug | Observe + verify | Inspiration + design review loop |
| After v0, blocking UI issues | Design review once | Fourth review |
| PDG empty, first page | Ship hierarchy with host; light snapshot | Full consistency audit |
| Findings all V1 | STOP; host polish from screenshot | Another consistency audit |

### 7.4 Maximizing influence **without** maximizing MCP usage

Influence comes from **timing and leverage**, not call count:

1. Put evidence **before** irreversible layout decisions (generation phase).  
2. One high-quality inspiration set beats three mediocre recollects.  
3. One design review after v0 beats continuous pixel nagging.  
4. Push narrative synthesis to host — MCP supplies facts that make the brief *better*.  
5. Prefer **Instant** evidence that widens host attention (PDG summary, resolve_route, screenshot) over **Heavy** when ROI similar.

---

## 8. Diminishing Returns detection

### 8.1 Signals (deterministic)

| Signal | Soft DR | Hard DR |
|--------|---------|---------|
| Design review loops this episode | ≥2 | ≥3 |
| New findings severity mostly advisory | soft | all V1/cosmetic |
| Same `scan_id` / near-identical screenshot hash | soft | hard |
| Capability attempt count for `design_review` | ≥2 | ≥3 without blocking change |
| Host verify passed + blocking empty | — | prefer STOP |
| Inspiration collect with 0 new providers left | hard | — |
| Budget remaining < Medium class | soft → substitute Instant | hard STOP |

### 8.2 Polish saturation

```text
polish_saturation = f(polish_loops, fraction_findings_below_V2, eqg_realized_last_step)
```

When saturation high:

- Suppress `inspiration_workflow`, Heavy collect, optional consistency.  
- Allow Instant observe/verify only if host claims a specific remaining defect.  
- Briefing: “Diminishing returns — further design loops unlikely to move hierarchy; implement remaining polish in host.”

### 8.3 Relation to economic diminishing returns

In SE: extra testing/tuning rounds find fewer critical defects. Design critique mirrors this — early reviews change structure; late reviews argue spacing. The coordinator should **detect the phase shift** and hand cosmetic work to the host without more MCP Heavy tools.

---

## 9. Decision procedure (coordinator mental model)

```text
on each briefing refresh:
  1. Update task_scope, visual_impact_ceiling, budget remaining (PSM)
  2. Candidate set = playbook step ∩ CapabilityRouter.eligible ∩ impact_allows
  3. For each candidate C:
       compute cost, EQG, ROI
  4. If best ROI < threshold OR budget insufficient:
       stop_reason = roi_below_threshold | budget_exhausted | diminishing_returns_*
       suggested_capability = null
       suggested_semantic_action = host_reason_or_implement   # host-only
  5. Else:
       suggest argmax ROI
       attach routing_rationale + benefit_claim + skip_condition + cost_units
```

See: [`diagrams/effort_allocation_loop.mmd`](diagrams/effort_allocation_loop.mmd)

---

## 10. Integration with Coordination Intelligence (minimal change)

### 10.1 What already exists

| Asset | Relevance |
|-------|-----------|
| PSM `episode.retry_counters` | Prototype for spend ledger |
| Playbook `retry_budget` / LoopGovernor | Local budgets; generalize |
| `H_VERIFY_BUDGET`, lazy SEO, snapshot cache heuristics | Cost-awareness precedents |
| Capability `risk` / `requires` gates | Soft eligibility |
| `CoordinatorBriefing` | Place for ROI rationale |
| Design / inspiration / component playbooks | Phases to budget, not always run |
| Report 07 boundary | Host reasons; MCP advises |

### 10.2 Smallest viable extensions

| Layer | Change | New architecture? |
|-------|--------|-------------------|
| **Heuristics YAML (R7)** | `H_ROI_*`, `H_BUDGET_*`, `H_DIMINISHING_*`, impact tier tables | No — artifact amp |
| **PSM schema (R1)** | `intelligence_budget`, `effort`, `polish_loops` | Additive fields |
| **ClusterResolver** | Set `task_scope` / impact ceiling from intent + archetype signals | Local |
| **CapabilityRouter.gate** | Reject (in *suggestion space*) Heavy when scope=surgical or DR=hard | Already advisory |
| **`_refresh_briefing`** | Score EQG/ROI; pick stop vs suggest; `routing_rationale` | Local |
| **Playbook composition** | `design_orient.generation` as optional path when scope+budget allow | R4 only |
| **normalize.py** | Debit budget on capability completion; bump polish_loops on review | Local |
| **AGENT_GUIDE** | One page: trust budget STOP; don’t farm MCP | Docs |

### 10.3 Explicit non-goals

- Mandatory tool rejection based on budget.  
- MCP-side design brief generation LLM.  
- Replacing Capability Graph with an RL optimizer.  
- Perpetual maximization of verify/design loops.

### 10.4 Validation ideas (later)

| Case | Expect |
|------|--------|
| “Fix button padding” | Budget low; no inspiration; ORAV only |
| “New landing page” | Orient spend before implement; one review after v0 |
| Third design review with only advisory findings | `diminishing_returns_hard` |
| Figma connected redesign | Skip inspiration; spend on context + foundations |
| Budget nearly empty mid-landing | Prefer Instant observe/verify over Heavy collect |

---

## 11. Increasing UI influence without increasing latency

### 11.1 Influence levers that are cheap

| Lever | Why high influence / low latency |
|-------|----------------------------------|
| **Earlier** inspiration/resources | Structure locked early; one Fast discover ≠ many post-hoc reviews |
| **Instant** PDG / resolve before code | Steers host away from wrong files/primitives |
| **Screenshot + visual_insights on first observe** | Host “sees”; avoids blind coding |
| **Single foundation select** | Prevents inventing bespoke buttons/tables |
| **One critique cycle** after v0 | Catches hierarchy defects before polish spirals |
| **Strong STOP** | Prevents slow waste; host finishes polish from evidence already in context |

### 11.2 Parallelism and caching (existing patterns)

Reuse: `H_SNAPSHOT_CACHE`, component select internal parallel consult, shadcn catalog warm, scan_id reuse — **effective cost zero** when applied. Effort allocation should treat cache hits as free and **not** re-debit full units (or debit 0).

### 11.3 Latency budget as first-class constraint

For agent UX, wall-clock matters more than completeness:

```text
preferred_next =
  argmax ROI(C)
  among C where expected_latency_ms < L_agent_patience(task_scope)
```

Surgical `L` ~ seconds; design_orient may allow one Medium step; never chain two Heavies without host intervening.

### 11.4 “Influence density”

Define:

```text
influence_density = ΔUI_structure_probability / latency_ms
```

Optimize density, not total influence. A 2s inspiration discover that prevents a wrong layout beats a 40s second design review that tweaks padding.

---

## 12. Worked examples

### 12.1 New SaaS landing (design_driven, V4)

| Step | Cost | EQG | ROI | Notes |
|------|------|-----|-----|-------|
| health + session | 1 | 5 | high | Required |
| inspiration discover | 5 | 9 | high | Refs=0 |
| host design brief | 0 MCP | — | — | Host reason |
| component select | 5 | 8 | high | Foundations |
| host implement v0 | 0 MCP | — | — | |
| observe + design review | 6 | 8 | high | First critique |
| host apply blocking | 0 | — | — | |
| verify | 1 | 7 | high | |
| 2nd design review | 6 | 2 | **low** | Soft DR → STOP polish to host |

### 12.2 Button padding (surgical, V1)

| Step | Cost | EQG | ROI |
|------|------|-----|-----|
| observe | 2 | 6 | high |
| verify | 1 | 8 | high |
| inspiration | 8 | 0.5 | **reject** |
| design review | 6 | 1 | **reject** |

Budget ~8; after verify pass → `verify_passed_sufficient`.

### 12.3 Redesign with Figma (redesign, V4)

| Step | Decision |
|------|----------|
| Inspiration | **Skip** (EQG≈0; Figma replaces) |
| Figma context | Spend |
| Component / PDG | Spend if gaps |
| Post-v0 review | Spend once |
| Consistency | Spend if PDG mature |

---

## 13. Supporting diagrams

| File | Content |
|------|---------|
| [`diagrams/host_mcp_responsibility.mmd`](diagrams/host_mcp_responsibility.mmd) | Host vs MCP boundary |
| [`diagrams/effort_allocation_loop.mmd`](diagrams/effort_allocation_loop.mmd) | Budget / ROI loop |
| [`diagrams/visual_impact_tiers.mmd`](diagrams/visual_impact_tiers.mmd) | Impact tiers → spend |
| [`diagrams/diminishing_returns.mmd`](diagrams/diminishing_returns.mmd) | Polish saturation |

---

## 14. Open questions for review

1. Should budget units be **calibrated to measured latency** of tools in this repo, or stay abstract until implementation?  
2. Should `routing_rationale` be host-visible always, or only when recommending Heavy / STOP?  
3. Do we expose `perception_coordinator_briefing` fields for budget remaining so agents can self-check?  
4. How aggressively should surgical scope **suppress** even Medium review when the route is a marketing page but the *ask* is one-line copy? (Ask intent ≫ page archetype.)  
5. Alignment: leaf_hint remains telemetry only — confirm impact tiers never bind to research state IDs (H_LEAF_HINT_TELEMETRY_ONLY).

---

## 15. Recommendation to reviewers

Approve this research direction if you agree that:

1. **Effort allocation** is a first-class coordination concern alongside playbook selection.  
2. The MCP’s job is to **maximize host LLM decision quality per second**, not MCP call count.  
3. **Intelligence Budget + visual leverage + EQG/ROI + diminishing returns** can sit in heuristics + PSM fields + briefing logic **without** new modules or mandatory control.  
4. UI influence is increased by **early high-leverage evidence** and **disciplined STOP**, not longer evaluation chains.

**Do not implement** until this document and the prior design-driven proposal are reviewed together as one program: *when to intervene* × *how much to spend*.

---

## References (internal)

- `coordination_layer/research/reports/07_coordination_intelligence_architecture.md`  
- `coordination_layer/runtime/README.md` (R0–R11; advisory coordinator)  
- `coordination_layer/runtime/decision_heuristics.v1.yaml`  
- `src/navigation/mcp/AGENT_GUIDE.md` (host brain)  
- Prior session proposal: design-driven workflow routing (intervention timing)

## References (external, conceptual)

- Law of diminishing returns in software development (DevIQ; general SE practice)  
- Engineering ROI method triangulation (multiple metrics beat one false-precise score)  
- Value of information / decision analysis (buy evidence only when EV uplift > cost)  
- Pareto / leverage allocation for product and design decisions
