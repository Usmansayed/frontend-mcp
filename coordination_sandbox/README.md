# Coordination Sandbox

**Isolated decision lab for Coordination Intelligence.**
Does **not** execute MCP tools. Does **not** import or modify production
`navigation.coordination_intelligence`, PSM runtime, or the shipping MCP.

Branch: `coordination-sandbox` (keep `main` / published MCP stable).

## Purpose

Tune the coordinator like an experienced frontend tech lead by watching
**engineering investment decisions**:

- How much budget it allocates
- When it enters design workflows
- When it suppresses expensive capabilities
- When it recommends STOP / diminishing returns
- How investment changes across lifecycle bands

Only after you are happy with sandbox decisions should you intentionally
port changes into production Coordination Intelligence.

## Layout

```
coordination_sandbox/
  brain/                  # VENDORED copies of coordination logic (tune here)
    situation_policy.py
    effort_allocator.py
    models.py             # minimal PSM for simulation
    playbook_plan.py      # sandbox candidate sequences (not MCP)
    catalog/              # R12 Situation Policy Catalog snapshot
  simulator/              # episode runner + reports
  scenarios/default.yaml  # prompt suite
  run.py                  # CLI
  output/                 # generated traces (gitignored)
```

## Run

From repo root (requires PyYAML):

```bash
# One prompt
python -m coordination_sandbox.run --prompt "Build a landing page"

# Full default suite (12 scenarios)
python -m coordination_sandbox.run --scenarios coordination_sandbox/scenarios/default.yaml

# Batch JSONL for hundreds of scenarios
python -m coordination_sandbox.run -s coordination_sandbox/scenarios/default.yaml --jsonl coordination_sandbox/output/batch.jsonl --quiet
```

Each run prints project state, lifecycle, situation policy, Engineering
Investment, visual impact, EQG, ROI, budget, playbook, recommended vs
skipped capabilities (with why), STOP / diminishing returns, and a full
decision trace. JSON copies land in `coordination_sandbox/output/<id>.json`.

## Isolation guarantees

| Area | Touched? |
|------|----------|
| Production Coordination Intelligence | No |
| Production PSM / Execution Runtime | No |
| Production MCP tools / server | No |
| PyPI package behavior | No |

## Sync from production (manual)

```bash
cp src/navigation/coordination_intelligence/planning/situation_policy.py coordination_sandbox/brain/
cp src/navigation/coordination_intelligence/planning/effort_allocator.py coordination_sandbox/brain/
# Then rewrite imports to coordination_sandbox.brain.*
cp coordination_layer/runtime/situation_policy_catalog.v1.yaml coordination_sandbox/brain/catalog/
```

## What "good" looks like

| Prompt | Expect |
|--------|--------|
| Fix one button / Improve spacing | Surgical, low budget, inspiration skipped |
| Production hotfix | Design workflows suppressed |
| Build a landing page | Design-driven early investment |
| Improve this existing dashboard | Mid incremental, not greenfield inspiration |
| Replace the component library | System-setup / foundations investment |
