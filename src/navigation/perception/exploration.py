"""Phase 4: CRG-guided exploration with live verification."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from navigation.browser_use.hints import GraphHintResolver
from navigation.codeGraph.interface import ICodeGraph

from .verification import SuccessCriteria, read_current_url, verify


@dataclass(slots=True)
class ExplorationStep:
    action: str
    detail: str
    url: str = ""

    def to_dict(self) -> dict:
        return {"action": self.action, "detail": self.detail, "url": self.url}


@dataclass(slots=True)
class ExplorationResult:
    goal: str
    ok: bool
    final_url: str
    steps: list[ExplorationStep] = field(default_factory=list)
    hint_summary: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "ok": self.ok,
            "final_url": self.final_url,
            "hint_summary": self.hint_summary,
            "steps": [s.to_dict() for s in self.steps],
            "error": self.error,
        }


async def explore_with_hints(
    session: Any,
    code_graph: ICodeGraph | None,
    goal: str,
    *,
    base_url: str,
    success: SuccessCriteria,
    candidate_paths: list[str] | None = None,
) -> ExplorationResult:
    """Use CRG hints to pick a path, navigate, verify — no blind agent loop."""
    steps: list[ExplorationStep] = []
    resolver = GraphHintResolver(code_graph)
    hint = resolver.resolve(goal)
    steps.append(ExplorationStep("crg.resolve", hint.summary, await read_current_url(session)))

    paths = list(candidate_paths or [])
    for kw in resolver.extract_keywords(goal):
        if kw not in paths:
            paths.append(f"/{kw}")

    # CRG-related file paths often mention edge-lab
    for fp in hint.related_files:
        if "edge" in fp.lower():
            paths.insert(0, "/edge-lab")

    if "/edge-lab" not in paths:
        paths.append("/edge-lab")

    b = base_url.rstrip("/")
    ok = False
    final_url = ""
    for path in paths:
        target = path if path.startswith("http") else f"{b}/{path.lstrip('/')}"
        try:
            await session.navigate_to(target)
            await asyncio.sleep(0.35)
            final_url = await read_current_url(session)
            steps.append(ExplorationStep("navigate", target, final_url))
            result = await verify(session, success)
            if result.ok:
                ok = True
                break
        except Exception as exc:
            steps.append(ExplorationStep("navigate.error", str(exc), await read_current_url(session)))

    if not ok:
        final_url = await read_current_url(session)

    return ExplorationResult(
        goal=goal,
        ok=ok,
        final_url=final_url,
        steps=steps,
        hint_summary=hint.summary,
        error=None if ok else "no candidate path verified",
    )
