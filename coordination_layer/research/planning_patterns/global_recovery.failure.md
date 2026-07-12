# Planning Pattern — Global Recovery

Every non-terminal state points to one or more `global.Sxx.*` failure states. Coordination Layer must handle each with a canonical recovery strategy.

## Signature

- **Applies to states in:** cluster.global.recovery.
- **Preconditions:** entered from any originating state.

## Recovery strategies (per global state)

| Global state | Strategy | Human-in-loop |
|--------------|----------|---------------|
| dev_server_down | health probe → single retry → hand back | maybe |
| auth_gate.requires_human | STOP; surface details | yes |
| figma_connect_failed | ask for new PAT; do not retry auto | yes |
| upstream_degraded | continue with degraded[] notes | no |
| verify_loop_exhausted | bundle evidence for user; pause | yes |
| tooling_broken | surface error; hand back | yes |
| pdg_refresh_failed | inspect error; retry once; else defer | maybe |
| session_lost | start new session; optionally state_restore | no |
| repo_unavailable | ask user for repo_root or proceed without repo modules | maybe |
| env_misconfigured | enumerate missing env; ask user | yes |
| user_abandoned | cleanup ephemeral sessions; pause | n/a |
| verify_success_terminal | report summary; end | no |

## Coordination implications

- Each state has one strategy — the planner does not re-derive on the fly.
- Human-in-loop signals are gates; automation must respect them.
- Cleanup happens in `user_abandoned` regardless of upstream cause.
