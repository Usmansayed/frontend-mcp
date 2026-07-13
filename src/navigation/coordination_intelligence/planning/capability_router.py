"""Capability Router — gate capabilities using PSM Runtime + capability contracts."""

from __future__ import annotations

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import (
    GateResult,
    ProjectSituationModel,
    posture_meets_min,
)


class CapabilityRouter:
    def __init__(self, bundle: RuntimeArtifactBundle) -> None:
        self._bundle = bundle

    def compute_capability_posture(self, psm: ProjectSituationModel) -> None:
        eligible: list[str] = []
        blocked: list[str] = []
        deferred: list[str] = []

        for cap_id, contract in self._bundle.capability_by_id.items():
            gate = self.gate(psm, cap_id)
            risk = contract.get("risk") or {}
            if risk.get("mcp_ready") is False:
                blocked.append(cap_id)
                continue
            if gate.allowed:
                eligible.append(cap_id)
            elif gate.gather_first:
                deferred.append(cap_id)
            else:
                blocked.append(cap_id)

        posture = psm.situation.capability_posture
        posture.eligible = sorted(eligible)
        posture.blocked = sorted(blocked)
        posture.deferred = sorted(deferred)

    def gate(self, psm: ProjectSituationModel, capability_id: str) -> GateResult:
        contract = self._bundle.capability_by_id.get(capability_id)
        if not contract:
            return GateResult(False, capability_id, reason="unknown_capability")

        defer_reason = self._anti_pattern_defers(psm, capability_id)
        if defer_reason:
            return GateResult(
                False,
                capability_id,
                reason=defer_reason,
                gather_first="browser_verify",
            )

        if self._anti_pattern_blocks(psm, capability_id):
            return GateResult(False, capability_id, reason="anti_pattern_block")

        requires = contract.get("requires") or {}
        for domain, spec in (requires.get("evidence") or {}).items():
            min_posture = (spec or {}).get("min_posture", "unknown")
            current = psm.evidence.domains.get(domain)
            if current is None or not posture_meets_min(current.posture, min_posture):
                return GateResult(
                    False,
                    capability_id,
                    reason=f"evidence_gap:{domain}",
                    gather_first=self._gather_for_domain(domain),
                )

        for artifact in requires.get("artifacts") or []:
            if not getattr(psm.artifacts, artifact, None):
                return GateResult(
                    False,
                    capability_id,
                    reason=f"missing_artifact:{artifact}",
                    gather_first=self._gather_for_artifact(artifact),
                )

        if psm.constraints.human_gates:
            return GateResult(False, capability_id, reason="human_gate_active")

        return GateResult(True, capability_id)

    def _anti_pattern_blocks(self, psm: ProjectSituationModel, capability_id: str) -> bool:
        for rule in self._bundle.anti_patterns.get("rules") or []:
            when = rule.get("when")
            blocked = rule.get("block_capabilities") or []
            if capability_id not in blocked:
                continue
            if when == "evidence_blocking_nonempty" and psm.evidence.blocking:
                return True
            if when == "auth_gate_requires_human" and psm.episode.auth_status == "requires_human":
                return True
            if when == "repo_root_missing" and not psm.artifacts.repo_root:
                return True
            if when == "no_scan_id_and_no_snapshot_id":
                if not psm.artifacts.scan_id and not psm.artifacts.snapshot_id:
                    return True
        return False

    def _anti_pattern_defers(self, psm: ProjectSituationModel, capability_id: str) -> str | None:
        attempts = psm.episode.retry_counters.get("capability_attempts") or {}
        for rule in self._bundle.anti_patterns.get("rules") or []:
            when = rule.get("when")
            deferred = rule.get("defer_capabilities") or []
            if capability_id not in deferred:
                continue
            if when == "same_page_rapid_iteration":
                observe_count = int(attempts.get("browser_observe", 0))
                if observe_count >= 2 and psm.artifacts.scan_id:
                    return str(rule.get("reason") or "anti_pattern_defer:rapid_iteration")
        return None

    @staticmethod
    def _gather_for_domain(domain: str) -> str | None:
        mapping = {
            "ui_runtime": "browser_observe",
            "codebase": "codebase_context",
            "design_system": "design_graph_manage",
            "seo": "seo_readiness",
        }
        return mapping.get(domain)

    @staticmethod
    def _gather_for_artifact(artifact: str) -> str | None:
        mapping = {
            "session_id": "browser_session_manage",
            "scan_id": "browser_observe",
            "repo_root": "codebase_context",
        }
        return mapping.get(artifact)
