# Implementation Plan — R12 Situation Policy + Engineering Investment

**Status:** Implemented (2026-07-14)  
**Date:** 2026-07-14  
**Constraints:** No new MCP tools, no new architecture layers, fully backward compatible.

## Mapping research → code

| Research piece | Target | Change |
|----------------|--------|--------|
| R12 Situation Policy Catalog | `coordination_layer/runtime/situation_policy_catalog.v1.yaml` + `distillation/sources/` + bundled `artifacts/runtime/` | New artifact; load in `RuntimeArtifactBundle` |
| Discriminators | `planning/situation_policy.py` + PSM `episode.retry_counters` | Additive; no schema break |
| Lifecycle investment bands | `ClusterResolver._infer_lifecycle_stage` + policy matcher | Richer stage inference; band→budget |
| EQG / ROI / DR / STOP | `planning/effort_allocator.py` called from `CoordinationIntelligenceService._refresh_briefing` | Gate suggestions; stop reasons |
| Briefing rationale | `BriefingState` + `CoordinatorBriefing` + envelope enrich | Additive JSON fields |
| Evidence reuse | Existing `_maybe_advance_cached_observe` + cost=0 for satisfied evidence | Extended in allocator |

## Stages

1. **R12 YAML + loader** — load optional if missing (compat) ✅
2. **Models + EffortState** — optional fields default empty ✅
3. **situation_policy + effort_allocator** — pure functions ✅
4. **Wire service briefing** — apply ROI gate after compile ✅
5. **Lifecycle inference improve** — design-evidence → S03, etc. ✅
6. **Tests + regression suites** ✅

## Non-goals

- Matching `landing.S03.*` leaf IDs at runtime
- Mandatory tool rejection
- New playbooks unless policy Preference is advisory only (keep current playbooks)
