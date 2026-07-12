# Assumptions Log

Every non-obvious modeling decision made during the state-space build lives here. Each entry is dated. If an assumption is later revised, the original entry stays and a follow-up entry cites it.

## Format

```
### A-YYYYMMDD-NNN — <short title>

- **Assumption:** <what we are taking as given>
- **Why:** <reasoning>
- **Impact:** <which parts of the corpus depend on this>
- **Revision:** <link to later entry if superseded>
```

---

### A-20260712-001 — Both `mcp_ready: true` and `mcp_ready: false` states are in scope

- **Assumption:** The state space models both what MCP can do today and what it aspires to do. Every state carries `mcp_ready: true | false`. Aspirational states are flagged and reference the specific scaffold gap.
- **Why:** User explicitly chose "both" in the plan clarification. Some project conditions (e.g., "component installed and adapted to codebase") only become reachable when scaffold work lands — the Coordination Layer needs to reason about both today and tomorrow.
- **Impact:** State schema, exploration log, all Phase 3 enumeration, coordination input report.

### A-20260712-002 — States are project-condition-first, not agent-behavior-first

- **Assumption:** Each state describes the condition of the project (route exists, form spec inferrable, SEO not yet audited) rather than what the agent is doing.
- **Why:** State-space search algorithms (BFS/DFS/A*/branch-and-bound) all operate over world states. Agent actions become edges. Modeling the world explicitly means the Coordination Layer can plan multiple valid paths through the same state.
- **Impact:** Every YAML file. Names avoid verbs like "the agent runs...".

### A-20260712-003 — Runtime artifacts (`session_id`, `scan_id`, `snapshot_id`) are attached, not identifying

- **Assumption:** A state is not identified by whether a `scan_id` exists — many states can share the same scan. Runtime artifacts appear in the `dependencies` and `known_evidence` fields, not in the state ID.
- **Why:** A given project condition (say "landing page has SEO recs pending fix") is the same state whether the agent captured the scan five seconds ago or five minutes ago. Confusing evidence with identity causes state explosion.
- **Impact:** State ID convention, evidence posture axis, cluster merge logic.

### A-20260712-004 — SEO evidence and PDG are treated as long-lived state, not per-session

- **Assumption:** `seo_graph.json` and `design_graph.json` persist across sessions and inform state entry conditions. A project entering "SEO campaign" is different if a graph already exists.
- **Why:** Both stores are documented as persistent (`.cache/seo_graph.json`, `.perception/design_graph.json`) and drive `audit.diff` / `graph.diff` queries. They are project-level facts.
- **Impact:** Evidence posture domain for `seo` and `design_system` can be `known` even when no session is active.

### A-20260712-005 — Actions are semantic, not tool names

- **Assumption:** Action strings in `possible_actions` are verbs like `probe_form_rules`, `derive_ai_visibility`, `verify_current_route`. They are never `perception_probe_form`.
- **Why:** The Coordination Layer is what translates semantic action → tool sequence. Anchoring actions to tool names now would prevent the Coordination Layer from having room to design.
- **Impact:** All Phase 3 enumeration, planning patterns.

### A-20260712-006 — Every state must have at least one recoverable failure state

- **Assumption:** For every non-terminal state we identify at least one realistic failure mode and its recovery path. Terminal states (`done`, `abandoned_by_user`) are exempt.
- **Why:** Real projects fail. A Coordination Layer that only handles happy paths is useless. Building the failure edges into the state graph itself, rather than a separate "error handler", forces the graph to be honest about risk.
- **Impact:** State schema requires `failure_states` and `recovery_paths` on non-terminal nodes.

### A-20260712-007 — 12 scenario forests are the enumeration seed, not the taxonomy

- **Assumption:** The forests are how we search the state space, not how we cluster it. Cluster meta-states in Phase 4 span forests (e.g., "waiting on human" appears in many forests).
- **Why:** Users don't experience projects as forests; they experience them as situations. Clustering by structural similarity (evidence + modules + verification requirements) makes coordination decisions repeatable.
- **Impact:** Phase 3 vs Phase 4 separation, Phase 5 report structure.

### A-20260712-008 — State confidence levels

- **Assumption:** `state_confidence: high | medium | low | speculative`
  - `high`: derived directly from AGENT_GUIDE, module docs, or shipped code
  - `medium`: reasonable extrapolation from existing patterns
  - `low`: real project condition but poorly supported by current MCP
  - `speculative`: depends on roadmap features
- **Why:** Not all states have equal ground truth. The Coordination Layer needs to know which parts of the graph it can trust.
- **Impact:** Every state YAML. Speculative states are `mcp_ready: false` by default.

### A-20260712-009 — Global states span archetypes

- **Assumption:** States prefixed `global.*` (auth blocked, dev server down, verify loop exhausted) apply across every archetype and short-circuit into recovery paths.
- **Why:** The AGENT_GUIDE hard rules (never loop login, never claim done without verify) are cross-cutting. Modeling them as one node reused everywhere avoids duplication.
- **Impact:** `possible_next_states` frequently points into `global.*`.

### A-20260712-010 — Verification requirements are stored as observable predicates

- **Assumption:** `verification_requirements` lists things a checker can observe (URL contains X, text present, JS assertion holds, blocking empty). Not "user is satisfied" or "code is correct".
- **Why:** Only observable predicates can be verified deterministically. This mirrors `SuccessCriteria` in `visual_browser_intelligence/verify/verification.py`.
- **Impact:** Every state's `verification_requirements`. Terminal "done" states inherit the strictest predicate: agent verified + blocking empty.

### A-20260712-011 — Project Situation Model (PSM) replaces "Situation Fingerprint"

- **Assumption:** The runtime object is the **Project Situation Model (PSM)** — evidence, constraints, confidence, episode control, and briefing. `cluster_signature` is a derived routing field inside PSM, not the top-level abstraction.
- **Why:** User decision (Report 08 review). "Fingerprint" implied classification-only; PSM matches the requirement to represent current project state holistically.
- **Impact:** Report 07 naming superseded; all implementation docs use PSM.

### A-20260712-012 — Architecture frozen; P0 distillation

- **Assumption:** Runtime control uses R0–R11 artifacts only. Research states → `state_lexicon` + `cluster_registry.member_state_ids` (telemetry).
- **Why:** User approved architecture freeze 2026-07-12 with amendments (T1 compact, capability_posture in cluster_signature, leaf_hint telemetry-only, capabilities-not-modules).
- **Impact:** `coordination_layer/distillation/build.py` + `coordination_layer/runtime/`; CI validates checksums and no state IDs in playbook control flow.

### A-20260712-013 — PSM Runtime replaces "Evidence Store"

- **Assumption:** The live coordinator state is **PSM Runtime** — not a separate Evidence Store. It owns evidence, postures, constraints, sessions, auth, verification, pending work, and playbook progress.
- **Why:** User refinement before P1 — runtime is the live project representation, not just evidence accumulation.
- **Impact:** `coordination_intelligence.psm.runtime.PSMRuntime`; all planning components read/write PSM only.

### A-20260712-014 — P2 invisible coordinator bridge

- **Assumption:** `CoordinatorBridge` hooks `server.call_tool` after every handler; session_id binds to PSM episode automatically on `perception_session_start`.
- **Why:** User P2 objective — coordination is invisible; host should not call `perception_coordinator_apply_envelope` in normal workflows.
- **Impact:** `data.coordinator` additive block on envelopes; `COORDINATION_DISABLED=1` preserves legacy envelopes exactly.
