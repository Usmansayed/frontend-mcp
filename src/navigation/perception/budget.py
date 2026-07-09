"""Token/size budget for MCP-friendly observation output."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OutputBudget:
    max_a11y_chars: int = 4000
    max_dom_chars: int = 4000
    max_list_items: int = 30
    max_issue_items: int = 20

    def trim_text(self, text: str, limit: int | None = None) -> str:
        cap = limit if limit is not None else self.max_dom_chars
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n…[truncated {len(text) - cap} chars]"


def apply_dev_insights_budget(insights: Any, budget: OutputBudget) -> dict[str, Any]:
    """Serialize dev insights; always preserve summary issues, trim long lists."""
    raw = insights.to_dict()
    summary = raw.get("summary") or {}
    summary["blocking_issues"] = (summary.get("blocking_issues") or [])[: budget.max_issue_items]
    summary["advisory_issues"] = (summary.get("advisory_issues") or [])[: budget.max_issue_items]
    raw["summary"] = summary

    for key in (
        "console_errors",
        "console_warnings",
        "exceptions",
        "network_failures",
        "api_calls",
        "slow_requests",
        "ui_errors",
    ):
        if key in raw and isinstance(raw[key], list):
            raw[key] = raw[key][: budget.max_list_items]
    return raw


def apply_observation_budget(obs_dict: dict[str, Any], budget: OutputBudget) -> dict[str, Any]:
    out = dict(obs_dict)
    out["a11y_tree"] = budget.trim_text(str(out.get("a11y_tree") or ""), budget.max_a11y_chars)
    out["dom_text"] = budget.trim_text(str(out.get("dom_text") or ""), budget.max_dom_chars)
    if "dev_insights" in out and out["dev_insights"] is not None:
        # Re-wrap as simple namespace for apply_dev_insights_budget
        class _Wrap:
            def to_dict(self) -> dict[str, Any]:
                return out["dev_insights"]

        out["dev_insights"] = apply_dev_insights_budget(_Wrap(), budget)
    return out
