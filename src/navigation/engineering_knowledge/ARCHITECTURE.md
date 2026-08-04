# Engineering Knowledge (V1)

**Status:** Frozen architecture for Pareto decision Spec.

## Layers (do not collapse)

```text
Sources
  → DesignSnapshot          # ONLY place that measures DOM/CSS
  → Engineering Knowledge Compiler
  → FrontendEngineeringSpec # ONLY place that creates decisions
  → SpecDiff                # ONLY place that diffs Specs
  → Coordinator             # ONLY place that prioritizes
  → Host LLM                # rebuilds UI from Spec
```

## Responsibility law

| Actor | May | Must not |
|-------|-----|----------|
| DesignSnapshot | Measure facts | Invent decisions / critique |
| Knowledge Compiler | Create `EngineeringDecision` records | Re-measure DOM |
| SpecDiff | Compare Specs | Re-compile or prioritize |
| Coordinator | Prioritize via impact/importance/status | Compile Spec values |
| Inspiration / Figma / Component tools | Provide sources + provenance envelopes | Invent private engineering formats as primary host truth |

**Clarification:** Discovery/collect may still return URLs and assets. Those are provenance inputs. Host-facing engineering truth is Spec.

## V1 decision groups (frozen — no expansion until A/B proves need)

1. Layout  
2. Information Hierarchy  
3. Navigation Model  
4. Spacing System  
5. Typography  
6. Color System  
7. Component Foundation  
8. Visual Density  

Deferred (intentionally): motion, accessibility deep, interaction details, loading/empty, responsive strategy, etc.

## Impact weights

Catalog base `impact_weight` ∈ (0,1]. Coordinator / ROI use:
`status`, `importance`, `confidence`, `impact_weight`.

No third optimization system — weights live on decisions and feed existing Engineering Investment.

## Success criterion

Not schema size. Host plans and builds differently because Spec contains high-value deterministic decisions.

## Phase 3 adapters

| Source | Adapter | Notes |
|--------|---------|-------|
| Live DOM | `compile_live_spec(snapshot)` | Full measurement path |
| Reference snapshot | `compile_reference_spec` / `compile_from_snapshot_dict` | Design Review SpecDiff |
| Inspiration collect | `compile_inspiration_seed_spec` | Soft priors only; geometry unresolved |
| Figma context | `compile_figma_seed_spec` | Token/font/frame priors; verify via Snapshot |

Design Review primary host artifact: `engineering_delta` (SpecDiff). English report is secondary.

A/B harness: `python -m evals.engineering_spec_ab.run`
