"""Cross-module integration coverage (P2.1–P2.10).

These tests exercise the interfaces between intelligence modules. Anything
requiring a browser or companion is marked ``integration`` and ``slow`` so
CI's fast tier can skip them; the offline pieces run in T0.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SANDBOX_ROOT = ROOT / "sandbox"

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry


# ---------------------------------------------------------------------------
# P2.2 — AI visibility pipeline (SEO providers → adapter → recommendations → readiness)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_p2_2_ai_visibility_adapter_derives_and_correlates() -> None:
    from navigation.seo_intelligence.ai_visibility import (
        AiVisibilityAdapter,
        attach_ai_readiness_block,
        detect_ai_readiness,
    )
    from navigation.seo_intelligence.models import (
        SeoEvidenceKind,
        SeoEvidenceRef,
    )

    evidence = [
        SeoEvidenceRef(
            evidence_id="ev:libre:schema",
            provider_id="librecrawl",
            kind=SeoEvidenceKind.CRAWL_ISSUE,
            title="No Structured Data",
            summary="Page has no JSON-LD or Schema.org markup",
            page_url="https://example.com/",
            severity="medium",
            metadata={"category": "Structured Data"},
        ),
        SeoEvidenceRef(
            evidence_id="ev:lh:meta",
            provider_id="lighthouse",
            kind=SeoEvidenceKind.TECHNICAL_ISSUE,
            title="Document does not have a meta description",
            summary="...",
            page_url="https://example.com/",
            severity="high",
        ),
    ]
    derived, degraded = AiVisibilityAdapter().derive(evidence, base_url="https://example.com/")
    assert isinstance(derived, list)
    assert isinstance(degraded, list)
    ai_evidence = [e for e in derived if e.kind.value == "ai_visibility"]
    assert ai_evidence, "expected at least one ai_visibility derived evidence"

    correlations = detect_ai_readiness(evidence + derived, base_url="https://example.com/")
    assert isinstance(correlations, list)

    ctx: dict = {}
    ctx = attach_ai_readiness_block(ctx, evidence=evidence + derived)
    assert "ai_readiness" in ctx


# ---------------------------------------------------------------------------
# P2.4 — Component foundation selection contract (already covered elsewhere too)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_p2_4_component_intelligence_contracts_module_present() -> None:
    """Ensure the component intelligence public API surface remains stable."""
    from navigation.component_intelligence import ComponentIntelligenceService

    service = ComponentIntelligenceService()
    for name in ("integrate_component", "search_components", "select_foundation"):
        assert hasattr(service, name) or hasattr(service, name.replace("_component", "")), name


# ---------------------------------------------------------------------------
# P2.6 — Figma → PDG discovery bridge (offline: not_connected path only)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_p2_6_figma_context_envelope_shape() -> None:
    """figma_context must return a valid envelope regardless of connection state.

    In environments without a Figma PAT / connected desktop bridge it should
    surface a clear ``error``; where a bridge is available the envelope should
    carry data. Either way, contract v1.0 shape is mandatory.
    """
    from navigation.mcp.handlers import handle_figma_context

    result = asyncio.run(handle_figma_context({}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_figma_context"
    if result["ok"] is False:
        assert result.get("error"), "figma_context failure must surface an error"
    else:
        assert isinstance(result.get("data"), dict)


# ---------------------------------------------------------------------------
# P2.10 — Lighthouse SEO (`perception_audit_seo`) is distinct from `perception_seo_audit`
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_p2_10_seo_audit_vs_audit_seo_are_distinct_tools() -> None:
    from navigation.mcp.tools import perception_tools

    class T:
        def __init__(self, name: str, description: str, inputSchema: dict) -> None:
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

    class Types:
        Tool = T

    tools = {t.name: t for t in perception_tools(Types)}
    assert "perception_audit_seo" in tools
    assert "perception_seo_audit" in tools
    fq = tools["perception_audit_seo"].description.lower()
    seo = tools["perception_seo_audit"].description.lower()
    assert fq != seo, "audit_seo (Lighthouse) and seo_audit (SEO Intelligence) must describe different work"


# ---------------------------------------------------------------------------
# P2.9 — SEO codebase hints — reasoning context accepts repo_root
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_p2_9_seo_audit_request_accepts_repo_root() -> None:
    from navigation.seo_intelligence import SeoAuditRequest

    req = SeoAuditRequest(
        website_url="https://example.com/",
        repo_root=str(SANDBOX_ROOT if SANDBOX_ROOT.exists() else ROOT),
    )
    assert req.repo_root, "SeoAuditRequest should carry repo_root for codebase hints"


# ---------------------------------------------------------------------------
# P2.3 & P2.5 — sandbox-required flows: keep them integration-marked
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_p2_3_resource_observe_bridge_requires_scan_id() -> None:
    from navigation.mcp.handlers import handle_resource_observe_bridge

    scans = ScanRegistry()
    result = asyncio.run(handle_resource_observe_bridge(scans, {"scan_id": "does-not-exist"}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_resource_observe_bridge"
    assert result["ok"] is False or bool(result.get("degraded"))


@pytest.mark.integration
@pytest.mark.slow
def test_p2_5_build_design_snapshot_requires_scan_or_session() -> None:
    from navigation.mcp.design_intelligence_handlers import handle_build_design_snapshot
    from navigation.visual_browser_intelligence.browser.session_store import SessionStore

    store = SessionStore()
    scans = ScanRegistry()
    snapshots = SnapshotRegistry()
    result = asyncio.run(handle_build_design_snapshot(store, scans, snapshots, {}))
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_build_design_snapshot"
    assert (result["ok"] is False) or bool((result.get("data") or {}).get("snapshot_id"))
