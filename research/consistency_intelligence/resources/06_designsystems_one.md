# Research: DesignSystems.one

**Site:** https://www.designsystems.one/  
**Scope:** Gallery of 74 real-world design systems, foundations guides, free tools

---

## What problem does it solve?

Teams don't know how to **structure** a design system — what belongs in foundations vs components, how to organize tokens, how to scale. DesignSystems.one catalogs mature systems and distills patterns.

---

## Organizational model (synthesized from site)

### Foundations layer

| Foundation | Typical contents |
|------------|------------------|
| **Color** | Primitives, semantic roles, OKLCH scales |
| **Typography** | Type scale, families, weights, line heights |
| **Spacing** | 4pt/8pt grid, semantic spacing names |
| **Elevation** | Shadows, z-index |
| **Motion** | Duration, easing |
| **Accessibility** | Contrast, focus, touch targets |

### Components layer

- **Patterns** — button, input, card, nav (the "right ten")
- **Variants** — size, emphasis, state
- **Documentation** — usage, anatomy, do/don't

### Agent-Ready Index (2026)

Rates systems on signals for AI consumption:
- Token exposure
- Component API clarity
- Documentation structure
- MCP/agent compatibility

Top-rated: shadcn/ui, Ant Design, Carbon, Chakra — systems with **explicit tokens + composable components**.

---

## Project Design Graph influence

DesignSystems.one suggests our graph should mirror how **mature teams organize**, not how CSS happens to be written:

```text
Project Design Graph
├── foundations/
│   ├── color (primitives + semantic)
│   ├── typography (scale + families)
│   ├── spacing (scale)
│   ├── radius
│   ├── shadow
│   └── motion
├── components/
│   ├── button (variants, states, anatomy)
│   ├── input
│   └── ...
├── patterns/
│   ├── navbar.floating
│   └── form.validation
├── relationships/
│   ├── button → uses → spacing.4
│   └── card → contains → button
└── meta/
    ├── confidence
    └── exceptions
```

---

## What to borrow

| Idea | Application |
|------|-------------|
| **Foundations before components** | Discovery order: scales → components |
| **Semantic naming** | Learn roles (primary, muted) not just hex |
| **Variant × state matrix** | Component consistency = variant coverage |
| **Agent-ready checklist** | Expose graph in MCP-consumable format |
| **90-day playbook structure** | Phased implementation roadmap |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Prescriptive aesthetics | We learn per-project, not prescribe |
| Gallery comparison | Reference Registry handles cross-product comparison |
| Static documentation | We need live learned graph |

---

## Fit in our MCP architecture

DesignSystems.one defines the **ontology** for Project Design Graph node types and relationships. It does not provide algorithms — it provides **taxonomy**.

Component Intelligence queries: "What variants does this project's button have?"  
Design Sense queries: "Does hierarchy match learned patterns?" (secondary — DS owns consistency)
