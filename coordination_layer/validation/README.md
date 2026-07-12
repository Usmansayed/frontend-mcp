# Coordination Intelligence — Validation & Regression

**Status:** Regression gate (release candidate frozen 2026-07-12)

The CVW suite proves the coordinator orchestrates complete frontend engineering workflows. **14/14 must pass** on every coordination-related change.

## Quick start

```bash
pip install pyyaml
$env:PYTHONPATH="src"
python src/run_coordination_validation.py
```

```bash
pytest tests/test_coordination_validation_suite.py tests/test_coordination_intelligence.py tests/test_coordination_integration.py tests/test_coordination_distillation.py -m unit
```

## Baseline (do not regress)

| Metric | Floor |
|--------|-------|
| Workflow success | 14/14 |
| Composite score | 99.8% |
| Unnecessary tool calls | 0 |

Trend log: `evals/coordination/score_history.jsonl`

## What gets measured

| Dimension | Primary gate? | Notes |
|-----------|---------------|-------|
| **Success** | **Yes** | Meets per-workflow `success_criteria` |
| Capability routing | Diagnostic | Tool → T1 capability mapping |
| Playbook accuracy | Diagnostic | Expected playbooks selected |
| Cluster accuracy | Diagnostic (simulate) | Outcome-weighted in simulate mode |
| Cluster sequence accuracy | Audit | Raw telemetry — `cluster_sequence_accuracy` per workflow |
| Step compilation | N/A in simulate | Host replays fixed script; see `step_compilation_advisory_mismatches` |
| Recovery / replanning | Diagnostic | Verify-fail and stop-reason behavior |

Full rubric: `evals/coordination/COORDINATION_VALIDATION_SUITE.md`

## Modes

| Mode | Description |
|------|-------------|
| **simulate** (default) | Deterministic envelope replay through `CoordinatorBridge` |
| **live** | Existing eval runners where linked (e.g. CVW-04 → `run_mcp_eval_validation_form.py`) |

## Files

| Path | Purpose |
|------|---------|
| `workflows.yaml` | 14 workflow definitions |
| `metrics_schema.json` | Per-workflow metrics shape |
| `report_schema.json` | Suite report shape |
| `src/coordination_validation/` | Harness, recorder, scorer |
| `src/run_coordination_validation.py` | CLI runner |

## On failure only

1. Identify failing CVW from report.
2. Trace `decisions[]` and `findings`.
3. Classify: validation expectation · artifact · coordinator.
4. One smallest change → re-run suite → compare `score_history.jsonl`.
5. Log in `evals/coordination/refinement_log.md`.

**Do not** tune artifacts or coordinator code when all workflows pass.

See `coordination_layer/RELEASE.md` for full change policy.
