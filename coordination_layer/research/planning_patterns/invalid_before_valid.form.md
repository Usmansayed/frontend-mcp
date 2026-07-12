# Planning Pattern — Invalid before Valid (Forms)

Canonical form-verification pattern (AGENT_GUIDE §4).

## Signature

- **Applies to states in:** cluster.feature.form_pipeline.
- **Preconditions:** form spec inferable via `probe_form`, session_id available.

## Steps

1. **probe_form_rules** — enumerate expected fields and validation.
2. **run_invalid_submit_check** — submit invalid; verify error UI matches expected predicates.
3. **run_valid_submit_check** — submit valid; verify success predicates.
4. **capture_regression_baseline** (optional).

## Why in this order

Invalid path exercises the validation logic directly; a valid path that "just works" without validation gating is not evidence that validation exists. Running invalid first prevents false positives.

## Recovery rules

- If invalid path passes when it should fail → validation missing → back to S05 with the fix.
- If valid path fails → probe form rules again, then S05 fix.

## States that embed this pattern

- saas.S05.new_feature.form_validation.v1
- saas.S07.new_feature.form_validation.invalid_path_verified
- saas.S07.new_feature.form_validation.verified

## Coordination implications

- Planner must **sequence** invalid before valid; cannot parallelize.
- probe_form → invalid → valid → verify sits well within one 3–5 retry budget when the form is well-formed.
