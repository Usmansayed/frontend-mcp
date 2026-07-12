# Report 02 — Frontend Lifecycle Research

Companion to `01_mcp_module_inventory.md`. Where Report 01 catalogs the tools, Report 02 catalogs the **work**: how a real frontend project moves through its lifecycle, independent of any specific tooling. This report grounds the five axes used in every state YAML.

Sources: `AGENT_GUIDE.md`, `docs/PRODUCTION_TEST_PLAN.md`, first-principles frontend engineering practice, and cross-check against the 150 state YAMLs.

---

## 1. Why an ontology first

Modeling "the project" is easier than modeling "the agent". The project moves through stages regardless of who or what makes the changes. If our ontology captures project reality, it will be usable by any agent, any planner, any tool — including tools we haven't built yet.

The five axes chosen are:

- **Axis A — Project maturity** (M0..M6): overall codebase maturity.
- **Axis B — Lifecycle stage** (S01..S12): what step of the current episode we're in.
- **Axis C — Evidence posture** per domain (unknown|partial|known|verified|regressed).
- **Axis D — Project archetype**: durable structural properties.
- **Axis E — Situation class**: what triggered this episode.

Together, they form a **fingerprint** for every state, enabling clustering, planning, and diagnosis.

## 2. What frontend work actually looks like

- **Non-linear.** Real projects loop S07↔S05, jump S11→S05 on hotfix, and cycle S09 every release.
- **Evidence-driven.** Decisions are only as good as the freshest evidence. Stale data lies.
- **Human-in-the-loop.** Auth, sign-off, design decisions, and abandonment all require the human. Automation must be graceful about that.
- **Cross-cutting.** Quality (S08), consistency (S09), and SEO (S08) are recurring — they aren't done once.
- **Failure-heavy.** More time is spent in F05 debugging and F12 recovery than the happy paths.

## 3. Why 12 scenario forests

Because a real project can be described as **twelve overlapping stories**:
- Bootstrap once.
- Design many times.
- Acquire components many times.
- Build many features.
- Debug many times.
- Audit many times.
- Grow SEO many times.
- Refine consistency many times.
- Release many times.
- Maintain forever.
- Migrate rarely.
- Recover from failure whenever needed.

Each forest is one story. Cross-links model the reality that stories interleave.

## 4. Why 24 archetypes

Frontend projects are not homogeneous. Site class shapes non-negotiables (an ecom needs SEO + perf; an admin needs a11y + form correctness). Structure (monorepo, MFE) shapes evidence collection. Rendering posture (CSR vs SSR) shapes SEO risk. Origin (greenfield vs legacy) shapes starting evidence posture.

## 5. Why five posture levels per domain

`unknown → partial → known → verified → regressed` is the smallest expressive set:

- `unknown`: agent has never checked.
- `partial`: agent has checked but data is stale, incomplete, or low-fidelity.
- `known`: fresh, high-fidelity data is in hand.
- `verified`: known data has been used to pass a success criterion.
- `regressed`: previously verified data is no longer true.

Coordination decisions differ significantly across these levels. Anything coarser would hide meaningful choices.

## 6. Why situation class is separate from stage

The same stage can host very different situations. S05 implementation looks different for `new_feature` vs `component_replacement` vs `framework_migration`. The situation class carries the "why now" — the stage carries the "where in the pipeline".

## 7. Grounding against AGENT_GUIDE

The AGENT_GUIDE's ten playbooks (§2–§10 plus §15) each map onto one of our forests or clusters:

| AGENT_GUIDE section | State-space home |
|---------------------|------------------|
| §2 New / changed UI | F02, F03, F04, cluster.feature.* |
| §3 Debugging | F05, cluster.debug.signal_class |
| §4 Forms | cluster.feature.form_pipeline |
| §5 Navigation / guards | cluster.feature.auth_flow, F04 nav change |
| §6 Multi-step flows | cluster.feature.flow_pipeline |
| §7 Regression | F09, cluster.release.baseline_and_staging |
| §8 Viewport | marketing.S07.ui_bug.responsive_break |
| §9 Edge cases | F12 global, cluster.debug.signal_class |
| §10 Code ↔ UI | cluster.debug.signal_class (correlation actions) |
| §15 AI visibility | cluster.seo.audit_cycle AI branch |

The mapping is 1:many — a playbook may map to a leaf, a cluster, or a pattern.

## 8. What the corpus explicitly excludes

- Prompt engineering.
- Any specific planner algorithm.
- Any tool-name mapping to actions.
- The Coordination Layer itself.

These are downstream of this research.
