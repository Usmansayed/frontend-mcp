# Decision Layer Lab — Design

**Date:** 2026-07-18  
**Status:** Approved for implementation  
**Mode:** Interactive lab + automated scenario pack (both)

## Goal

Improve Coordination Intelligence (strategy, gate, backlog, ship, residue, confidence) **without calling real MCP tools**. Feed fake/recorded envelopes into the **production** decision path; iterate until the scenario pack stays green.

## Non-goals

- Forking / copying the MCP codebase  
- Replacing live evidence-quality work (Inspiration / Snapshot / SpecDiff)  
- Expanding coordination features inside the lab — the lab evaluates and hardens what exists  
- LLM-as-agent in the loop (v1)

## Architecture

```text
Scenario pack (YAML)
        │
   ┌────┴────┐
   ▼         ▼
Interactive  Eval runner (pytest + CLI)
   │         │
   └────┬────┘
        ▼
 DecisionLayerLab
        ▼
 CoordinationIntelligenceService + make_envelope
        ▼
 Assert gate / next / backlog / confidence / prohibited
```

## Core API

- `start(intent, …)` → episode_id  
- `feed(tool, ok, data, …)` → enriched envelope + strategy snapshot  
- `snapshot()` → gate, backlog, confidence, next capability, surface_type  
- `expect(**assertions)` → raise on mismatch  
- `run_scenario(path|dict)` / `run_pack(dir)` → scorecard  

## Scenario format

```yaml
id: settings_surface_v1
intent: redesign workspace settings preferences
lifecycle_stage: S03_design
project_maturity: M1
feeds:
  - tool: perception_build_design_snapshot
    ok: true
    data: { … }
    expect:                    # optional checkpoint
      surface_type: settings_form
expect:                        # final
  gate.state: provisional|blocked|ready|…
  next_capability: …
  prohibited_contains: [claim_complete]
```

## Placement

- `src/navigation/coordination_intelligence/lab/`  
- `evals/decision_lab/scenarios/`  
- `tests/decision_lab/`  
- `scripts/decision_lab.py`  

## Success

- Hours of coordination iteration with no browser  
- Same YAML for interactive + CI  
- Hotfix never picks up design-scope gates  
- Pack fails when tunnel vision / wrong surface / thin clear / ritual evidence returns  
