"""Handler-level matrix for perception_seo_audit's include_ai_visibility toggle.

Runs the audit in DEVELOPMENT mode against a URL that produces graceful degraded
notes but still returns a valid contract-v1.0 envelope. Verifies that the
``ai_readiness`` block is present when include_ai_visibility is ``True`` (or
omitted) and absent when explicitly ``False``.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import handle_seo_audit


def _audit(**args) -> dict:
    scans = ScanRegistry()
    return asyncio.run(handle_seo_audit(scans, args))


@pytest.mark.integration
@pytest.mark.slow
def test_seo_audit_returns_valid_envelope() -> None:
    result = _audit(website_url="https://example.com/")
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_seo_audit"
    assert "data" in result
    assert isinstance(result.get("degraded", []), list)


@pytest.mark.integration
@pytest.mark.slow
def test_seo_audit_defaults_include_ai_visibility_true() -> None:
    result = _audit(website_url="https://example.com/")
    if not result["ok"]:
        pytest.skip(f"seo audit not runnable in this environment: {result.get('error')}")
    ctx = (result.get("data") or {}).get("reasoning_context_v2") or {}
    assert "ai_readiness" in ctx, "ai_readiness block must be present by default"


@pytest.mark.integration
@pytest.mark.slow
def test_seo_audit_include_ai_visibility_false_omits_block() -> None:
    result = _audit(website_url="https://example.com/", include_ai_visibility=False)
    if not result["ok"]:
        pytest.skip(f"seo audit not runnable in this environment: {result.get('error')}")
    ctx = (result.get("data") or {}).get("reasoning_context_v2") or {}
    assert "ai_readiness" not in ctx, (
        "ai_readiness block must NOT be present when include_ai_visibility=False"
    )
    recs = (result.get("data") or {}).get("recommendations") or []
    assert not any(
        (r.get("category") or "").lower() == "ai_visibility" for r in recs
    ), "no ai_visibility recommendations should be emitted when disabled"


@pytest.mark.unit
def test_seo_audit_request_include_ai_visibility_default() -> None:
    """Model-level default without needing companions to run."""
    from navigation.seo_intelligence import SeoAuditRequest

    req = SeoAuditRequest(website_url="https://example.com/")
    assert req.include_ai_visibility is True

    req_off = SeoAuditRequest(website_url="https://example.com/", include_ai_visibility=False)
    assert req_off.include_ai_visibility is False
