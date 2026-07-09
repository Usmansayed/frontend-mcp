from __future__ import annotations

import asyncio
from pathlib import Path

from navigation.visual_browser_intelligence.agent import PerceptionAgentRunner
from navigation.codebase_intelligence.graph import create_code_graph

SANDBOX = Path(__file__).resolve().parent.parent / "sandbox"


def run_demo() -> None:
    code_graph = create_code_graph(repo_root=SANDBOX, enabled=True)
    task = "Locate checkout button and continue flow"

    print("=== Dry-run timeline (BrowserUseNavigator) ===")
    from navigation.visual_browser_intelligence.agent import BrowserUseNavigator

    for step in BrowserUseNavigator(code_graph).execute(task):
        print(f"  {step.action} -> {step.details}")

    print("\n=== Graph hint preview for live agent ===")
    runner = PerceptionAgentRunner(code_graph=code_graph, start_url="http://localhost:5173")
    hint = runner.hint_resolver.resolve(task)
    from navigation.visual_browser_intelligence.agent import format_hints_for_agent

    print(format_hints_for_agent(hint, runner.start_url))

    print("\n=== Live agent (requires AWS creds + sandbox running) ===")
    print("Run: python src/run_agent.py --task", repr(task))


if __name__ == "__main__":
    run_demo()
