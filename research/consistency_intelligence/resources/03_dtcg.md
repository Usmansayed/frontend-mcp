# Research: Design Tokens Community Group (DTCG)

**Repository:** [design-tokens/community-group](https://github.com/design-tokens/community-group)  
**Specification:** https://www.designtokens.org/  
**Format draft:** 2025.10  
**Local clone:** `research/consistency_intelligence/repos/community-group/schemas/`

---

## What problem does it solve?

Tool vendors (Figma, Penpot, Style Dictionary, Tokens Studio) each had proprietary token formats. DTCG defines a **vendor-neutral interchange format** so tokens flow between design and development without bespoke glue code.

---

## How does it work internally?

### Token anatomy (2025.10)

```json
{
  "color": {
    "text": {
      "primary": {
        "$type": "color",
        "$value": {
          "colorSpace": "srgb",
          "components": [0, 0, 0],
          "alpha": 1
        },
        "$description": "Primary body text"
      }
    }
  }
}
```

### Key concepts

| Concept | Description |
|---------|-------------|
| **Token** | Name + `$value` + optional `$type`, `$description`, `$extensions` |
| **Group** | Arbitrary nesting — tools must NOT infer type from group name |
| **Alias** | `$value: "{color.palette.black}"` — reference by path |
| **$ref** | JSON Pointer (RFC 6901) for property-level references |
| **Composite token** | Typography, shadow, border — multi-field `$value` |
| **Types** | color, dimension, fontFamily, fontWeight, duration, cubicBezier, border, shadow, typography, … |

### JSON Schemas (`schemas/src/2025.10/`)

- `format/token.json` — token structure, type-conditional `$value` schemas
- `format/values/color.json` — OKLCH, sRGB, lab, etc.
- `format/values/dimension.json` — `{value, unit}`
- `resolver.json` — reference resolution spec (separate from format)

Style Dictionary v4 detects DTCG via `detectDtcgSyntax()` and uses `$value`/`$type` delegates.

---

## Data structures for our internal model

Our `ProjectDesignGraph` token nodes should be **DTCG-compatible**:

```python
@dataclass
class DesignTokenNode:
    path: tuple[str, ...]          # ("color", "text", "primary")
    dtcg_type: str | None
    value: Any                     # resolved or reference
    raw_value: Any                 # before resolution
    description: str = ""
    extensions: dict = field(default_factory=dict)
    deprecated: bool | str = False
    source_file: str = ""
    resolved_value: Any | None = None  # after alias chain
```

---

## Algorithms worth borrowing

| Idea | Application |
|------|-------------|
| **Curly-brace alias syntax** | Unified reference format across tools |
| **Typed composite tokens** | Typography = font + size + lineHeight + color |
| **$extensions vendor fields** | MCP-specific metadata (confidence, learned vs declared) |
| **JSON Schema validation** | Validate ingested token files at boundary |
| **Separate resolver spec** | Reference resolution independent of storage |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Spec is draft-only (2025.10 preview) | Pin version; don't chase unstable draft |
| No learning/discovery | DTCG is declaration format, not observation |
| No component semantics | Tokens ≠ component variants |
| Groups are arbitrary | We add our own relationship layer |

---

## Fit in our MCP architecture

DTCG is the **wire format** for the token layer of Project Design Graph:

```text
Declared tokens (DTCG JSON, CSS vars, Tailwind)
        │
        ▼
DTCG-normalized Token Store
        │
        ├── compare against → Learned standards (Style Discovery)
        └── compare against → DOM computed values (Validator)
```

**Compatibility rule:** Any token we emit or ingest should validate against `@dtcg/schemas` where possible. Use `$extensions.perception` for engine-specific fields (confidence, evidence_count, exception_flag).
