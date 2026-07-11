# Design Snapshot Engine

**Responsibility:** Observe, extract, normalize, and measure. **Never critiques.**

## Position in the stack

```text
Browser Intelligence (raw DOM, a11y, screenshots, runtime)
        │
        ▼
Design Snapshot Engine  ← this module
        │
        ▼
Structured DesignSnapshot
        │
        ├── Design Sense Intelligence (reasoning only)
        ├── Consistency Intelligence
        ├── Component Intelligence
        ├── Accessibility Intelligence
        └── Future modules
```

## Extractors (independently testable)

| Extractor | Output section |
|-----------|----------------|
| TypographyExtractor | `typography` |
| SpacingExtractor | `spacing` |
| ColorExtractor | `colors` |
| LayoutExtractor | `layout` |
| GridExtractor | `grid` |
| HierarchyExtractor | `hierarchy` |
| ComponentExtractor | `components` |
| MotionExtractor | `motion` |
| AccessibilityExtractor | `accessibility` |
| DesignTokenExtractor | `design_tokens` |

## External research

**designlang** (MIT, npm) — Playwright DOM walker, 17+ extractors, DTCG tokens, WCAG.
Optional augment via `integrations/designlang.py` when `DESIGNLANG_ENABLED=1`.

Native Python extractors are the default path (no Node dependency).

## API

```python
from navigation.design_snapshot_engine import DesignSnapshotService

service = DesignSnapshotService()
snapshot = await service.capture(browser_session, observation=obs)
```

## Policy

- Extractors produce **facts** (`issues` in a section are measured signals, not UX critique).
- Intelligence modules consume `DesignSnapshot`; they do not parse raw DOM/CSS.
