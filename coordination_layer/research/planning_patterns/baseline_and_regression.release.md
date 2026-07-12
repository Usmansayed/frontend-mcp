# Planning Pattern — Baseline → Verify → Diff (Release / Regression)

Release-time regression discipline.

## Signature

- **Applies to states in:** cluster.release.baseline_and_staging, cluster.production.live_and_incidents.
- **Preconditions:** functional verification passed for target pages.

## Steps

1. **capture baseline** — scans + snapshots for target pages.
2. **stage / deploy** — release pipeline external to MCP.
3. **verify staging** — session_start against staging URL; iterate pages.
4. **diff vs baseline** — accept, reject, or mark regression.
5. **sign off** — human gate.

## Recovery rules

- Baseline stale → recapture before diffing.
- Diff shows regression → hand off to F05 (debug); do not sign off.
- Env misconfig → global.Sxx.env_misconfigured; fix before verify.

## States that embed this pattern

- marketing.S10.release_prep.regression_baseline_capture → baseline_stored → staging_verify → staging_verified

## Coordination implications

- Baselines have TTLs; planner tracks freshness (see `baseline_stale`).
- Sign-off is always a human gate; planner blocks on it.
