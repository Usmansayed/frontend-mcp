"""Phase 1 — execution tiers and SEO async jobs."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.scan_registry import ScanRegistry
from navigation.execution_runtime.policies.tier import ExecutionTier, tier_for_tool
from navigation.mcp.handlers import (
    handle_seo_audit_cancel,
    handle_seo_audit_poll,
    handle_seo_audit_start,
)
from navigation.seo_intelligence.jobs.store import SeoAuditJobStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult


@pytest.mark.unit
def test_tier_code_context_is_offload() -> None:
    assert tier_for_tool("perception_code_context") == ExecutionTier.SYNC_OFFLOAD


@pytest.mark.unit
def test_tier_health_is_sync_fast() -> None:
    assert tier_for_tool("perception_health") == ExecutionTier.SYNC_FAST


@pytest.mark.unit
def test_tier_seo_audit_start_is_sync_fast() -> None:
    assert tier_for_tool("perception_seo_audit_start") == ExecutionTier.SYNC_FAST


@pytest.mark.unit
def test_job_store_create_and_cancel(tmp_path: Path) -> None:
    store = SeoAuditJobStore(root=tmp_path / "jobs")
    job = store.create({"website_url": "https://example.com"})
    assert job.audit_job_id.startswith("audit_job_")
    loaded = store.get(job.audit_job_id)
    assert loaded is not None
    store.request_cancel(job.audit_job_id)
    loaded = store.get(job.audit_job_id)
    assert loaded is not None
    assert loaded.cancel_requested is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seo_audit_start_development_returns_instant_result(monkeypatch: pytest.MonkeyPatch) -> None:
    scans = ScanRegistry()
    scan_rec = scans.register(
        session_id="sess-1",
        run_id="run-1",
        url="https://example.com",
        observation={"url": "https://example.com", "title": "Example"},
    )

    async def _fake_development_audit(self, request):
        return SeoAuditResult(request=request, audit_id="audit_dev123")

    monkeypatch.setenv("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    monkeypatch.setattr(
        "navigation.seo_intelligence.planning.orchestrator.SeoAuditOrchestrator.development_audit",
        _fake_development_audit,
    )

    result = await handle_seo_audit_start(
        scans,
        {"website_url": "https://example.com", "scan_id": scan_rec.scan_id},
    )
    assert result["ok"] is True
    assert result["tool"] == "perception_seo_audit_start"
    data = result.get("data") or {}
    assert data.get("status") == "completed"
    assert data.get("instant") is True
    assert data.get("audit_id") == "audit_dev123"
    assert "audit_job_id" not in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seo_audit_start_professional_returns_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import patch

    scans = ScanRegistry()

    async def _fake_audit(self, request, **kwargs):
        return SeoAuditResult(request=request, audit_id="audit_test123")

    monkeypatch.setenv("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    monkeypatch.setattr(
        "navigation.seo_intelligence.planning.orchestrator.SeoAuditOrchestrator.audit",
        _fake_audit,
    )
    with patch("navigation.seo_intelligence.setup.auth_requirements.has_google_tokens", return_value=True):
        with patch(
            "navigation.seo_intelligence.setup.auth_requirements.bing_api.has_stored_tokens",
            return_value=True,
        ):
            result = await handle_seo_audit_start(
                scans,
                {"website_url": "https://example.com", "mode": "professional"},
            )
    assert result["ok"] is True
    assert result["tool"] == "perception_seo_audit_start"
    job_id = (result.get("data") or {}).get("audit_job_id")
    assert job_id

    await asyncio.sleep(0.05)
    poll = await handle_seo_audit_poll({"audit_job_id": job_id})
    assert poll["ok"] is True
    job = (poll.get("data") or {}).get("seo_audit_job") or {}
    assert job.get("audit_job_id") == job_id
    assert job.get("status") in ("completed", "collecting", "analyzing", "bootstrapping", "queued")

    cancel = await handle_seo_audit_cancel({"audit_job_id": job_id})
    assert cancel["ok"] is True
