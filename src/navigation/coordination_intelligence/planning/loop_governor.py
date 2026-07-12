"""Loop Governor — invariants, retry budgets, and playbook progression on PSM Runtime."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.playbook_selector import PlaybookSelector
from navigation.coordination_intelligence.psm.normalize import VERIFY_CAPABILITIES

VERIFY_STEP_ACTIONS = frozenset({
    "verify_success_criteria",
    "run_invalid_submit_check",
    "run_valid_submit_check",
    "verify_staging_pages",
    "verify_consistency_fix",
    "verify_integration",
    "verify_seo_recommendation",
})


class LoopGovernor:
    def __init__(self, bundle: RuntimeArtifactBundle) -> None:
        self._bundle = bundle
        self._selector = PlaybookSelector(bundle)

    def check(self, psm: ProjectSituationModel, *, event: str | None = None) -> str | None:
        if psm.episode.auth_status == "requires_human":
            return "TR_AUTH_REQUIRED:auth_gate_requires_human"

        if psm.episode.verification_status == "failed":
            playbook_id = psm.episode.active_playbook_id
            playbook = self._bundle.playbook_by_id.get(playbook_id or "") or {}
            budget = int(playbook.get("retry_budget", 5))
            if int(psm.episode.retry_counters.get("verify_loop", 0)) >= budget:
                return "TR_VERIFY_EXHAUSTED"

        if psm.evidence.blocking and event == "before_advisory_capability":
            return "TR_BLOCKING_NONEMPTY"

        if event == "invalid_before_valid_violation":
            return "INV_INVALID_BEFORE_VALID"

        return None

    def should_stop(self, psm: ProjectSituationModel) -> str | None:
        return self.check(psm)

    def evaluate_step_advancement(
        self,
        psm: ProjectSituationModel,
        *,
        capability_id: str | None,
        envelope: dict[str, Any],
    ) -> bool:
        """Return True when the governor authorizes advancing the active playbook step."""
        if not capability_id or not envelope.get("ok"):
            return False

        step = self._selector.current_step(psm)
        if not step:
            return False
        if step.get("host_llm_only"):
            return False
        if step.get("capability") != capability_id:
            return False

        playbook_id = self._selector.select_playbook_id(psm)
        playbook = self._bundle.playbook_by_id.get(playbook_id or "") or {}
        if not self._sequence_allows(psm, playbook, step):
            return False

        semantic = step.get("semantic_action")
        if capability_id in VERIFY_CAPABILITIES or semantic in VERIFY_STEP_ACTIONS:
            return psm.episode.verification_status == "passed"

        if capability_id == "form_probe":
            return True

        if capability_id == "auth_gate":
            return psm.episode.auth_status != "requires_human"

        return True

    def advance_if_satisfied(
        self,
        psm: ProjectSituationModel,
        *,
        capability_id: str | None,
        envelope: dict[str, Any],
    ) -> bool:
        """Mark step complete when evidence satisfies the governor. Returns whether advanced."""
        if not self.evaluate_step_advancement(psm, capability_id=capability_id, envelope=envelope):
            return False
        step = self._selector.current_step(psm)
        if not step:
            return False
        step_id = step.get("step_id")
        if not step_id:
            return False
        self._selector.mark_step_complete(psm, step_id)
        return True

    def _sequence_allows(
        self,
        psm: ProjectSituationModel,
        playbook: dict,
        step: dict,
    ) -> bool:
        constraints = playbook.get("sequence_constraints") or []
        step_id = step.get("step_id")
        for rule in constraints:
            for before_id, after_id in rule.items():
                if before_id.endswith("_before") and after_id == step_id:
                    required = before_id.replace("_before", "")
                    if required not in psm.episode.completed_step_ids:
                        return False
        return True
