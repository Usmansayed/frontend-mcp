"""Contract coverage for the residual P1 tools that weren't referenced elsewhere.

These fill the gap between the primary test files and the release gate G6
requirement (P1 tool coverage ≥95%). Each test issues a minimal, non-network
call to confirm the handler returns a well-formed contract v1.0 envelope
even when its upstream provider is unavailable — that is the contract we
promise agents.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.mcp.handlers import (
    handle_audit_best_practices,
    handle_audit_performance,
    handle_figma_connect,
    handle_resource_avatar_search,
    handle_resource_font_search,
    handle_resource_illustration_search,
    handle_resource_logo_search,
    handle_resource_photo_search,
)


def _run(coro) -> dict:
    return asyncio.run(coro)


@pytest.mark.unit
def test_perception_figma_connect_envelope() -> None:
    """perception_figma_connect must return a well-formed envelope even without a PAT."""
    result = _run(handle_figma_connect({}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_figma_connect"
    assert isinstance(result.get("data"), dict)


@pytest.mark.unit
@pytest.mark.parametrize(
    "handler,tool_name",
    [
        (handle_resource_avatar_search, "perception_resource_avatar_search"),
        (handle_resource_font_search, "perception_resource_font_search"),
        (handle_resource_illustration_search, "perception_resource_illustration_search"),
        (handle_resource_logo_search, "perception_resource_logo_search"),
        (handle_resource_photo_search, "perception_resource_photo_search"),
    ],
)
def test_resource_search_shortcuts_return_envelopes(handler, tool_name: str) -> None:
    """Each category shortcut must produce ok:true or explicit degraded[] — never crash."""
    result = _run(handler({"query": "coverage-probe"}))
    assert result["contract_version"] == "1.0", tool_name
    assert result["tool"] == tool_name
    if not result["ok"]:
        assert result.get("degraded") or result.get("error"), (
            f"{tool_name} failure must surface degraded[] or error"
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize(
    "handler,tool_name",
    [
        (handle_audit_best_practices, "perception_audit_best_practices"),
        (handle_audit_performance, "perception_audit_performance"),
    ],
)
def test_lighthouse_audits_return_envelopes_or_skip(handler, tool_name: str) -> None:
    """Lighthouse audits must degrade cleanly when Lighthouse is unavailable."""
    from navigation.frontend_quality_intelligence.audits.runner import lighthouse_available
    from navigation.visual_browser_intelligence.browser.session_store import SessionStore

    store = SessionStore()
    result = _run(handler(store, {"session_id": "nonexistent", "url": "http://127.0.0.1:1"}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == tool_name
    if not lighthouse_available():
        assert not result["ok"] or bool(result.get("degraded")), (
            "when lighthouse is unavailable, audits must surface an error or degraded[]"
        )
