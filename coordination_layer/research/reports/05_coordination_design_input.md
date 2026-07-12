# Report 05 — Coordination Design Input

Final research deliverable. Distills the 150-state graph and 24 clusters into design hypotheses for the Coordination Layer. Nothing here is implementation — all suggestions are **grounded in the state-space graph** and either the module inventory or explicit assumptions.

Explicit non-goals (re-stated):
- No tool names as primary transitions.
- No prompt templates.
- No implementation tickets.
- No selection of a specific planner algorithm — proposals only, with pros and cons.

---

## 1. Recurring workflows (top 10 multi-state paths)

Extracted from `possible_next_states` walks across the graph.

1. **Greenfield hero verify path** — `landing.S01.intent.described` → `S02.discovery.stack_chosen` → `dev_server_up` → `S04.architecture.route_plan_ready` → `S05.new_feature.landing_hero.stub` → `S07.verified`. Length 6. Uses framework + visual_browser modules.
2. **Form validation with auth** — `saas.S05.form_validation.v1` → `S07.blocked_by_auth` → `global.auth_gate.requires_human` → `S07.auth_flow.verified_and_state_saved` → `S07.form_validation.invalid_path_verified` → `S07.verified`. Length 6.
3. **SEO audit + fix loop** — `S08.seo_campaign.audit_needed` → `audit_completed_dev` → `fix_applying` → `re_audit_after_fix` (loop up to 3–5 times). Length variable.
4. **Debug via full diagnosis** — `S07.ui_bug.<signal>` → `full_diagnosis_run` → `S07.change_scope_ready` → `S07.<domain>.clean|verified`. Length 4.
5. **Component acquisition happy path** — `S05.query_vague` → `plan_ready` → `candidates_ranked` → `candidate_selected` → `integration_dry_run_report` → `S07.integrated_and_verified`. Length 6.
6. **PDG bootstrap + audit** — `S09.pdg_empty` → refresh → `pdg_seeded_from_snapshot` → `audit_findings_open` → `propose_fix_open` → `S05.applying_fix` → `S09.no_deviation_detected`. Length 7.
7. **Quality trio (a11y + perf + best-practices)** — three parallel three-node cycles under S08 converging into release baseline. Length 3×3.
8. **Release baseline → staging → prod** — `S10.regression_baseline_capture` → `baseline_stored` → `staging_verify` → `staging_verified` → `S11.live_and_monitored`. Length 5.
9. **Hotfix compressed path** — `S11.hotfix_requested` → `S07.<signal>` → `S05.change_scope` → `S11.hotfix_deployed` → `live_and_monitored`. Length 5. Skips most quality gates.
10. **Framework migration incremental** — `S12.plan_ready` → `incremental_progress` (loop) → `completed` → `S10.regression_baseline_capture`. Length variable.

## 2. State clusters and their frequency

Twenty-four clusters (see Report 04) span 150 leaves. Distribution highlights:

- **Consistency (14)**, **SEO (12)**, **Component (12)**, **Debug (12)**, and **Global recovery (12)** are the five largest.
- **Feature clusters** collectively hold 24 members — the "core" of implementation work.
- **Every non-terminal state points at global.recovery** as a failure surface.

## 3. High-risk transitions

Transitions with high blast-radius or `modules_must_not_execute` conflicts:

| From | Risk | Notes |
|------|------|-------|
| Any → `complib.S05.integration_live_scaffold` | Repo mutation without dry-run oversight; `mcp_ready: false` | Coordination must refuse this transition today. |
| SEO pro mode without auth | `auth_required` returned | Never retry pro mode without `seo_connect`. |
| Consistency audit with empty PDG | Empty results mistaken for clean | Must call `pdg_refresh` first. |
| Verify after live mutation without pre-scan captured | Cannot produce diff | Pre-act scan capture is a coordination invariant. |
| Framework migration big-bang | Wholesale regression risk | Prefer incremental unless small project. |
| Design Sense findings ≠ Consistency deviations | Confusing advisory with authoritative | Two different clusters, two different fingerprints. |
| Inspiration/Resource session left open | Ephemeral blob leak | Cleanup is a hard requirement. |
| Auth gate → automated retry | AGENT_GUIDE hard rule violation | Coordination must never loop login. |

## 4. Frequent module combination patterns

From the `relevant_modules` on the leaves:

- **VB + FQ** — implementation + verify + audit path (every S05→S07→S08 flow).
- **VB + DSE + Cons** — design pipeline (S03/S09 all use it).
- **SEO + VB + CB** — SEO audits that include page evidence and codebase hints.
- **Comp + FW + CB + DSense + Cons + VB** — component selection consults five contracts in parallel.
- **DW + VB** — flow-oriented work (auth, forms with probes, multi-step flows).
- **Res + VB (observe-bridge)** — resource matching family-aware, per-page.

## 5. Evidence gates

Decisions that require an evidence posture at or above a threshold before proceeding:

- SEO audit: `ui_runtime: partial|known` (rendering evidence via scan_id preferred).
- Consistency audit: `design_system: partial|known` (PDG populated).
- SEO pro mode: `env` configured (`env_misconfigured` if not).
- Component integrate live: not gate-satisfiable today (`mcp_ready: false`).
- Release sign-off: quality: `verified` on a11y, perf, best_practices; SEO: `verified` on target pages.
- Regression diff: prior baseline must be within TTL (`baseline_stale` if not).

## 6. Missing evidence situations

States where `unknown_evidence` blocks the next natural transition:

- `landing.S02.discovery.dev_server_up` unknowns: content, layout decisions — cannot start design without hearing intent.
- `admin.S06.new_feature.data_table.integrated` unknowns: empty and error states — verify blocked until scenarios simulated.
- `marketing.S03.design.pdg_empty_snapshot_ready` unknowns: design_system standards — consistency audit blocked until PDG built.
- `dssite.S09.consistency_cleanup.token_drift_detected` unknowns: full scope of drift — validators partial.
- `saas.S07.functional_bug.intermittent` unknowns: triggering condition — repro required before hypothesis testing.

## 7. Decision bottlenecks (high fan-out states)

States with 3+ next states. Fan-out sites are natural points for the Coordination Layer to plan choice.

| State | Fan-out | Choices |
|-------|---------|---------|
| landing.S04.architecture.route_plan_ready | 4 | to F02, F03, F04 variants |
| landing.S07.new_feature.landing_hero.verified | 3 | to SEO / A11y / Perf audit |
| marketing.S11.production.live_and_monitored | 3 | hotfix / baseline / SEO diff |
| landing.S08.seo_campaign.audit_needed | 3 | dev / pro / auth-required |
| complib.S05.component_replacement.candidate_selected | 2+ | dry-run / live (scaffold) |
| marketing.S12.framework_migration.plan_ready | 2 | incremental / big-bang |
| complib.S05.component_replacement.candidates_ranked | 2+ | select or refine |

## 8. Lazy evaluation opportunities

States where modules can be deferred until evidence posture upgrades:

- **SEO audit** — defer until page is at S07 (verified) and indexable.
- **Consistency audit** — defer until PDG has non-zero standards.
- **Design Sense** — defer until snapshot captured.
- **AI visibility analyzers** — only run when SEO evidence exists.
- **Perf / A11y audits** — defer past hot iteration; run at S08 or pre-release.
- **PDG refresh** — schedule off-hours or when snapshot deltas exceed a threshold.

## 9. Caching opportunities

Persistent artifacts that already exist and should be preferred over re-collection:

- **SEO graph (`.cache/seo_graph.json`)** — audit.diff queries beat fresh audits when incremental.
- **PDG (`.perception/design_graph.json`)** — knowledge_query beats re-discovery.
- **framework_docs** — already caches; planner should reuse aggressively.
- **DesignSnapshot registry (per session)** — snapshot cached by scan; do not rebuild when scan unchanged.
- **`FigmaDesignContext`** — cached per file_key; planner reuses.
- **State save/restore** — auth reuse across sessions.

## 10. Parallel execution opportunities

Independent evidence collection allowed by module design:

- **Bootstrap probes:** `perception_health` ∥ `detect_framework` ∥ preloading `framework_docs`.
- **Component selection consultations:** Framework ∥ Codebase ∥ Design Sense ∥ Consistency ∥ Browser contracts.
- **Per-page quality iteration:** many pages audit-mode in parallel.
- **SEO + Lighthouse-SEO:** two distinct surfaces, safe to run in parallel then reconcile.
- **Design snapshot ∥ SEO scan** on the same page (both consume the scan).

## 11. Architecture hypotheses

Proposals only. Each has a rationale grounded in the state graph, and a caution.

### Hypothesis A — Hierarchical planner over clusters

- **Structure:** Outer planner picks a **cluster path** (a sequence of clusters). Inner planner picks leaf states within a cluster.
- **Why:** Fits the strong cluster locality of the graph (10 recurring workflows all traverse ≤4 clusters).
- **Caution:** Inter-cluster transitions (F04→F05, F04→F07) are frequent; the outer planner must not treat cluster boundaries as walls.

### Hypothesis B — AND/OR planning graph

- **Structure:** Actions have preconditions (evidence postures) and effects (evidence upgrades). Planner searches for goal state.
- **Why:** Naturally captures evidence gates and lazy evaluation opportunities.
- **Caution:** Global recovery states force a lot of OR-branches; risk of state explosion.

### Hypothesis C — FSM per cluster + top-level dispatcher

- **Structure:** Each cluster is a small FSM (nodes = leaves, edges = actions). A top-level dispatcher picks the FSM based on lifecycle stage + situation class.
- **Why:** Simple, debuggable; mirrors AGENT_GUIDE playbooks 1:1.
- **Caution:** Cross-cluster edges become "escape hatches" that the FSM formalism does not model cleanly.

### Hypothesis D — Reactive planner + intent stack

- **Structure:** Agent maintains an intent stack; each state's `user_intents` maps to on-stack goals. Reactive planner picks the next action satisfying the top goal.
- **Why:** Handles interruptions (user says "wait, first fix this bug") elegantly.
- **Caution:** Progress guarantees weaker; more prone to thrashing under conflicting intents.

### Recommendation for further prototyping

- Start with **Hypothesis C** (FSM per cluster) because it maps most cleanly to AGENT_GUIDE.
- Layer **evidence-gate preconditions** from Hypothesis B to gain lazy evaluation and caching.
- Reserve Hypothesis D as a fallback if user-interruption handling proves messy in FSM.

## 12. Concrete design invariants for the Coordination Layer

Regardless of algorithm choice, these must hold:

1. **Verify-before-done.** No state marked complete without a verify pass and `blocking: []`.
2. **Recovery-is-first-class.** Every plan branch must terminate in a `global.*` state or a successful terminal.
3. **Cleanup on exit.** Ephemeral resources (blob sessions, debug_mode, audit_mode) must close on episode close.
4. **Never loop auth.** `auth_gate.requires_human` STOPS.
5. **Prefer diff to full audit** when persistent graphs (SEO, PDG) exist.
6. **Dry run first.** Component integration defaults to dry-run; live install is `mcp_ready: false`.
7. **Semantic actions, not tool calls.** Coordination Layer plans in semantic verbs; a separate execution layer resolves them to MCP tools.
8. **Retry budget explicit.** OBSERVE→REASON→ACT→VERIFY loop capped at 3–5 iterations; exceed → `verify_loop_exhausted`.
9. **Persistent-first, session-second.** SEO graph, PDG, Figma PAT reused; sessions transient.
10. **Human-in-loop is a state, not an error.** `auth_gate.requires_human` and `user_abandoned` are legitimate destinations.

## 13. Open questions for future research

- **Multi-episode continuity.** How does the state space compose across episodes when persistent artifacts (SEO graph, PDG) age? Suggests a "staleness posture" domain in future evidence models.
- **Cross-project sharing.** When multiple projects share a design system, should PDG entries be portable? Would create a new archetype (`shared_design_system_consumer`).
- **Feedback from acted-upon fixes.** Aging of `verified` back to `partial` after N days? Introduces a "temporal decay" mechanic.
- **Concurrency across sessions.** Two agents editing the same project simultaneously — not modeled here.
- **Human sign-off machinery.** Beyond `auth_gate`, how does the Coordination Layer wait for a code review or release approval? Modeled today as a global state; may deserve a first-class async mechanism.

---

## Deliverable status

- 150 state YAML files under `coordination_layer/research/state_space/states/`.
- 24 clusters catalogued in `coordination_layer/research/state_space/abstracted/cluster_index.md`.
- 8 planning patterns under `coordination_layer/research/planning_patterns/`.
- 12 forest documents under `coordination_layer/research/scenario_graph/forests/`.
- 5 reports under `coordination_layer/research/reports/` (this is #05).
- Diagrams under `coordination_layer/research/diagrams/` (next todo).
- Exploration logs for both batches.
- Assumptions log with 10 entries.

The Coordination Layer design can now begin, informed by this corpus.
