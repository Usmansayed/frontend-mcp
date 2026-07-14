"""Phase 3: run verified checkpoints (deterministic + scripted for now)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from navigation.design_workflow_intelligence.flows.flow_graph import Checkpoint, FlowGraph
from navigation.component_intelligence.probes.form_probe import _fill_validation_form
from navigation.visual_browser_intelligence.actions.scripted_actions import click_button_text
from navigation.visual_browser_intelligence.verify.verification import SuccessCriteria, read_current_url, verify


@dataclass(slots=True)
class CheckpointResult:
    name: str
    ok: bool
    mode: str
    url: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "mode": self.mode,
            "url": self.url,
            "reasons": self.reasons,
        }


@dataclass(slots=True)
class FlowRunResult:
    flow: str
    ok: bool
    checkpoints: list[CheckpointResult] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "flow": self.flow,
            "ok": self.ok,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "error": self.error,
        }


class FlowRunner:
    def __init__(self, base_url: str = "http://localhost:5173", *, headless: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.headless = headless

    def _abs(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    async def _run_deterministic(self, session: Any, cp: Checkpoint) -> CheckpointResult:
        await session.navigate_to(self._abs(cp.navigate_url or ""))
        await asyncio.sleep(0.3)
        result = await verify(session, cp.success)
        return CheckpointResult(
            cp.name, result.ok, "deterministic", result.url, reasons=result.reasons
        )

    async def _run_validation_scripted(self, session: Any, cp: Checkpoint) -> CheckpointResult:
        if cp.name == "submit-empty":
            if cp.ensure_url:
                await session.navigate_to(self._abs(cp.ensure_url))
                await asyncio.sleep(0.2)
            await click_button_text(session, "Validate & submit")
            await asyncio.sleep(0.3)
        elif cp.name == "submit-valid":
            if cp.ensure_url:
                await session.navigate_to(self._abs(cp.ensure_url))
                await asyncio.sleep(0.2)
            await _fill_validation_form(session)
            await click_button_text(session, "Validate & submit")
            await asyncio.sleep(0.3)
        else:
            return CheckpointResult(cp.name, False, "scripted", await read_current_url(session), ["unknown checkpoint"])

        result = await verify(session, cp.success)
        return CheckpointResult(cp.name, result.ok, "scripted", result.url, reasons=result.reasons)

    async def _run_shop_scripted(self, session: Any, cp: Checkpoint) -> CheckpointResult:
        from navigation.visual_browser_intelligence.actions.scripted_actions import set_input_by_label

        if cp.name == "checkout-to-confirmation":
            await click_button_text(session, "Buy now")
            await asyncio.sleep(0.4)
            await click_button_text(session, "Checkout")
            await asyncio.sleep(0.4)
            await set_input_by_label(session, "Full name", "John Doe")
            await set_input_by_label(session, "Address", "123 Main St")
            await set_input_by_label(session, "City", "Anytown")
            await click_button_text(session, "Continue to payment")
            await asyncio.sleep(0.4)
            await set_input_by_label(session, "Card number", "4242424242424242")
            await click_button_text(session, "Review order")
            await asyncio.sleep(0.4)
            await click_button_text(session, "Place order")
            await asyncio.sleep(0.4)

        result = await verify(session, cp.success)
        return CheckpointResult(cp.name, result.ok, "scripted", result.url, reasons=result.reasons)

    async def run_flow(self, flow: FlowGraph) -> FlowRunResult:
        from navigation.visual_browser_intelligence.browser.browser_session_manager import (
            BrowserSessionManager,
        )

        manager = BrowserSessionManager.get()
        results: list[CheckpointResult] = []
        managed = None
        try:
            managed = await manager.acquire(
                base_url=self.base_url,
                headless=self.headless,
                viewport_width=1920,
                viewport_height=1080,
            )
            session = managed.browser
            await session.navigate_to(self.base_url)

            for cp in flow.checkpoints:
                if cp.is_deterministic:
                    res = await self._run_deterministic(session, cp)
                elif flow.name == "validation-form":
                    res = await self._run_validation_scripted(session, cp)
                elif flow.name == "shop-order":
                    res = await self._run_shop_scripted(session, cp)
                else:
                    res = CheckpointResult(cp.name, False, "unsupported", await read_current_url(session), ["no runner"])
                results.append(res)
                if not res.ok:
                    break
        except Exception as exc:
            return FlowRunResult(flow.name, False, results, error=str(exc))
        finally:
            if managed is not None:
                try:
                    await manager.release(
                        isolated=managed.isolated,
                        lease_id=managed.lease_id,
                    )
                except Exception:
                    pass

        ok = bool(results) and all(r.ok for r in results)
        return FlowRunResult(flow.name, ok, results)
