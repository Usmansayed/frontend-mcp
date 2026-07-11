# Design Benchmark Suite

Gold-standard design reviews for measuring Design Sense Intelligence quality.

Every benchmark case includes:

| Artifact | File |
|----------|------|
| Manifest + inputs | `benchmark.json` |
| Expected findings | `benchmark.json` → `gold_findings` |
| Expected pass/fail | `benchmark.json` → `expected_score` |
| Gold review narrative | `benchmark.json` → `gold_review` |

Optional (future): `page.html`, `page.css`, `screenshot.png` captured from live URLs.

## Run evaluation

```bash
python tests/run_design_benchmark.py
```

Outputs:

- `tests/results/design_benchmark_report.json`
- `tests/results/design_benchmark_analysis.md`

## Categories

| Folder | Cases |
|--------|-------|
| `auth/` | Login flows |
| `ecommerce/` | Checkout, cart |
| `forms/` | Validation, wizards |
| `dashboards/` | Analytics, admin |
| `landing/` | Task-only / minimal input |
| `design_systems/` | Lint / token violations |
| `sandbox/` | Live sandbox app pages |

## Matching rules

Gold findings use `match` patterns (substring, case-insensitive) against actual `category`, `message`, and `id`.

- **required: true** — false negative if not matched
- **required: false** — bonus true positive if matched
- **gold_forbidden** — false positive if matched

## Policy

Do not add features until benchmark metrics improve. Re-run after every significant change.
