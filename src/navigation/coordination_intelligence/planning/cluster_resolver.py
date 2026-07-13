"""Cluster resolver — infer runtime cluster from PSM evidence (never research states)."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import ProjectSituationModel


class ClusterResolver:
    """Infer cluster_id and lifecycle stage from live PSM evidence."""

    def __init__(self, bundle: RuntimeArtifactBundle) -> None:
        self._bundle = bundle
        self._rules = bundle.decision_heuristics.get("cluster_resolution") or {}

    def resolve(self, psm: ProjectSituationModel) -> None:
        cluster_id = self._score_clusters(psm)
        prev_cluster = psm.situation.cluster_id
        if cluster_id:
            psm.situation.cluster_id = cluster_id
            cluster = self._bundle.cluster_by_id.get(cluster_id) or {}
            default_playbook = cluster.get("default_playbook")
            if default_playbook and self._playbook_gate_allows(cluster, psm):
                current = psm.episode.active_playbook_id
                generic = current in (None, "", "observe_reason_act_verify.loop")
                if generic or prev_cluster != cluster_id:
                    psm.episode.active_playbook_id = default_playbook
        psm.situation.lifecycle_stage = self._infer_lifecycle_stage(psm)

    def _playbook_gate_allows(self, cluster: dict[str, Any], psm: ProjectSituationModel) -> bool:
        gate = cluster.get("playbook_gate") or {}
        required = gate.get("requires_last_capability")
        if not required:
            return True
        return psm.episode.retry_counters.get("last_capability") == required

    def _score_clusters(self, psm: ProjectSituationModel) -> str | None:
        scores: dict[str, int] = {}
        current = psm.situation.cluster_id
        inertia = int(self._rules.get("inertia_points", 1))

        def bump(cid: str, points: int) -> None:
            scores[cid] = scores.get(cid, 0) + points

        if current:
            bump(current, inertia)

        last_tool = psm.episode.retry_counters.get("last_tool")
        if isinstance(last_tool, str):
            for cid, points in (self._rules.get("tool_affinity") or {}).get(last_tool, {}).items():
                bump(cid, int(points))

        last_cap = psm.episode.retry_counters.get("last_capability")
        if isinstance(last_cap, str):
            for cid, points in (self._rules.get("capability_affinity") or {}).get(last_cap, {}).items():
                bump(cid, int(points))

        playbook_pts = int(self._rules.get("playbook_affinity_points", 3))
        if psm.episode.active_playbook_id:
            for cluster_id, cluster in self._bundle.cluster_by_id.items():
                if cluster.get("default_playbook") == psm.episode.active_playbook_id:
                    bump(cluster_id, playbook_pts)

        cap_pts = int(self._rules.get("suggested_capability_points", 1))
        for cluster_id, cluster in self._bundle.cluster_by_id.items():
            for cap in cluster.get("suggested_capabilities") or []:
                if cap in psm.situation.capability_posture.eligible:
                    bump(cluster_id, cap_pts)

        for rule in self._rules.get("evidence_posture_bumps") or []:
            domain = rule.get("domain")
            when_not = rule.get("when_not", "unknown")
            if not domain or domain not in psm.evidence.domains:
                continue
            if psm.evidence.domains[domain].posture != when_not:
                for cid, points in (rule.get("bumps") or {}).items():
                    bump(cid, int(points))

        for gate_cluster, points in (self._rules.get("human_gates_bump") or {}).items():
            if psm.constraints.human_gates:
                bump(gate_cluster, int(points))

        attempts = psm.episode.retry_counters.get("capability_attempts") or {}
        for rule in self._rules.get("conditional_bumps") or []:
            if self._conditional_rule_matches(rule, psm, attempts, last_cap):
                for cid, points in (rule.get("bumps") or {}).items():
                    bump(cid, int(points))

        if not scores:
            return current or self._rules.get("default_cluster") or "cluster.discovery.bootstrap"
        return max(scores.items(), key=lambda item: item[1])[0]

    def _conditional_rule_matches(
        self,
        rule: dict[str, Any],
        psm: ProjectSituationModel,
        attempts: dict[str, Any],
        last_cap: Any,
    ) -> bool:
        min_attempts = rule.get("capability_attempts_at_least") or {}
        for cap, minimum in min_attempts.items():
            if int(attempts.get(cap, 0)) < int(minimum):
                return False

        for cond in rule.get("all_of") or []:
            if not self._eval_condition(cond, psm, attempts, last_cap):
                return False
        for cap in rule.get("any_capability_attempted") or []:
            if int(attempts.get(cap, 0)) >= 1:
                break
        else:
            if rule.get("any_capability_attempted"):
                return False
        for cap in rule.get("none_capability_attempted") or []:
            if int(attempts.get(cap, 0)) >= 1:
                return False
        return True

    @staticmethod
    def _eval_condition(
        cond: dict[str, Any],
        psm: ProjectSituationModel,
        attempts: dict[str, Any],
        last_cap: Any,
    ) -> bool:
        if "capability_attempted" in cond:
            cap = cond["capability_attempted"]
            return int(attempts.get(cap, 0)) >= 1
        if "last_capability" in cond:
            return last_cap == cond["last_capability"]
        if "verification_status" in cond:
            return psm.episode.verification_status == cond["verification_status"]
        return True

    @staticmethod
    def _infer_lifecycle_stage(psm: ProjectSituationModel) -> str:
        # Intent keyword hint (host-provided) — never research leaf IDs
        for frame in reversed(psm.episode.intent_stack):
            from navigation.coordination_intelligence.planning.situation_policy import intent_suggests_stage

            hinted = intent_suggests_stage(frame.intent)
            if hinted:
                return hinted

        if psm.constraints.human_gates:
            return "Sxx_any"
        if psm.episode.verification_status == "passed" and psm.episode.completed_step_ids:
            # Prefer late verification band when verify already succeeded
            if psm.situation.lifecycle_stage in (
                "S08_quality",
                "S09_consistency",
                "S10_release",
                "S11_production",
            ):
                return psm.situation.lifecycle_stage
            return "S07_verification"
        if psm.episode.completed_step_ids and psm.episode.verification_status != "passed":
            return "S05_implementation"

        domains = psm.evidence.domains
        known_count = sum(1 for d in domains.values() if d.posture not in ("unknown",))
        design_src = domains["design_source"].posture not in ("unknown",)
        design_sys = domains["design_system"].posture not in ("unknown",)
        assets = domains["assets"].posture not in ("unknown",)
        figma = bool((psm.artifacts.persistent or {}).get("figma_connected"))

        if known_count == 0 and not figma:
            return "S02_discovery"
        if (design_src or assets or figma) and domains["ui_runtime"].posture == "unknown":
            return "S03_design"
        if domains["ui_runtime"].posture in ("known", "verified", "partial", "regressed"):
            return "S05_implementation"
        if domains["seo"].posture not in ("unknown",):
            return "S08_quality"
        if design_sys:
            return "S09_consistency"
        return psm.situation.lifecycle_stage or "S05_implementation"
