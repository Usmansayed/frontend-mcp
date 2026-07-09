from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.codeGraph.interface import ICodeGraph

from .hints import GraphHintResolver, hint_to_step_details


@dataclass(slots=True)
class BrowserUseStep:
    action: str
    details: dict[str, Any] = field(default_factory=dict)


class BrowserUseNavigator:
    """
    Lightweight orchestration timeline for tests and dry-runs.
    For real browser automation with Bedrock Nova, use PerceptionAgentRunner.
    """

    def __init__(self, code_graph: ICodeGraph | None = None) -> None:
        self.code_graph = code_graph
        self.timeline: list[BrowserUseStep] = []
        self.hint_resolver = GraphHintResolver(code_graph)

    def execute(self, task: str) -> list[BrowserUseStep]:
        self.timeline.append(BrowserUseStep(action="browser_use.start", details={"task": task}))

        hint = self.hint_resolver.resolve(task)
        self.timeline.append(BrowserUseStep(action="code_graph.query", details=hint_to_step_details(hint)))

        self.timeline.append(
            BrowserUseStep(
                action="browser_use.navigate",
                details={
                    "task": task,
                    "hint_used": hint.ok,
                    "mode": "dry_run",
                    "note": "Use PerceptionAgentRunner for live Browser Use + Bedrock",
                },
            )
        )
        self.timeline.append(BrowserUseStep(action="browser_use.continue", details={"status": "ok"}))
        return self.timeline
