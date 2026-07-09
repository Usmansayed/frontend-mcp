from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.codeGraph.interface import GraphQueryResult, ICodeGraph


@dataclass(slots=True)
class NavigationHint:
    task: str
    summary: str
    hits: list[dict[str, Any]] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    route_files: list[str] = field(default_factory=list)
    ok: bool = False


class GraphHintResolver:
    """Resolve optional navigation hints from ICodeGraph without coupling Browser Use to CRG."""

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "to", "as", "in", "on", "for", "open",
        "navigate", "locate", "complete", "continue", "flow", "changes", "save",
        "with", "from", "into", "then", "that", "this", "your", "user",
    }

    def __init__(self, code_graph: ICodeGraph | None) -> None:
        self.code_graph = code_graph

    @classmethod
    def extract_keywords(cls, task: str) -> list[str]:
        words = [w.strip(".,!?").lower() for w in task.split()]
        return [w for w in words if w not in cls.STOP_WORDS and len(w) > 2]

    NAV_PRIORITY = ("checkout", "cart", "login", "admin", "settings", "shop", "profile", "payment", "shipping")

    def resolve(self, task: str) -> NavigationHint:
        if self.code_graph is None:
            return NavigationHint(task=task, summary="Graph unavailable", ok=False)

        hits: list[dict[str, Any]] = []
        related_files: list[str] = []
        route_files: list[str] = []
        summary = "No graph hints found"
        keywords = self.extract_keywords(task)
        priority = [k for k in self.NAV_PRIORITY if k in keywords]
        search_order = priority + [k for k in keywords if k not in priority]

        hint = self.code_graph.find_navigation_hint(task)
        if hint.ok and (hint.payload or {}).get("results"):
            hits = list(hint.payload["results"])
            summary = hint.summary

        if not hits:
            for kw in search_order:
                result = self.code_graph.search(kw, limit=5)
                if result.ok and (result.payload or {}).get("results"):
                    for item in result.payload["results"]:
                        if item not in hits:
                            hits.append(item)
                    summary = result.summary
                    if kw in self.NAV_PRIORITY:
                        break

        if not hits:
            for kw in search_order[:2]:
                result = self.code_graph.find_entry_point(kw)
                if result.ok and (result.payload or {}).get("results"):
                    hits = list(result.payload["results"])
                    summary = result.summary
                    break

        for kw in search_order[:3]:
            related = self.code_graph.find_related_files(kw)
            if related.ok:
                for item in (related.payload or {}).get("results") or []:
                    fp = item.get("file_path") or item.get("name")
                    if fp and fp not in related_files:
                        related_files.append(fp)

        keywords = self.extract_keywords(task)
        if {"checkout", "cart", "shop"} & set(keywords):
            route = self.code_graph.get_route(
                changed_files=[
                    "src/pages/shop/Cart.jsx",
                    "src/pages/shop/checkout/ShippingStep.jsx",
                ],
            )
            if route.ok:
                route_files = list((route.payload or {}).get("impacted_files") or [])[:8]

        return NavigationHint(
            task=task,
            summary=summary,
            hits=hits[:8],
            related_files=related_files[:8],
            route_files=route_files,
            ok=bool(hits or related_files or route_files),
        )


def format_hints_for_agent(hint: NavigationHint, start_url: str) -> str:
    """Turn graph hints into advisory context for Browser Use's extend_system_message."""
    if not hint.ok:
        return (
            "## Code graph hints\n"
            "No codebase hints are available for this task. Rely on the live page only.\n"
            f"Start URL: {start_url}\n"
        )

    lines = [
        "## Code graph hints (advisory only)",
        "These come from a static code graph. Prefer what you see in the browser if they conflict.",
        f"Start URL: {start_url}",
        f"Graph summary: {hint.summary}",
        "",
    ]

    if hint.hits:
        lines.append("Relevant code entities:")
        for item in hint.hits:
            name = item.get("name") or item.get("qualified_name") or "unknown"
            fp = item.get("file_path") or item.get("file") or ""
            kind = item.get("kind") or ""
            suffix = f" ({fp})" if fp else ""
            lines.append(f"- {name}{' [' + kind + ']' if kind else ''}{suffix}")

    if hint.related_files:
        lines.append("")
        lines.append("Related files:")
        for fp in hint.related_files:
            lines.append(f"- {fp}")

    if hint.route_files:
        lines.append("")
        lines.append("Likely route / impact files for shop-checkout flow:")
        for fp in hint.route_files:
            lines.append(f"- {fp}")

    lines.append("")
    lines.append("Use breadcrumbs, navbar links, buttons, and forms visible on the page.")
    return "\n".join(lines)


def hint_to_step_details(hint: NavigationHint, raw: GraphQueryResult | None = None) -> dict[str, Any]:
    return {
        "ok": hint.ok,
        "summary": hint.summary,
        "error": raw.error if raw else None,
        "hits": len(hint.hits),
        "top_hit": (hint.hits[0].get("name") if hint.hits else None),
        "related_files": hint.related_files[:3],
        "route_files": hint.route_files[:3],
    }
