# Planning Pattern — OBSERVE → REASON → ACT → VERIFY loop

The universal loop for any state that reaches into browser-grounded UI work.

## Signature

- **Applies to states in:** cluster.feature.*, cluster.debug.signal_class, cluster.consistency.audit_cycle, cluster.migration.framework_or_redesign.
- **Preconditions:** session_id available, dev server reachable.
- **Loop termination:** verify_success + blocking empty, OR retry budget exhausted.

## Steps (semantic)

1. **observe** — capture evidence for the current state. Produces `scan_id` or refreshed evidence.
2. **reason** — inspect `agent_summary.blocking`, DOM, dev insights; decide next act.
3. **act** — apply a change to the project (code edit, execute_script, execute_actions).
4. **verify** — check success criteria via observable predicates.

## Recovery rules

- If verify fails, return to observe with a fresh scan and run `diff` against the pre-act snapshot.
- Retry budget: 3–5 iterations depending on state confidence. Exceeding budget → `global.Sxx.verify_loop_exhausted`.
- Never claim done without a passing verify (AGENT_GUIDE hard rule).

## States that embed this pattern

- Every state with `verification_requirements` populated and `possible_actions` that mutate the project.

## Coordination implications

- The retry budget is a first-class planner parameter.
- The pre-act evidence is used to build a diff at verify-fail — the planner must retain the pre-act `scan_id`.
