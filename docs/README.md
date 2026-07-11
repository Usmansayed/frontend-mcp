# Frontend Perception MCP — Documentation

Platform docs for the ultimate frontend MCP for AI coding agents.

## Start here

| Doc | Description |
|-----|-------------|
| [architecture.md](./architecture.md) | System design, intelligence modules |
| [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md) | Intelligence module platform map |
| [INTEGRATION_PLAN.md](./INTEGRATION_PLAN.md) | BrowserTools study → our reimplementation plan |
| [roadmap.md](./roadmap.md) | Shipped, in-progress, planned versions |
| [PRODUCT_STORY.md](./PRODUCT_STORY.md) | Landing page copy, positioning, feature narrative |
| [TECHNICAL_NARRATIVE.md](./TECHNICAL_NARRATIVE.md) | How we build: pipelines, patterns, creative architecture (for technical landing sections) |
| [tool_reference.md](./tool_reference.md) | All MCP tools and parameters |
| [design_decisions.md](./design_decisions.md) | ADR log |

## Feature subsystems

| Doc | Status |
|-----|--------|
| [features/visual.md](./features/visual.md) | ✅ v0.2 |
| [features/verification.md](./features/verification.md) | ✅ |
| [features/flows.md](./features/flows.md) | ✅ |
| [features/console.md](./features/console.md) | ✅ v0.4 |
| [features/network.md](./features/network.md) | ✅ v0.5 |
| [features/audits.md](./features/audits.md) | ✅ v0.6 |
| [features/reports.md](./features/reports.md) | ✅ v0.7 |
| [features/framework_intelligence.md](./features/framework_intelligence.md) | ✅ v1.0 |
| [features/component_intelligence.md](./features/component_intelligence.md) | ✅ Phase 1 search |
| [features/component_intelligence_architecture.md](./features/component_intelligence_architecture.md) | 🚧 full orchestrator pipeline |
| [features/design_sense_intelligence.md](./features/design_sense_intelligence.md) | 🚧 review orchestration |
| [features/consistency_intelligence.md](./features/consistency_intelligence.md) | 📋 scaffold |
| [features/inspiration_intelligence.md](./features/inspiration_intelligence.md) | ✅ public gallery inspiration |
| [features/resource_intelligence.md](./features/resource_intelligence.md) | 📋 research & architecture |
| [features/figma_intelligence.md](./features/figma_intelligence.md) | 🚧 user Figma account scaffold |
| [features/comparison_browser_tools.md](./features/comparison_browser_tools.md) | Reference vs us |

## Agent playbooks

Runtime playbooks for host agents: [AGENT_GUIDE.md](../AGENT_GUIDE.md) (also MCP resource `perception://agent-guide`).

## References (study only)

[references/README.md](../references/README.md) — external clones, not dependencies.

## Contributing

When shipping a feature:

1. Update the matching `docs/features/*.md`
2. Update `roadmap.md` and `tool_reference.md` if tools change
3. Add ADR to `design_decisions.md` if architectural
