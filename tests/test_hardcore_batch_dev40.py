"""Tests for .dev40 — license string shape + process/package skew + short audit timeout."""

from __future__ import annotations

from navigation.core.code_revision import CODE_REVISION
from navigation.core.process_identity import version_skew_report
from navigation.execution_runtime.policies.timeout import TimeoutPolicy
from navigation.resource_intelligence.license.resolver import normalize_license_input
from navigation.resource_intelligence.models import ResourceDiscoveryRequest
from navigation.resource_intelligence.service import ResourceIntelligenceService


def test_code_revision_matches_pyproject():
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert CODE_REVISION == data["project"]["version"]


def test_normalize_license_flat_string_isc():
    profile = normalize_license_input("ISC")
    assert profile.spdx_id == "ISC"
    assert profile.commercial_use is True


def test_normalize_license_nested_name_object():
    profile = normalize_license_input({"name": "ISC", "commercial_use": True})
    assert profile.spdx_id == "ISC"
    assert profile.commercial_use is True


def test_license_check_flat_string_does_not_crash():
    svc = ResourceIntelligenceService()
    summary = svc.check_license(
        {"license": "ISC", "provider_id": "lucide"},
        ResourceDiscoveryRequest(query="license check", commercial_required=True),
    )
    assert summary["spdx_id"] == "ISC"
    assert summary["allowed"] is True


def test_license_check_nested_object_still_works():
    svc = ResourceIntelligenceService()
    summary = svc.check_license(
        {"license": {"spdx_id": "MIT", "commercial_use": True, "attribution_required": True}},
        ResourceDiscoveryRequest(query="license check", commercial_required=True, attribution_ok=True),
    )
    assert summary["spdx_id"] == "MIT"
    assert summary["allowed"] is True


def test_audit_timeout_honors_short_timeout_s():
    policy = TimeoutPolicy()
    wall = policy.timeout_for("perception_audit_accessibility", {"timeout_s": 90})
    assert wall == 95.0  # 90 + 5 overhead
    assert wall < 120.0


def test_audit_timeout_default_still_at_least_120():
    policy = TimeoutPolicy()
    wall = policy.timeout_for("perception_audit_accessibility", {})
    assert wall >= 120.0


def test_version_skew_report_includes_code_revision():
    report = version_skew_report(CODE_REVISION)
    assert report["code_revision"] == CODE_REVISION
    # Fresh process with matching revision should not claim code_revision_mismatch.
    assert "code_revision_mismatch" not in report["version_skew_reasons"]
