# Decision Layer Lab

Improve coordination **without browsers**. Same YAML for interactive REPL, pack runs, and pytest.

## Quick start

```bash
# CI baseline (smoke + promoted experiments) — default
python scripts/decision_lab.py run
python scripts/decision_lab.py run -p baseline --scorecard evals/decision_lab/last_scorecard.json

# Fast smoke only
python scripts/decision_lab.py run -p smoke

# One scenario
python scripts/decision_lab.py run -s evals/decision_lab/scenarios/02_settings_surface.yaml

# Interactive
python scripts/decision_lab.py repl -i "redesign workspace settings"

# Pytest
python -m pytest tests/decision_lab/ -q
```

## Packs

| Pack | Path | Contents |
|------|------|----------|
| `baseline` | `packs/baseline.yaml` | Smoke + promoted EXP locks (**17** scenarios) |
| `smoke` | `packs/smoke.yaml` | Original 6 only |

Experiments live under `experiments/EXP-NNN-*/` with reports; wins get promoted into `baseline.yaml`.

## Session loop

1. Hypothesis in a new `experiments/EXP-NNN-*/README.md`  
2. Scenario + pytest  
3. Tweak coordination  
4. `python scripts/decision_lab.py run` (baseline) until green  
5. Promote scenario into `packs/baseline.yaml` when stable  

No real MCP tools — envelopes only.
