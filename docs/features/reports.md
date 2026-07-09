# Reports subsystem

**Status:** ✅ shipped (v0.7)  
**Module:** `src/navigation/reports/`

## Problem

Raw console logs and network dumps overwhelm agents. We need **structured reports** with consistent sections.

## Standard report sections

```
Summary
Blocking Issues
Warnings
Console          → console module
Network          → network module
Visual Problems  → visual_insights
Performance      → audits / metrics
Accessibility    → audit a11y
Suggested Fixes  → deterministic hints only (links to code_context)
Artifacts        → scan_ids, screenshots, HAR, lighthouse JSON
```

## Models

```python
@dataclass
class PerceptionReport:
    summary: str  # one-line factual summary assembled from counts
    blocking: list[str]
    warnings: list[str]
    console: dict | None
    network: dict | None
    visual: dict | None
    audits: dict[str, dict]
    verification: dict
    suggested_fixes: list[str]
    artifacts: list[dict]
    scan_id: str | None
    url: str
    mode: str  # debug | full | audit
    degraded: list[str]
```

No LLM-generated "suggested fixes" in server — only rule-based hints (e.g. "Console errors detected — use perception_console_get").

## Tools

| Tool | Behavior |
|------|----------|
| `perception_full_diagnosis` | Observe → console → network → a11y + performance audits → visual → verification → `PerceptionReport`. `run_audits=false` skips Lighthouse. |
| `perception_debug_mode` | Observe + console + network (no Lighthouse) |
| `perception_audit_mode` | All four Lighthouse categories on current or given URL |

## Integration with scans

- `perception_report` embedded in scan observation
- `artifacts/{session}/diagnosis/diagnosis.json` and `diagnosis.md`
- Resources: `perception://scan/{id}/diagnosis.json`, `perception://scan/{id}/diagnosis.md`

## Agent consumption

JSON first via `data.perception_report` and `data.agent_summary.diagnosis`; optional markdown resource for human readability.

## Related

- All `docs/features/*.md`
- [INTEGRATION_PLAN.md](../INTEGRATION_PLAN.md)
- [ADR-012](../design_decisions.md#adr-012-diagnosis-orchestrator-no-llm-in-server)
