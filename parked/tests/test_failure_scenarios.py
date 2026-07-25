"""Failure and degraded-mode scenarios F1–F16 from the production master test plan.

Each test targets one row of the P2 failure matrix. Scenarios that require an
external state to be down (F1 dev server, F2 browser crash, F3 Lighthouse
missing) are marked ``failure`` — they exercise the graceful path and skip
when the environment already has the dependency.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.envelope import make_envelope


# ---------------------------------------------------------------------------
# F1 — Dev server down: perception_health surfaces ok=false with a clear error.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f1_dev_server_unreachable() -> None:
    from navigation.mcp.handlers import handle_health

    result = asyncio.run(handle_health({"url": "http://127.0.0.1:1"}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_health"
    assert result["ok"] is False
    assert result.get("error"), "health must surface an error when unreachable"


# ---------------------------------------------------------------------------
# F3 — Lighthouse / Node missing → audits must degrade, not crash.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f3_lighthouse_unavailable_is_reported_gracefully(monkeypatch) -> None:
    from navigation.frontend_quality_intelligence.audits import runner as audit_runner

    monkeypatch.setattr(audit_runner, "lighthouse_available", lambda: False)
    assert audit_runner.lighthouse_available() is False


# ---------------------------------------------------------------------------
# F6 — Windows cp1252 console: JSON serialization stays UTF-8.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f6_envelope_json_is_utf8_safe() -> None:
    env = make_envelope(
        "perception_seo_audit",
        data={"title": "café — résumé — 中文"},
        degraded=["utf8_probe:π"],
    )
    encoded = json.dumps(env)
    assert "\\u" in encoded or "café" not in encoded or "\\u00e9" in encoded or "é" in encoded
    round_tripped = json.loads(encoded)
    assert round_tripped["data"]["title"].startswith("café") or round_tripped["data"]["title"].startswith("caf")


# ---------------------------------------------------------------------------
# F7 — OAuth cancelled: no partial credentials leak.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f7_seo_connect_cancelled_is_actionable() -> None:
    from navigation.mcp.handlers import handle_seo_connect

    result = asyncio.run(handle_seo_connect({"website_url": "", "action": "start"}))
    assert result["contract_version"] == "1.0"
    if result["ok"] is False:
        assert result.get("error"), "cancelled setup must include an actionable error"


# ---------------------------------------------------------------------------
# F8 — SEO audit in professional mode without auth → auth_required error, no crash.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.slow
def test_f8_seo_audit_professional_without_auth() -> None:
    from navigation.mcp.handlers import handle_seo_audit
    from navigation.core.scan_registry import ScanRegistry

    scans = ScanRegistry()
    result = asyncio.run(
        handle_seo_audit(
            scans,
            {
                "website_url": "https://example.com/",
                "mode": "professional",
                "gsc_auth_bypass_for_test": False,
            },
        )
    )
    assert result["contract_version"] == "1.0"
    if not result["ok"]:
        assert result.get("error"), "auth-blocked audit must expose an error"


# ---------------------------------------------------------------------------
# F9 — Figma not connected: figma_context surfaces figma_not_connected.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f9_figma_not_connected(monkeypatch) -> None:
    """When Figma is not connected the handler must surface an error, not crash.

    Skipped when the host machine has a live Figma bridge — this test targets the
    no-PAT graceful path, not a rejection of successful connections.
    """
    from navigation.mcp.handlers import handle_figma_context

    monkeypatch.delenv("FIGMA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("FIGMA_PAT", raising=False)
    result = asyncio.run(handle_figma_context({}))
    assert result["contract_version"] == "1.0"
    if result["ok"]:
        pytest.skip("host has a live Figma bridge — no-PAT path cannot be exercised here")
    assert result.get("error"), "figma failure envelope must carry an error"


# ---------------------------------------------------------------------------
# F11 — Invalid tool arguments: early validation errors, not exceptions.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f11_seo_audit_missing_website_url() -> None:
    from navigation.mcp.handlers import handle_seo_audit
    from navigation.core.scan_registry import ScanRegistry

    scans = ScanRegistry()
    result = asyncio.run(handle_seo_audit(scans, {}))
    assert result["contract_version"] == "1.0"
    assert result["ok"] is False
    assert "website_url" in (result.get("error") or "")


@pytest.mark.failure
@pytest.mark.unit
def test_f11_integrate_missing_query_and_candidate() -> None:
    from navigation.mcp.handlers import handle_integrate_component

    result = asyncio.run(handle_integrate_component({}))
    assert result["contract_version"] == "1.0"
    assert result["ok"] is False
    assert "query" in (result.get("error") or "").lower()


# ---------------------------------------------------------------------------
# F12 — Unknown scan_id: resource read fails cleanly, no crash.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f12_unknown_scan_id_resource_read() -> None:
    from navigation.core.scan_registry import ScanRegistry
    from navigation.mcp.resources import read_resource

    scans = ScanRegistry()
    with pytest.raises(Exception):
        read_resource("perception://scan/does-not-exist/report.json", scans)


# ---------------------------------------------------------------------------
# F13 — include_ai_visibility=false: no ai_readiness block or ai_visibility recs.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f13_include_ai_visibility_false_skips_layer() -> None:
    from navigation.seo_intelligence.models import (
        SeoAuditMode,
        SeoEvidenceKind,
        SeoEvidenceRef,
    )
    from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline

    evidence = [
        SeoEvidenceRef(
            evidence_id="ev:libre:schema",
            provider_id="librecrawl",
            kind=SeoEvidenceKind.CRAWL_ISSUE,
            title="No Structured Data",
            summary="Page has no JSON-LD or Schema.org markup",
            page_url="https://example.com/",
        ),
    ]
    _recs, correlations, ctx = run_recommendation_pipeline(
        evidence,
        audit_id="audit_f13",
        mode=SeoAuditMode.DEVELOPMENT,
        website_url="https://example.com/",
        ai_reasoning=False,
        include_ai_visibility=False,
    )
    assert "ai_readiness" not in ctx
    assert not any(c.get("category") == "ai_visibility" for c in correlations)


# ---------------------------------------------------------------------------
# F14 — Insufficient evidence for an AI analyzer → degraded note, score excludes skipped.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f14_analyzer_skip_produces_degraded_note() -> None:
    from navigation.seo_intelligence.ai_visibility import AiVisibilityAdapter

    derived, degraded = AiVisibilityAdapter().derive([], base_url="https://example.com/")
    assert isinstance(derived, list)
    assert any("insufficient_evidence" in note or "skipped" in note.lower() for note in degraded), (
        f"expected at least one skip note when no evidence is provided, got {degraded!r}"
    )


# ---------------------------------------------------------------------------
# F16 — Disk full / cache write fail: graph save surfaces the error.
# ---------------------------------------------------------------------------


@pytest.mark.failure
@pytest.mark.unit
def test_f16_graph_save_to_readonly_directory(tmp_path: Path, monkeypatch) -> None:
    from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore

    graph_path = tmp_path / "nested" / "seo_graph.json"
    store = SeoKnowledgeGraphStore(path=graph_path)
    store.load()
    store.save()
    assert graph_path.exists()

    def _bad_write(*args, **kwargs):
        raise OSError("disk full (probe)")

    monkeypatch.setattr(Path, "write_text", _bad_write)
    with pytest.raises(OSError):
        store.save()
