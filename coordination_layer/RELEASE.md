# Coordination Layer — Release Candidate (Frozen Baseline)

**Status:** Feature complete and stable — **do not proactively tune**.  
**Frozen:** 2026-07-12  
**Bundle:** `coordination_layer/runtime/` v1.0.0 (`manifest.json`)

---

## Baseline metrics (regression floor)

| Metric | Baseline |
|--------|----------|
| Workflow success | **14/14 (100%)** |
| Composite coordination score | **99.8%** |
| Capability routing | 100% |
| Playbook selection | 100% |
| Tool efficiency | 100% (0 unnecessary tool calls) |
| Critical recovery failures | 0 |
| Release targets | **MET** |

Evidence: `evals/coordination/reports/latest.json`, `evals/coordination/score_history.jsonl`

---

## Architecture (stable)

The coordination layer is a **deterministic, advisory** planner between playbooks and MCP tools. The **host LLM remains the sole reasoning engine**.

```
Host LLM
    ↓ calls perception_* tools
MCP handlers (unchanged)
    ↓ envelope
CoordinatorBridge (P2 invisible integration)
    ↓
CoordinationIntelligenceService
    ├── PSM Runtime          — evidence, postures, sessions, playbook progress
    ├── ClusterResolver      — cluster.* from live evidence (never research state IDs)
    ├── CapabilityRouter     — T1 capability posture + gates
    ├── PlaybookSelector     — playbook + active step
    ├── StepCompiler         — capability → MCP tool preview
    └── LoopGovernor         — invariants, retry budgets, step advancement
    ↓ reads
Runtime artifacts R0–R11     — coordination_layer/runtime/
```

**Design principles (frozen):**

- Capabilities, not modules — stable T1 capability IDs; tool changes via R8 only
- Research corpus (150 states) informs artifacts; **never participates in runtime control flow**
- `cluster_signature` includes situation class, lifecycle, evidence postures, constraints, capability posture
- `leaf_hint` is telemetry only

Deep architecture: `coordination_layer/research/reports/07_coordination_intelligence_architecture.md`, `08_runtime_artifacts_and_capability_graph.md`

---

## Implementation map

| Component | Path |
|-----------|------|
| Service facade | `src/navigation/coordination_intelligence/service.py` |
| PSM Runtime | `src/navigation/coordination_intelligence/psm/` |
| Planning layer | `src/navigation/coordination_intelligence/planning/` |
| Artifact loader | `src/navigation/coordination_intelligence/artifacts/loader.py` |
| MCP bridge (P2) | `src/navigation/coordination_intelligence/integration/bridge.py` |
| Episode binding | `src/navigation/coordination_intelligence/integration/episode_binding.py` |
| Explicit MCP tools | `perception_coordinator_episode_start`, `_apply_envelope`, `_briefing` |
| Disable integration | `COORDINATION_DISABLED=1` |

---

## Runtime artifacts (R0–R11)

Generated from `coordination_layer/distillation/sources/` — **do not hand-edit runtime/**.

| ID | File | Refinement target |
|----|------|-------------------|
| R2 | `capability_graph.v1.yaml` | Capability contracts |
| R3 | `cluster_registry.v1.yaml` | Cluster registry, playbook gates |
| R4 | `playbook_templates.v1.yaml` | Playbook templates |
| R5 | `invariant_registry.v1.yaml` | Invariant registry |
| R6 | `replan_registry.v1.yaml` | Replan registry |
| R7 | `decision_heuristics.v1.yaml` | Heuristics + `cluster_resolution` scoring |
| R8 | `tool_bindings.v1.yaml` | Tool bindings |
| R9 | `anti_patterns.v1.yaml` | Anti-pattern catalog |

Rebuild only when a **proven** artifact gap requires it:

```bash
pip install pyyaml
python coordination_layer/distillation/build.py
```

---

## Validation & regression

The CVW suite (CVW-01 .. CVW-14) is the **regression gate** for coordination behavior.

```bash
$env:PYTHONPATH="src"
python src/run_coordination_validation.py
pytest tests/test_coordination_validation_suite.py tests/test_coordination_intelligence.py tests/test_coordination_integration.py tests/test_coordination_distillation.py -m unit
```

| Artifact | Purpose |
|----------|---------|
| `coordination_layer/validation/workflows.yaml` | Workflow definitions + success criteria |
| `evals/coordination/reports/latest.json` | Latest full-suite report |
| `evals/coordination/score_history.jsonl` | Score trend log (append-only) |
| `evals/coordination/refinement_log.md` | Historical refinement decisions |

### Simulate-mode measurement scope

| Metric | Simulate behavior |
|--------|-------------------|
| `success` | **Primary gate** — must stay 14/14 |
| `cluster_accuracy` | Outcome-weighted (final cluster + playbook convergence) |
| `cluster_sequence_accuracy` | Raw telemetry sequence (audit only) |
| `step_compilation_accuracy` | Not scored — host replays a fixed script; advisory mismatches recorded in findings |
| `step_compilation_advisory_mismatches` | Informational count per workflow |

Full rubric: `evals/coordination/COORDINATION_VALIDATION_SUITE.md`

---

## Change policy (evidence-driven only)

**Do not** continue tuning heuristics, playbooks, or artifacts to improve metrics.

When a **real workflow fails** or a **regression** is detected:

1. Identify the failing CVW (or new scenario).
2. Trace root cause from `decisions[]`, `findings`, and PSM timeline.
3. Classify: validation expectation · artifact (R3/R4/R7/R8) · coordinator logic.
4. Make the **smallest possible change** (one change per iteration).
5. Re-run the full validation suite.
6. Compare `score_history.jsonl` — keep only if workflow success improves or is preserved with no regressions.

Log every iteration in `evals/coordination/refinement_log.md`.

**Prefer:** validation expectation fix → artifact fix → coordinator fix (last resort).

---

## Execution Runtime (E1–E4 — frozen v1.0.0)

Deterministic execution beneath the coordinator — **no reasoning**:

```
CompiledStep → execution_runtime.execute() → MCP handlers → envelope → CoordinatorBridge
```

Package: `src/navigation/execution_runtime/`  
Docs: `docs/EXECUTION_RUNTIME.md`

| Suite | Baseline |
|-------|----------|
| EVW | 10/10 (100%) |
| Execution unit tests | 19/19 |
| MCP contract | PASS |

---

## Platform v1.0.0 (frozen 2026-07-12)

Full production validation passed. **No further infrastructure work** — future changes from product usage only.

| Gate | Result |
|------|--------|
| CVW | 14/14 |
| EVW | 10/10 |
| Unit/golden pytest | 101/101 |
| MCP contract | PASS |
| Release gate G1–G10 | PASS |
| Performance baseline | Within budget |

Evidence: `evals/production/readiness_report.json`

Re-run: `python src/run_production_validation.py` (sandbox dev server required for live gates)

---

## What is out of scope

- New coordinator abstractions or major features without validation proof
- Metric optimization when 14/14 workflows pass
- Research state IDs in runtime routing
- Changes to existing `perception_*` tool contracts (use R8 bindings only)

---

## Research corpus

`coordination_layer/research/` remains the design reference. It is **read-only input** to distillation — not runtime control flow.
