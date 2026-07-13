# State Space Influence on Runtime Coordination

**Status:** Research only — **not approved for implementation**  
**Date:** 2026-07-14  
**Audience:** Principal / architecture review before Engineering Investment or design-driven routing lands  
**Inputs reviewed together:**
- 150-state corpus (~250 KB) + forests + lifecycle map
- Runtime artifacts R0–R11 (~140 KB)
- Reports 01–08 (esp. 04, 05, 07, 08)
- PSM Runtime, Capability Graph, Playbooks, Validation suite
- [`research/engineering_effort_allocation/`](../engineering_effort_allocation/)
- Design-driven workflow proposal (session)

---

## Executive summary

**We correctly refused to run a 150-state FSM at runtime.**  
**We incorrectly treated that refusal as “the engineering knowledge in the corpus is finished once clusters exist.”**

Distillation preserved the **spine** (24 clusters → playbooks → capabilities → gates) and discarded the **leaf engineering policy** (maturity, module eligibility forks, compressed hotfix paths, opposing design forks, transition intent). The lexicon (R11, ~59 KB) still ships — but **no production code reads it**. Lifecycle stage is on the PSM schema but **coarsely inferred** and barely drives investment.

**Recommended architecture (final before implementation):**

```text
Do NOT load 150 states as a control FSM.
DO keep the corpus as the source of truth for distillation.
DO add ONE new compile-time artifact: Situation Policy Catalog (R12)
    — small enums + policy rows distilled FROM the 150 states
    — drives Engineering Investment, eligibility, EQG priors, STOP bias
DO promote lifecycle stage (S01–S12) into a first-class investment curve
DO keep leaf_hint telemetry-only (optional nearest-leaf for host briefings)
DO NOT grow the Capability Graph or tool surface for this
```

This restores tech-lead judgment **without** false-precision leaf matching.

---

## 1. First principles: why the state space existed

The corpus was never “a classifier training set.” It was a **structured encoding of how experienced frontend engineers think about projects over time**:

| Captured knowledge | Why it matters for coordination |
|--------------------|----------------------------------|
| Project maturity (M0–M6) | Greenfield vs production → effort ceiling |
| Lifecycle stage (S01–S12) | Early: influence structure; late: correctness / regression |
| Engineering situations | Hotfix ≠ redesign ≠ form validation |
| Evidence posture | What’s known / unknown before next spend |
| Transitions & failures | What “good next” and “bad next” look like |
| Module eligibility / forbids | Inspiration forbidden when refs already agreed; SEO forbidden mid-hotfix |
| Recovery paths | How to get unstuck without random tool spam |
| Intent & verification requirements | What “done” means in that situation |

Clusters answer: **which family of playbook?**  
States answered: **given this family, which policy applies?**

Today the second answer is mostly gone from runtime.

---

## 2. What runtime actually uses today

### 2.1 Control path (active)

```text
Tool envelope → PSM normalize → ClusterResolver (affinity scores)
  → PlaybookSelector → LoopGovernor → CapabilityRouter → StepCompiler
  → briefing.suggested_* / stop_reason
```

### 2.2 What is declared but underused

| Asset | Status |
|-------|--------|
| `lifecycle_stage` on PSM | Present; inference coarse (evidence counts / domains) |
| `project_maturity` on PSM | Schema field; not corpus-driven |
| `leaf_hint` | Optional; never used for routing (correct) |
| `state_lexicon.v1.json` | Loaded into bundle; **unread by production code** |
| `lifecycle_stage_state_map.yaml` | Research only — R01–R04 rules not fully in R7 |
| 13/24 clusters → `observe_reason_act_verify.loop` | Playbook collapse hides specialized policy |

### 2.3 Challenge: “clusters are enough”

**Assumption (Report 07/08):** Distilling to 24 clusters loses noise, keeps signal.

**Challenge:** Clusters keep **routing family**; they drop **discriminators inside the family**.

Canonical counterexample (same cluster, opposite policy):

| Research leaf | Inspiration? | Next intent |
|---------------|--------------|-------------|
| `landing.S03.design.direction_agreed_with_references` | Relevant | Capture / architecture |
| `landing.S03.design.direction_agreed_no_references` | **Forbidden** | Architecture or component search |

Both map → `cluster.design.reference_gathering` → `discover_collect_cleanup.inspiration_resource`.  
A tech lead would **not** run the same investment profile. The runtime would.

Other collapses:

- Production **hotfix** shares playbook family with **staging release**.  
- Design Sense redesign-apply collapses into tiny `debug.iteration_target` + generic ORA.  
- Debug’s twelve “each signal has a playbook” claim in cluster_index is not implemented.

**Verdict:** 24 clusters are **necessary but not sufficient** for Engineering Investment / design orientation / STOP quality.

---

## 3. Approaches: how state knowledge can influence runtime

| Approach | Description | Pros | Cons | Verdict |
|----------|-------------|------|------|---------|
| **A. Research only** | Keep corpus offline; never influence runtime beyond current distillation | Max simplicity | Leaves investment / eligibility underpowered | **Insufficient alone** |
| **B. Load 150 FSM** | Match nearest leaf; drive transitions | Max fidelity | Brittle, false precision, rejected by 07/08, host sidelined | **Reject** |
| **C. Heuristics only** | Hand-write more R7 rules forever | Incremental | Diverges from corpus; doesn’t scale; we already under-implement declared heuristics | **Necessary but incomplete** |
| **D. Searchable lexicon at runtime** | Query R11 on complex cases | Cheap (59 KB) | Lexicon lacks eligibility/transitions; unread today; still leaf IDs | **Useful for briefings only** |
| **E. Build-time re-distill** | New artifact(s) compiled from YAML | Single source of truth; no FSM | Needs careful feature design | **Primary recommendation** |
| **F. Partial embed** | Ship subset of fields as vectors on clusters | Midway | Still loses leaf forks unless subtypes exist | Combine with E |
| **G. Host-only briefing packs** | Markdown/JSON packs for LLM from corpus | Amplifies host | No deterministic budget without PSM fields | **Complement E** |

### Recommended hybrid: **E + G + selective C**

```text
150 YAML (research SoT)
        │  distillation build
        ▼
R12 Situation Policy Catalog   ←── NEW (small, deterministic)
R7  Heuristics (maintain/extend)
R11 Lexicon (telemetry + optional host briefing lookup)
R3  Clusters (unchanged role)
        │
        ▼
PSM.situation_policy  +  lifecycle investment band
        │
        ▼
Engineering Investment / EQG priors / eligibility / STOP bias
        │
        ▼
Advisory briefing (host still decides)
```

---

## 4. Proposed R12 — Situation Policy Catalog

**Not a state machine.** A compact table of **discriminated policies** distilled from leaf majorities and known forks.

### 4.1 Discriminators (enums, not 150 IDs)

```text
task_scope:            surgical | feature_incremental | design_driven | redesign | system_setup | debug | hotfix
lifecycle_band:        early | mid | late | production   # derived from S01–S12
maturity_band:         greenfield | growing | mature     # derived from M0–M6
design_reference_posture: none | prose | inspiration | figma | agreed_with_refs | agreed_no_refs
system_posture:        no_ds | partial_ds | mature_ds     # from design_system evidence + PDG
foundation_posture:    unknown | selected | integrated
polish_saturation:     none | soft | hard                 # from effort allocation research
```

These map **from live PSM evidence + intent**, with optional **nearest-leaf hint** for humans — never as control IDs.

### 4.2 Policy row (what each row encodes)

```yaml
policy_id: design.greenfield.no_refs.early
match:
  lifecycle_band: early
  maturity_band: greenfield
  design_reference_posture: none | agreed_no_refs
investment:
  B_base: 32
  visual_impact_ceiling: V4
  allow_heavy: [inspiration_workflow, component_select]
  forbid_or_defer: [seo_evidence_collect]
eqg_priors:
  inspiration_workflow: 9
  design_review: 2          # before first paint — low
  browser_verify: 6
stop_bias: after_orient_then_implement
playbook_ Preference: design_orient.generation → then ORA / critique
```

Opposite row for `agreed_with_refs` **forbids** inspiration — restoring the lost fork **without** matching `landing.S03…` IDs.

### 4.3 Size & maintenance

| Estimate | Notes |
|----------|-------|
| Target rows | **40–80** (not 150) covering Report 05 workflows + maturity×lifecycle bands |
| Size | Likely **<40 KB** YAML |
| Build | Distiller proposes rows from leaf groups; humans approve (same as current curated sources) |
| Validation | CVW: surgical never suggests inspiration; greenfield+no_refs suggests orient before implement |

### 4.4 What stays research-only

- Full transition graphs (422 edges)  
- Forest narrative prose  
- Rare `recovery_paths` detail (fold into global_recovery + replan)  
- Per-leaf verification essay text (host + AGENT_GUIDE)

Do **not** ship the raw 150 YAMLs in the MCP wheel unless for offline docs.

---

## 5. Lifecycle → Engineering Investment (the missing curve)

This is why S01–S12 existed. Investment must **evolve**.

| Band | Stages | Tech-lead stance | Budget bias | Favored evidence | Suppress |
|------|--------|------------------|-------------|------------------|----------|
| **Early** | S01–S04 | Change the trajectory | High `B_base`, V4 ceiling | Inspiration/Figma, foundations, PDG summary, host brief | Premature SEO, consistency audits on empty systems |
| **Mid** | S05–S07 | Ship correct features | Medium | Observe/verify, form/probe, selective component, one design review after meaningful paint | Re-collecting inspiration every feature |
| **Late** | S08–S10 | Harden quality | Medium–low; ROI gate strict | Quality/SEO when indexable, consistency if PDG mature, baselines | Design-orient theater |
| **Production** | S11–S12 | Protect live systems | Low for design; higher for debug/hotfix | Observe, verify, diff, compressed hotfix | Inspiration, heavy design review unless redesign cluster |

```text
Early:   maximize structural influence per dollar of latency
Mid:     balance feature quality vs speed
Late:    maximize correctness; polish only if ROI high
Prod:    minimize blast radius; suppress generative design spend
```

See [`diagrams/lifecycle_investment_curve.mmd`](diagrams/lifecycle_investment_curve.mmd).

**Challenge:** Default PSM lifecycle ≈ `S05_implementation` collapses early projects into mid-band and **under-invests** in orientation. Fixing inference + investment bands is higher leverage than adding tools.

---

## 6. Answers to the eight deliverable questions

### 6.1 How should state space influence runtime decisions?

As **compiled policy priors** (R12) + **lifecycle investment bands**, feeding:

- Intelligence Budget `B_base` / Heavy allow-list  
- EQG priors per capability  
- Module forbid/defer vectors  
- Playbook preference / composition  
- STOP bias (early: don’t stop before orient; late: stop when verify passes + DR)

Not as live leaf matching.

### 6.2 Is the 24-cluster abstraction sufficient?

**For playbook family selection: yes.**  
**For Engineering Investment, design orientation, and eligibility forks: no.**

Keep 24 clusters. Add **situation discriminators + policy catalog** beneath them.

### 6.3 Should information from the 150 states be preserved?

**Yes — selectively:**

| Preserve at runtime | Discard at runtime |
|---------------------|--------------------|
| Maturity / lifecycle bands | Full edge lists |
| Situation discriminators (hotfix, with/without refs, …) | Leaf IDs as control |
| Module eligibility majority / forks | Forest prose |
| EQG/investment priors distilled from leaf intent | Unused full lexicon matching |
| Optional leaf_hint for host briefing | 150-way transitions |

### 6.4 How Engineering Investment should change across stages

See §5. Early = structural influence; mid = feature+verify; late = quality ROI; production = safety + compression.

### 6.5 Is the coordinator missing important engineering context?

**Yes.** Missing today:

1. Greenfield vs mature investment asymmetry  
2. Intra-cluster design forks (inspiration vs not)  
3. Hotfix compression vs release playbook  
4. Lifecycle as investment driver (not just affinity scoring)  
5. Corpus knowledge wired into EQG priors  
6. Lexicon shipped but inert  
7. Declared heuristics / lifecycle map under-implemented  

### 6.6 Architectural simplifications / improvements

| Simplify | Improve |
|----------|---------|
| Don’t revive 150 FSM | Add R12 policy catalog |
| Don’t make leaf_hint control flow | Wire lifecycle → budget |
| Don’t load raw YAML in hot path | Distill at build (already have `build.py`) |
| Don’t add MCP tools for this | Enrich briefing with policy + ROI rationale |
| Don’t parallel Design Workflow Intelligence into PSM | One policy layer shared by ClusterResolver + Effort Allocation |

### 6.7 Risks of over-engineering

| Risk | Mitigation |
|------|------------|
| R12 becomes 150 states in disguise | Cap rows; enums only; forbid state_id in match |
| Premature optimization of unused lexicon | Either wire for briefings or drop from wheel |
| Double systems (heuristics + R12 diverge) | Heuristics implement R12; corpus is SoT via build |
| Host ignores policy | Keep advisory; success = better defaults, not enforcement |
| Validation theater | Few CVW scenarios proving forks + lifecycle bands |

### 6.8 Recommended final architecture (before any implementation)

```text
┌─────────────────────────────────────────────────────────────┐
│ Host LLM — reason, brief, implement, override               │
└───────────────────────────▲─────────────────────────────────┘
                            │ advisory briefing
┌───────────────────────────┴─────────────────────────────────┐
│ Coordination Intelligence                                   │
│  PSM Runtime  ← evidence, artifacts, episode                │
│  Discriminators ← intent + evidence + lifecycle/maturity    │
│  R12 Situation Policy → Budget, EQG priors, allow/forbid    │
│  ClusterResolver (family) + Playbook (+ optional compose)   │
│  CapabilityRouter + Effort ROI gate + LoopGovernor          │
│  StepCompiler → suggested capability OR STOP                │
└───────────────────────────▲─────────────────────────────────┘
                            │ facts
┌───────────────────────────┴─────────────────────────────────┐
│ MCP modules — deterministic evidence only                   │
└─────────────────────────────────────────────────────────────┘

Build-time: 150 states → R12 (+ maintain R2–R11)
Runtime:    never match leaf IDs for control
Telemetry:  optional leaf_hint / lexicon for humans & briefings
```

**Confidence claim:** This is the smallest design that lets the coordinator allocate effort **the way a frontend tech lead would across a project’s life**, without recreating the research FSM.

---

## 7. Mapping to Engineering Effort Allocation

| Effort concept | State-space influence |
|----------------|----------------------|
| Intelligence Budget | `lifecycle_band` × `maturity_band` × `task_scope` from R12 |
| Visual impact ceiling | Early greenfield → V4; production hotfix → V1–V2 |
| EQG priors | Distilled from leaf “what evidence mattered here” |
| Diminishing returns | Late/production bands tighten ROI threshold faster |
| Host vs MCP | Policy recommends *evidence class*; host writes briefs |

Pair with: [`../engineering_effort_allocation/ENGINEERING_EFFORT_ALLOCATION.md`](../engineering_effort_allocation/ENGINEERING_EFFORT_ALLOCATION.md)

---

## 8. Approach evaluation: “available as lightweight reference?”

| Option | Recommendation |
|--------|----------------|
| Keep full 150 YAML in package | **No** (wheel bloat; invites FSM misuse) |
| Keep lexicon searchable in coordinator hot path for routing | **No** |
| Keep lexicon for `leaf_hint` + human/debug briefing | **Yes, optional** |
| Offline research forever | **Yes, SoT** |
| Distill into R12 | **Yes, required for investment intelligence** |
| Consult raw YAML only for complex host prompts | Prefer **prebuilt briefing packs** at build time over raw search |

~250 KB absolute size is not the bottleneck. **Control-flow complexity** is.

---

## 9. What we overlooked (principal review)

1. **Report 04’s “no information loss”** referred to the corpus remaining on disk — not runtime fidelity. Easy to misread.  
2. **Shipping unused lexicon** creates a false sense that leaf knowledge is “in the system.”  
3. **Affinity-based ClusterResolver** optimizes “what tool just ran,” not “what stage of the product life are we in.”  
4. **ORA as default for 13 clusters** is a simplicity win that becomes an investment blind spot.  
5. **Design-driven proposal** and **Effort Allocation** without **lifecycle × maturity policy** would still treat a mature production bug like a greenfield landing if intent keywords misfire.  
6. **Validation suite** proves bridge invariants — it does **not** prove tech-lead effort allocation. New CVW cases are required before claiming confidence.  
7. **AGENT_GUIDE** and CI playbooks remain disconnected; briefings need policy language agents will actually follow.

---

## 10. Implementation boundary (when approved later)

**In scope (small):**

1. Design R12 schema + distiller sketch from leaf groups  
2. Discriminator derivation from PSM evidence  
3. Lifecycle investment bands → budget/EQG  
4. Briefing fields: `situation_policy_id`, `investment_band`, `routing_rationale`  
5. CVW scenarios for forks (inspiration forbid/allow; hotfix suppress design)

**Out of scope:**

- 150-state runtime matcher  
- New MCP tools  
- Mandatory enforcement  
- MCP-side LLM  
- Redesigning Browser Intelligence / Capability Graph topology

---

## 11. Decision ask for reviewers

Approve research direction if you agree:

1. Clusters stay; **policies** return.  
2. State space remains research SoT and **compile-time** influence via R12 — not a runtime FSM.  
3. Lifecycle + maturity must drive **Engineering Investment**.  
4. Lexicon is telemetry/briefing — never control.  
5. We will not implement Effort Allocation until this + Effort Allocation docs are jointly accepted.

---

## References

- `coordination_layer/research/reports/05_coordination_design_input.md`  
- `coordination_layer/research/reports/07_coordination_intelligence_architecture.md`  
- `coordination_layer/research/reports/08_runtime_artifacts_and_capability_graph.md`  
- `coordination_layer/research/lifecycle/lifecycle_stage_state_map.yaml`  
- `coordination_layer/runtime/README.md`  
- `research/engineering_effort_allocation/ENGINEERING_EFFORT_ALLOCATION.md`
