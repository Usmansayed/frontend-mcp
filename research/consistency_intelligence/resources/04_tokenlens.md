# Research: TokenLens

**Product:** https://tokenlens.app/  
**Creator notes:** https://francescoimprota.com/2025/11/17/token-lens/  
**Related study:** [OverlayQA token drift study](https://overlayqa.com/blog/design-token-drift-study/) (375 sites)

---

## What problem does it solve?

Design token JSON files and CSS implementations **drift apart**. Teams define 40 color tokens but only 28 appear in CSS. Hardcoded `#hex` values proliferate. Nobody knows the "real source of truth."

TokenLens answers: **What percentage of CSS actually uses tokens? Where are hardcoded values? Which tokens are unused?**

---

## How does it work (inferred architecture)

TokenLens is a **browser-based static analyzer** — no install, no build step.

### Inputs

1. Design token definitions (JSON, multiple files)
2. CSS files (multiple files)

### Processing (inferred)

```text
Parse token JSON → token index by category (color, spacing, font, …)
        │
        ▼
Parse CSS → property declarations per selector
        │
        ▼
Map token types → CSS properties
  (color tokens → color, background-color, border-color, …)
  (spacing tokens → margin, padding, gap, …)
        │
        ▼
For each CSS value:
  - matches token reference? → used
  - matches resolved token value? → implicit use
  - raw hex/px? → hardcoded instance
        │
        ▼
Aggregate:
  - coverage % per category
  - unused token list
  - hardcoded instances (file, selector, property, value)
  - component breakdown (infer from class names)
```

### Outputs

| Metric | Meaning |
|--------|---------|
| Token coverage % | Declarations using tokens vs hardcoded |
| Unused tokens | Defined but never referenced |
| Hardcoded instances | Specific violations with location |
| Component breakdown | Worst offenders by selector/class |

### Future direction (from creator)

- **Churn** — how often tokens change across releases (stability signal)
- **Fragmentation** — near-duplicate tokens with tiny value differences

---

## Philosophy worth borrowing

| Principle | Our application |
|-----------|-----------------|
| **Flashlight, not gate** | Report facts; agent decides priority |
| **Shared vocabulary** | "23 hardcoded values in 8 files" beats "system isn't followed" |
| **Category-level coverage** | Score spacing, color, typography separately |
| **Designer-friendly output** | Not just JSON — human-readable report |
| **No account required** | MCP tool should work on any scan |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Static CSS only | We have live DOM via Browser Intelligence |
| No learning | Compares to **declared** tokens only, not learned norms |
| No confidence | Binary match/miss |
| No component graph | Class-name inference is shallow |

---

## Fit in our MCP architecture

TokenLens informs the **Consistency Validator** reporting layer:

```text
Declared Token Graph (DTCG)
        +
Observed Values (DesignSnapshot + computed styles)
        │
        ▼
Coverage Analyzer (TokenLens-style)
  - adoption rate
  - hardcoded detection
  - unused tokens
  - fragmentation (near-duplicates)
        │
        ▼
ConsistencyReport.coverage
```

When **no declared tokens exist**, skip declared-vs-CSS comparison and rely entirely on **Style Discovery** (NATURALIZE path).

OverlayQA's study (40.4% avg coverage, 7.5% at 90%+) sets realistic benchmarks for our coverage scoring.
