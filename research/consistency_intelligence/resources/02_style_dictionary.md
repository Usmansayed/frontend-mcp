# Research: Style Dictionary

**Repository:** [amzn/style-dictionary](https://github.com/amzn/style-dictionary)  
**Docs:** https://styledictionary.com/  
**Local clone:** `research/consistency_intelligence/repos/style-dictionary/`

---

## What problem does it solve?

Design tokens are defined once but must exist on many platforms (CSS, iOS, Android, SCSS, JS). Style Dictionary is a **build-time translation engine**: JSON tokens → platform-specific outputs via transforms, formats, and reference resolution.

**Our parallel:** We should **not** rebuild token export. We should **ingest** token definitions in SD/DTCG format and understand reference graphs when validating consistency.

---

## How does it work internally?

### Build pipeline

```text
config.json (source globs, platforms, hooks)
        │
        ▼
loadFile → combineJSON (merge token files)
        │
        ▼
detectDtcgSyntax → preprocess → expandObjectTokens
        │
        ▼
resolveReferences (alias chains, circular detection)
        │
        ▼
transformMap (per-platform transforms, deferred refs)
        │
        ▼
filterTokens → format (SCSS, CSS, JSON, etc.)
        │
        ▼
performActions (copy assets, etc.)
```

### Core class: `StyleDictionary`

Extends `Register` — hooks for custom parsers, transforms, formats, filters, actions.

Key methods:
- `extend(config)` — merge config
- `buildAllPlatforms()` / `buildPlatform(name)`
- Token dictionary: `tokens`, `allTokens`, `tokenMap`

### Reference resolution (`lib/utils/references/`)

- Syntax: `{color.primary}` or DTCG `$value: "{color.primary}"`
- `resolveReferences()` — inline substitution with circular ref detection
- `getPathFromName`, `getValueByPath` — dot-path traversal
- Supports partial references: `"1px solid {color.border.light}"`

### Transforms (`lib/transform/`)

- Per-token transforms: name, value, attribute
- Transform groups: `scss`, `css`, `js`, etc.
- Deferred transforms when value contains unresolved refs

### Data structures

```typescript
interface DesignToken {
  value?: any;      // legacy
  $value?: any;     // DTCG
  $type?: string;
  key?: string;     // "{colors.red.500}"
  path?: string[];
  original?: DesignToken;
  filePath?: string;
}

interface Dictionary {
  tokens: TransformedTokens;
  allTokens: TransformedToken[];
  tokenMap: Map<string, TransformedToken>;
}
```

`flattenTokens()` walks nested JSON → flat array with `{group.sub.token}` keys.

---

## Algorithms worth borrowing

| Idea | Application |
|------|-------------|
| **Nested token tree → flat map** | Project Design Graph token index |
| **Reference resolution with cycles** | Alias chains in declared tokens |
| **Platform transforms as views** | Same graph → CSS vars, Tailwind, etc. |
| **Hooks/filters** | Framework-specific token loaders (Tailwind config, CSS :root) |
| **Collision warnings** | Detect duplicate values under different names (fragmentation) |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Build-time only | We need **runtime** DOM validation |
| No learning | SD doesn't discover conventions from implementation |
| No confidence | Binary: token exists or not |
| Output-focused | We need **ingest + graph**, not code generation |

---

## Fit in our MCP architecture

Style Dictionary is a **provider adapter**, not our engine:

```text
Codebase Intelligence
        │
        ▼
Token Ingestion Layer
  ├── style-dictionary JSON (DTCG)
  ├── CSS :root variables
  ├── Tailwind theme
  └── Figma export (via Tokens Studio)
        │
        ▼
Normalized Token Graph (DTCG-compatible internal model)
        │
        ▼
Project Design Graph.tokens
```

**Dependency:** Use `@dtcg/schemas` for validation. Optionally wrap SD's reference resolver logic (study, don't fork blindly).

Do **not** reinvent token file parsing. Do **not** become a build tool.
