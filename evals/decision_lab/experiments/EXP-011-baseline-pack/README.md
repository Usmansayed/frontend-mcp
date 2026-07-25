## After

- `packs/baseline.yaml` + `packs/smoke.yaml`  
- `decision_lab run` defaults to **baseline** (16 scenarios)  
- pytest `test_baseline_pack` / `test_exp011_*` green  

## Verdict

**Win.** Experiment wins are now the CI source of truth, not orphan tests.
