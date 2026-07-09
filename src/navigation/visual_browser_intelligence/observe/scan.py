"""Unified page scan — single entry point for MCP and agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.core.budget import OutputBudget, apply_observation_budget
from navigation.visual_browser_intelligence.observe.observation import PageObservation, collect_observation
from navigation.visual_browser_intelligence.observe.preflight import PreflightResult, preflight_check


@dataclass(slots=True)
class ScanResult:
    ok: bool
    url: str
    observation: PageObservation | None = None
    preflight: PreflightResult | None = None
    degraded: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self, *, budget: OutputBudget | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "url": self.url,
            "error": self.error,
            "degraded": list(self.degraded),
        }
        if self.preflight is not None:
            out["preflight"] = self.preflight.to_dict()
        if self.observation is not None:
            obs = self.observation.to_dict()
            if budget is not None:
                obs = apply_observation_budget(obs, budget)
            out["observation"] = obs
        return out


async def scan_page(
    session: Any,
    url: str,
    *,
    images_dir: Path | None = None,
    name: str = "scan",
    budget: OutputBudget | None = None,
    ready_timeout: float = 15.0,
    screenshot_mode: str = "viewport",
    screenshot_selector: str | None = None,
    annotate_screenshot: bool = True,
    console_service: Any | None = None,
    network_service: Any | None = None,
    har_dir: Path | None = None,
) -> ScanResult:
    """Navigate, preflight, observe — one envelope for coding agents."""
    degraded: list[str] = []
    console_window_start: int | None = None
    network_window_start: int | None = None
    if console_service is not None:
        console_window_start = console_service.mark_window()
    if network_service is not None:
        network_window_start = network_service.mark_window()

    pre = await preflight_check(session, url, ready_timeout=ready_timeout)
    if not pre.ok:
        return ScanResult(
            ok=False,
            url=url,
            preflight=pre,
            error=pre.error,
            degraded=pre.degraded,
        )
    degraded.extend(pre.degraded)

    obs = await collect_observation(
        session,
        images_dir=images_dir,
        name=name,
        screenshot_mode=screenshot_mode,  # type: ignore[arg-type]
        screenshot_selector=screenshot_selector,
        annotate_screenshot=annotate_screenshot,
        console_service=console_service,
        console_window_start=console_window_start,
        network_service=network_service,
        network_window_start=network_window_start,
        har_dir=har_dir,
    )
    if obs.degraded:
        degraded.extend(obs.degraded)
    if obs.dev_insights and obs.dev_insights.degraded:
        degraded.extend(obs.dev_insights.degraded)

    return ScanResult(
        ok=True,
        url=obs.url or pre.url,
        observation=obs,
        preflight=pre,
        degraded=sorted(set(degraded)),
    )
