# Inspiration Intelligence — Architecture

Public design inspiration orchestration. **Figma Intelligence** is a separate future module for the user's own Figma account.

## Flow

```text
Agent
  → Intent
  → Search Planner
  → Community Intelligence (query expansion)
  → Provider Manager (priority cascade + early stop)
  → Dribbble | Behance | Awwwards | SiteInspire | Godly | Land-book
  → Candidate Intelligence
  → Ranking
  → Selection Planner
  → Browser Intelligence (execution only)
  → Design Snapshot → Design Sense → Consistency → Reference Registry
  → Agent
```

## Provider priority

Search stops as soon as enough high-confidence candidates are found (default: 3 at score ≥ 0.55).

1. Dribbble — live discovery adapter
2. Behance — navigation knowledge only
3. Awwwards — navigation knowledge only
4. SiteInspire — navigation knowledge only
5. Godly — navigation knowledge only
6. Land-book — navigation knowledge only

## Separation from Figma Intelligence

| Module | Responsibility |
|--------|----------------|
| **Inspiration Intelligence** | Public inspiration sites, screenshots, reference patterns |
| **Figma Intelligence** | User Figma account, files, variables, Community duplication |

Browser automation is an **execution layer** only. Ranking, comparison, and evaluation stay in intelligence modules.

See `docs/providers/` for per-site navigation research.
