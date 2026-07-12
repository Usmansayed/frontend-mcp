# Forest F12 — Global Failure & Recovery

**Root:** any stage. States are prefixed `global.*` and short-circuit into recovery paths.
**Target leaves:** ~10
**Archetype coverage:** all.

## Global failure surfaces

1. **`global.dev_server_down`** — health fails; block all browser-dependent modules until recovered.
2. **`global.auth_gate_requires_human`** — auth_gate returned `requires_human: true`; STOP.
3. **`global.figma_connect_failed`** — PAT invalid or expired; no retry loop.
4. **`global.upstream_degraded`** — third-party dependency (Lighthouse, LibreCrawl, GSC, docs provider) unavailable.
5. **`global.verify_loop_exhausted`** — max verify retries hit without success.
6. **`global.tooling_broken`** — Node/npm/build tooling fails.
7. **`global.pdg_refresh_failed`** — discovery pipeline could not build PDG.
8. **`global.session_lost`** — session_id invalid or browser closed unexpectedly.
9. **`global.repo_unavailable`** — repo_root missing or not readable.
10. **`global.env_misconfigured`** — required env vars absent (SEO pro, GSC).

## Recovery playbooks (referenced by state YAMLs)

- **health-recover:** wait/probe → re-issue health → if still down, hand back to user.
- **human-in-loop:** surface `auth_gate` output, STOP.
- **rotate-credentials:** ask user for new PAT/token; do not retry auto.
- **degrade-gracefully:** continue with `degraded[]` notes; skip affected steps.
- **verify-exhaust-escape:** re-observe with screenshot + diff → new hypothesis or human hand-off.
- **restart-session:** end + start new session; reuse state_save/restore if applicable.

## Design intent

Global states are **cross-cutting**. Every non-terminal state in F01–F11 declares one or more of these as its `failure_states`. This avoids duplicating error handling per forest and mirrors AGENT_GUIDE hard rules.
