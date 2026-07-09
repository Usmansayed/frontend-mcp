from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.codebase_intelligence.graph.interface import ICodeGraph

from .hints import GraphHintResolver, NavigationHint, format_hints_for_agent, hint_to_step_details
from .integration import BrowserUseStep
from .llm import create_bedrock_llm, credentials_available


@dataclass(slots=True)
class AgentRunResult:
    task: str
    success: bool
    steps_taken: int
    final_result: str | None
    hint: NavigationHint
    timeline: list[BrowserUseStep] = field(default_factory=list)
    error: str | None = None

    def summary(self) -> str:
        lines = [
            f"Task: {self.task}",
            f"Success: {self.success}",
            f"Steps: {self.steps_taken}",
            f"Graph hints used: {self.hint.ok} ({len(self.hint.hits)} hits)",
        ]
        if self.final_result:
            lines.append(f"Result: {self.final_result[:500]}")
        if self.error:
            lines.append(f"Error: {self.error}")
        return "\n".join(lines)


class PerceptionAgentRunner:
    """
    Runs a real Browser Use agent with optional CRG navigation hints.

    Graph hints are injected via extend_system_message — never a hard pipeline stage.
    If the graph or Bedrock credentials are missing, the agent still attempts the task.
    """

    def __init__(
        self,
        code_graph: ICodeGraph | None = None,
        *,
        start_url: str | None = None,
        model: str | None = None,
        region: str | None = None,
        max_steps: int = 25,
        headless: bool = False,
        use_vision: bool = True,
    ) -> None:
        self.code_graph = code_graph
        self.start_url = start_url or os.getenv("SANDBOX_URL", "http://localhost:5173")
        self.model = model
        self.region = region
        self.max_steps = max_steps
        self.headless = headless
        self.use_vision = use_vision
        self.hint_resolver = GraphHintResolver(code_graph)
        self.timeline: list[BrowserUseStep] = []

    def _record(self, action: str, details: dict[str, Any]) -> None:
        self.timeline.append(BrowserUseStep(action=action, details=details))

    async def run(self, task: str) -> AgentRunResult:
        self.timeline = []
        self._record("browser_use.start", {"task": task, "start_url": self.start_url})

        hint = self.hint_resolver.resolve(task)
        self._record("code_graph.query", hint_to_step_details(hint))

        if not credentials_available():
            self._record("browser_use.skip", {"reason": "missing_aws_credentials"})
            return AgentRunResult(
                task=task,
                success=False,
                steps_taken=0,
                final_result=None,
                hint=hint,
                timeline=self.timeline,
                error="AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
            )

        try:
            from browser_use import Agent, BrowserProfile
        except ImportError as exc:
            return AgentRunResult(
                task=task,
                success=False,
                steps_taken=0,
                final_result=None,
                hint=hint,
                timeline=self.timeline,
                error=f"browser-use not installed: {exc}",
            )

        llm = create_bedrock_llm(model=self.model, region=self.region)
        graph_context = format_hints_for_agent(hint, self.start_url)

        full_task = (
            f"{task}\n\n"
            f"Open {self.start_url} first if you are not already on the Navigation Maze app."
        )

        profile = BrowserProfile(headless=self.headless)

        self._record(
            "browser_use.agent_init",
            {
                "model": self.model or os.getenv("BEDROCK_MODEL", "amazon.nova-pro-v1:0"),
                "hint_injected": hint.ok,
                "max_steps": self.max_steps,
            },
        )

        agent = Agent(
            task=full_task,
            llm=llm,
            browser_profile=profile,
            use_vision=self.use_vision,
            extend_system_message=graph_context,
            initial_actions=[{"navigate": {"url": self.start_url, "new_tab": False}}],
        )

        try:
            history = await agent.run(max_steps=self.max_steps)
            final = history.final_result()
            success = bool(history.is_successful())
            self._record(
                "browser_use.done",
                {
                    "success": success,
                    "steps": len(history.history),
                    "final_result": (final or "")[:300],
                },
            )
            return AgentRunResult(
                task=task,
                success=success,
                steps_taken=len(history.history),
                final_result=final,
                hint=hint,
                timeline=self.timeline,
            )
        except Exception as exc:
            self._record("browser_use.error", {"error": str(exc)})
            return AgentRunResult(
                task=task,
                success=False,
                steps_taken=len(self.timeline),
                final_result=None,
                hint=hint,
                timeline=self.timeline,
                error=str(exc),
            )

    def run_sync(self, task: str) -> AgentRunResult:
        return asyncio.run(self.run(task))
