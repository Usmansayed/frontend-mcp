# Design Sense Intelligence — Architecture v1 (FROZEN)

**Status:** Frozen contracts — improve implementations only behind interfaces.

## Position in stack (v2)

```text
Browser Intelligence → Design Snapshot Engine → DesignSnapshot
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    ▼                               ▼                               ▼
        Design Sense Intelligence      Consistency Intelligence        Component Intelligence
        (reasoning only)               (token/scale validation)        (guidance contracts)
```

Design Sense **must not** parse raw DOM/CSS. It consumes `ReviewRequest.design_snapshot` or legacy fields hydrated via `snapshot_access.enrich_request()`.

## Pipeline (do not reorder without ADR)

```text
ReviewRequest
      │
      ├─ OBJECTIVE LANE ─────────────────────────────┐
      │   reviewers: layout, typography, color, a11y   │
      │   providers: design_lint (WCAG future)         │
      │                                                │
      ├─ SUBJECTIVE LANE ────────────────────────────┤
      │   reviewers: hierarchy, nav, component, ux, motion │
      │   providers: open_design, microsoft, uicrit,       │
      │              design_knowledge, crit_rams             │
      │                                                │
      ▼                                                ▼
              ReasoningEngine.synthesize()
                      │
                      ▼
              ReviewCoordinator.merge()
                      │
                      ▼
              DesignReviewReport
```

## Module map (frozen)

| Package | Role | Change policy |
|---------|------|---------------|
| `providers/` | External + methodology adapters | Add providers; do not break `DesignSenseProvider` |
| `knowledge/` | First-class design knowledge | Expand content; keep `KnowledgeService.contribute()` |
| `rules/` | Objective Design Lint port | Add rules; keep `run_lint()` |
| `reviewers/` | Specialist critics | Add reviewers; keep `lane` + `review()` |
| `reasoning/` | Narrative synthesis | Deepen logic; keep `synthesize()` signature |
| `workflows/` | Microsoft + UICrit pipelines | Extend phases; keep entry functions |
| `learning/` | Feedback, examples, benchmarks | Append data; keep `LearningStore` |
| `heuristics/` | Browser runtime signals (observe) | Unchanged — not design knowledge |

## Contracts

- `DesignSenseProvider`: `name`, `kind`, `lane`, `contribute(request) → ProviderContribution`
- `SpecialistReviewer`: `name`, `category`, `lane`, `review(request) → findings`
- `ReasoningEngine`: `synthesize(objective, subjective, scores, knowledge_notes) → ReasoningResult`
- `ReviewCoordinator.run(request) → DesignReviewReport`
- `DesignSenseService.review(request) → DesignReviewReport`

## Policy

> From this point onward, only improve implementations behind the interfaces.  
> Do not redesign the module structure unless absolutely necessary (requires new ADR).
