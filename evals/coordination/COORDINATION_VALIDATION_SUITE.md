# Coordination Intelligence — Validation Suite

**Status:** Regression gate — release candidate frozen 2026-07-12  
**Baseline:** 14/14 pass · 100% workflow success · 99.8% composite  
**Runner:** [`src/run_coordination_validation.py`](../../src/run_coordination_validation.py)  
**Specs:** [`coordination_layer/validation/workflows.yaml`](../../coordination_layer/validation/workflows.yaml)  
**Frozen baseline:** [`coordination_layer/RELEASE.md`](../../coordination_layer/RELEASE.md)

---

## Purpose

Regression-test that Coordination Intelligence orchestrates **complete frontend engineering workflows** — not isolated MCP tool calls — by recording every coordinator decision and comparing it to expected engineering outcomes.

The **primary gate is `success`** (per-workflow `success_criteria`). Other metrics are diagnostic unless a workflow fails.

---

## Workflow catalog (CVW-01 .. CVW-14)

| ID | Workflow | Primary cluster | Primary playbook | Modules exercised |
|----|----------|-----------------|------------------|-------------------|
| CVW-01 | Build landing page from Figma | `cluster.design.figma_pipeline` | discover → snapshot/consistency | Figma, Browser, Snapshot, Design Sense, Consistency |
| CVW-02 | Build page from inspiration only | `cluster.design.reference_gathering` | discover_collect_cleanup | Inspiration, Resource, Browser, Snapshot |
| CVW-03 | Improve existing page | `cluster.debug.iteration_target` | observe_reason_act_verify | Browser, Quality |
| CVW-04 | Add new feature (form) | `cluster.feature.form_pipeline` | invalid_before_valid.form | Design Workflow, Browser |
| CVW-05 | Replace component library | `cluster.component.acquisition_pipeline` | search_select_integrate | Component, Framework, Codebase, Browser |
| CVW-06 | Improve accessibility | `cluster.quality.audit_cycle` | observe_reason_act_verify | Quality, Browser |
| CVW-07 | Improve SEO | `cluster.seo.audit_cycle` | audit_fix_verify.seo | SEO, Browser, Codebase |
| CVW-08 | Improve AI Visibility | `cluster.seo.audit_cycle` | audit_fix_verify.seo | SEO (+ AI readiness block) |
| CVW-09 | Fix responsive issues | `cluster.debug.signal_class` | observe_reason_act_verify | Browser, Quality (diagnosis) |
| CVW-10 | Debug runtime issues | `cluster.debug.signal_class` | observe_reason_act_verify | Browser, Quality (console) |
| CVW-11 | Optimize performance | `cluster.quality.audit_cycle` | observe_reason_act_verify | Quality, Browser |
| CVW-12 | Improve consistency | `cluster.consistency.audit_cycle` | snapshot_review_consistency | Consistency, Snapshot, Browser |
| CVW-13 | Migrate framework | `cluster.migration.framework_or_redesign` | observe_reason_act_verify | Framework, Codebase, Browser |
| CVW-14 | Production maintenance | `cluster.production.live_and_incidents` | baseline_and_regression | Browser (baseline/diff) |

---

## Metrics (per workflow)

| Metric | What it measures | Simulate notes |
|--------|------------------|----------------|
| **`success`** | Meets `success_criteria` | **Primary regression gate** |
| `capability_routing_accuracy` | Tool → T1 capability mapping | Fully scored |
| `playbook_accuracy` | Expected playbooks selected | Fully scored |
| `cluster_accuracy` | Cluster routing quality | Outcome-weighted (final cluster + playbook) |
| `cluster_sequence_accuracy` | Raw `cluster.*` sequence membership | Audit telemetry only |
| `step_compilation_accuracy` | Compiled tools vs next tool | **Not scored** in simulate — host replays fixed script |
| `step_compilation_advisory_mismatches` | Advisory compile vs script divergence | Informational |
| `governor_accuracy` | Playbook step advancement | Diagnostic |
| `recovery_score` | Verify-fail / blocking recovery | Diagnostic |
| `replanning_quality` | Stop reasons / replan triggers | Diagnostic |
| `unnecessary_tool_calls` | Tools outside expected set | Must stay 0 at baseline |
| `elapsed_ms` | Simulate replay time | Informational |

### Global coordination score

Every suite run appends to `evals/coordination/score_history.jsonl` with categories:

- Cluster Accuracy, Capability Routing, Playbook Selection, Step Compilation (when applicable)
- Recovery Quality, Replanning Quality, Tool Efficiency, Overall Workflow Success

Composite excludes metrics not applicable in simulate mode (e.g. step compilation).

---

## Decision record (per tool step)

Each step in `decisions[]` captures:

- Tool invoked and envelope `ok`
- **PSM snapshot:** cluster, lifecycle, completed steps, blocking, capability posture
- **Coordinator briefing:** suggested capability, semantic action, compiled tools
- **Governor:** whether step advanced
- **Expected vs actual** capability for routing accuracy

---

## Running the suite

```bash
$env:PYTHONPATH="src"
python src/run_coordination_validation.py
```

Single workflow:

```bash
python src/run_coordination_validation.py --workflow CVW-04
```

### Live mode (where linked)

| Workflow | Live runner |
|----------|-------------|
| CVW-04 | `src/run_mcp_eval_validation_form.py` |
| CVW-08 | `src/run_mcp_eval_ai_visibility.py` |

---

## On failure — classification rubric

| Category | Examples |
|----------|----------|
| **validation_expectation** | Simulate scorer too strict; success criteria mismatch |
| **artifact_gap** | Cluster signal, playbook mapping, anti-pattern (R3/R4/R7/R8) |
| **coordinator_logic** | PSM, resolver, governor bug (last resort) |
| **poor_routing** | Wrong final cluster affecting success |
| **incorrect_playbook_selection** | Wrong playbook affecting success |
| **recovery_behavior** | Wrong capability after verify-fail |

**Change policy:** One smallest change per iteration. Re-run full suite. Keep only if success is preserved or improved. Log in `evals/coordination/refinement_log.md`.

**Do not** tune artifacts or coordinator when 14/14 pass.

---

## Reports

```
evals/coordination/
  reports/latest.json           # Full suite summary + coordination_score
  reports/CVW-XX/report.json    # Per-workflow detail
  score_history.jsonl           # Append-only trend log
  refinement_log.md             # Iteration decisions
```

---

## CI integration

```bash
pytest tests/test_coordination_validation_suite.py tests/test_coordination_intelligence.py tests/test_coordination_integration.py tests/test_coordination_distillation.py -m unit
```

Full simulate suite:

```bash
python src/run_coordination_validation.py
```

Exit code 1 if any workflow fails `success`.
