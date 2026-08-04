# Engineering Spec A/B eval

Deterministic planning influence harness for FrontendEngineeringSpec V1.

## Goal

Show that high-impact Spec decisions change the host **implementation plan** compared to adjective-only planning.

Success is **not** schema size. Success is measurable influence gain.

## Run

```bash
# from repo root with PYTHONPATH=src (or installed package)
python -m evals.engineering_spec_ab.run
python -m evals.engineering_spec_ab.run --scenario saas_dashboard
```

Report: `evals/engineering_spec_ab/output/ab_report.json`

## Scenarios

| id | What it tests |
|----|----------------|
| `saas_dashboard` | Live Snapshot → Spec → plan cites sidebar/nav/type/color |
| `landing_seed` | Inspiration seed Spec soft priors change plan vs adjectives |
| `dashboard_drift` | SpecDiff detects sidebar width drift |

## Interpreting scores

- `score_without` — fraction of critical/high decisions reflected in adjective plan (should be low)
- `score_with` — fraction reflected when plan is Spec-driven (should be high)
- `influence_gain` — with − without; must clear scenario threshold

If `influence_gain` is weak: **do not expand the catalog**. Improve compiler resolution quality for existing V1 decisions.

## Real-world follow-up (manual)

After this harness passes:

1. Same task in Cursor **without** MCP
2. Same task **with** MCP 1.2.dev + `intent` + read `engineering_spec`
3. Compare plans and final UI against Spec fields
