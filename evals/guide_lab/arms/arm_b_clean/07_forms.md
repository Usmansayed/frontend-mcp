# Guide: Forms / Guards / Flows

## Use when
Form validation, auth gates, multi-step flows — not a marketing landing.

## Usually owe
1. Read strategy
2. `probe_form` / `probe_guards` / flow checkpoints
3. Verify data.verified=true (invalid then valid as needed)

## Skip
Greenfield inspiration tours unless the surface is actually new marketing UI.

## Done condition
Probe criteria covered; verify passed; auth requires_human → stop for user.
