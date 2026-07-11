# Research: OverlayQA Design System Audit

**Product:** https://overlayqa.com/  
**Workflow:** https://overlayqa.com/workflows/design-system-audit/  
**Drift study:** https://overlayqa.com/blog/design-token-drift-study/ (375 sites)

---

## What problem does it solve?

Design systems **degrade in production**. Tokens get hardcoded, spacing drifts, interactive states go missing. Manual audits don't scale. OverlayQA automates inspection of **live builds**.

---

## How does it work (methodology)

### Audit pipeline

```text
Live URL (staging or production)
        │
        ▼
Browser capture → computed CSS per element
        │
        ▼
Token inspector
  - off-scale spacing (between token values)
  - orphan font sizes (not in type scale)
  - near-duplicate colors/shadows
  - inconsistent border radius
        │
        ▼
Interactive state scan
  - missing hover, focus, disabled
        │
        ▼
Violation documentation
  - selector, property, expected vs actual
        │
        ▼
Export to Jira / Linear / Notion
```

### Optional Figma comparison

- Extract tokens from Figma frame (6 categories)
- Capture live screenshot
- AI visual diff → 0-100 similarity score
- **Note:** This is design-comparison, not convention-learning

### Drift study findings (benchmark context)

| Metric | Value |
|--------|-------|
| Sites audited | 375 |
| Avg token coverage | 40.4% |
| 90%+ coverage | 7.5% of sites |
| Hardcoded values | 47/site average |
| Component drift | 100% of sites, 5.3 types/site |

---

## Scoring methodology

| Tier | Coverage |
|------|----------|
| Excellent | 90%+ |
| Good | 60-89% |
| Poor | <40% (average) |

Dimensions:
- **Adoption** — component coverage, token compliance
- **Quality** — visual drift score, override frequency
- **Efficiency** — time saved (organizational, not our scope)

---

## What to borrow

| Idea | Application |
|------|-------------|
| **Computed CSS inspection** | We already have this via DesignSnapshot |
| **Off-scale detection** | Values between learned scale steps |
| **Orphan detection** | Values not in learned clusters |
| **Near-duplicate detection** | Fragmentation metric (TokenLens + OverlayQA) |
| **State completeness** | Missing hover/focus/disabled per component class |
| **Severity by impact** | Prioritize violations on primary components |
| **Structured export** | ConsistencyReport → agent + issue trackers |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| AI visual diff as core | Subjective; not our consistency mission |
| Figma-required | We work without design files |
| SaaS dependency | We're local MCP |
| Binary pass/fail | We need confidence + exceptions |

---

## Fit in our MCP architecture

OverlayQA validates our **Consistency Validator** design:

```text
DesignSnapshot (from Browser Intelligence)
        +
Project Design Graph (learned + declared)
        │
        ▼
Consistency Validator
  ├── off-scale spacing (OverlayQA-style)
  ├── orphan typography
  ├── near-duplicate colors
  ├── state completeness
  └── token coverage (TokenLens-style)
        │
        ▼
ConsistencyReport
  - violations with CSS context
  - coverage scores
  - severity
  - evidence
```

We overlap with OverlayQA on **deterministic CSS audit** but differentiate via **learned project norms** (NATURALIZE) when no declared tokens exist.
