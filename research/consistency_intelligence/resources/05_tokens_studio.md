# Research: Tokens Studio

**Product:** https://tokens.studio/  
**Docs:** https://docs.tokens.studio/  
**Open source:** Figma plugin + Studio platform

---

## What problem does it solve?

Large teams need **token hierarchy**, **design↔code sync**, and **multi-platform export** without vendor lock-in. Tokens Studio bridges Figma/Penpot ↔ GitHub ↔ Style Dictionary.

---

## How it works (architecture, from product surface)

### Token hierarchy

```text
Primitive tokens (raw values)
        │
        ▼
Semantic tokens (role-based: color.text.primary)
        │
        ▼
Component tokens (button.primary.background)
```

Three-tier model is industry standard (also seen in DesignSystems.one, Carbon, etc.).

### Workflows

| Workflow | Description |
|----------|-------------|
| **Figma/Penpot plugin** | Edit tokens in design tool |
| **Studio platform** | Central management, automation |
| **Git sync** | Push/pull token JSON to repository |
| **Style Dictionary export** | Generate CSS, iOS, Android via SD |
| **CLI/SDK** | Custom integrations |

### Key principles

- **Open by default** — no proprietary format (aligns with DTCG)
- **Tool agnostic** — Figma, Penpot, GitHub, VS Code, Framer
- **Automation** — reduce manual sync between design and code

---

## Data structures (typical export)

Tokens Studio exports JSON compatible with Style Dictionary / DTCG:

```json
{
  "global": {
    "spacing": {
      "4": { "value": "4px", "type": "spacing" }
    }
  },
  "semantic": {
    "color": {
      "background": {
        "primary": { "value": "{global.color.white}", "type": "color" }
      }
    }
  }
}
```

Sets, themes, and responsive modes add dimensions to the graph.

---

## What to borrow

| Idea | Application |
|------|-------------|
| **Primitive → semantic → component tiers** | Project Design Graph layers |
| **Theme/mode as dimension** | dark/light variants in graph |
| **Git as source of truth** | Codebase Intelligence ingests from repo |
| **SD as export, not storage** | We ingest, don't build |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Design-tool centric | Our primary input is **live DOM + code** |
| Subscription platform | We're an MCP engine, not SaaS |
| Manual token authoring | We **discover** when declarations missing |

---

## Fit in our MCP architecture

Tokens Studio is a **future provider** for declared tokens:

```text
Design Workflow Intelligence (future)
        │
        ▼
providers/tokens_studio/  OR  providers/figma_tokens/
        │
        ▼
Declared Token Graph (DTCG-normalized)
        │
        ▼
compare vs Learned Standards vs Live DOM
```

For v1, prioritize **code + DOM discovery** over Figma sync. Tokens Studio informs **how to structure** the Project Design Graph hierarchy.
