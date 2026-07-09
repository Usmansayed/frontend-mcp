"""Phase 4: detect feature-gated UI vs hard failures."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import read_page_text, read_current_url


@dataclass(slots=True)
class FeatureFlagProbe:
    route: str
    flag_name: str
    available_without_flag: bool
    available_with_flag: bool
    in_code_graph: bool = True
    status: str = "unknown"  # feature_gated | enabled | missing

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "flag_name": self.flag_name,
            "available_without_flag": self.available_without_flag,
            "available_with_flag": self.available_with_flag,
            "in_code_graph": self.in_code_graph,
            "status": self.status,
        }


@dataclass(slots=True)
class FeatureFlagResult:
    ok: bool
    probes: list[FeatureFlagProbe] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {"ok": self.ok, "probes": [p.to_dict() for p in self.probes], "error": self.error}


async def probe_feature_flag(
    session: Any,
    base_url: str,
    route: str,
    *,
    flag_query: str,
    feature_text: str,
) -> FeatureFlagResult:
    b = base_url.rstrip("/")
    path = route if route.startswith("/") else f"/{route}"
    probes: list[FeatureFlagProbe] = []

    try:
        await session.navigate_to(f"{b}{path}")
        await asyncio.sleep(0.3)
        text_off = (await read_page_text(session, include_dom_text=True)).lower()
        off_has_feature = feature_text.lower() in text_off

        await session.navigate_to(f"{b}{path}?{flag_query}")
        await asyncio.sleep(0.3)
        text_on = (await read_page_text(session, include_dom_text=True)).lower()
        on_has_feature = feature_text.lower() in text_on

        status = "feature_gated"
        if on_has_feature and not off_has_feature:
            status = "feature_gated"
        elif on_has_feature and off_has_feature:
            status = "enabled"
        else:
            status = "missing"

        probe = FeatureFlagProbe(
            route=path,
            flag_name=flag_query.split("=")[0],
            available_without_flag=off_has_feature,
            available_with_flag=on_has_feature,
            status=status,
        )
        probes.append(probe)
        ok = status == "feature_gated"
        return FeatureFlagResult(ok=ok, probes=probes)
    except Exception as exc:
        return FeatureFlagResult(ok=False, probes=probes, error=str(exc))
