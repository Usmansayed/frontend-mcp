"""Playbook Selector — choose and advance playbooks from PSM Runtime."""

from __future__ import annotations

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import ProjectSituationModel


class PlaybookSelector:
    def __init__(self, bundle: RuntimeArtifactBundle) -> None:
        self._bundle = bundle

    def select_playbook_id(self, psm: ProjectSituationModel) -> str | None:
        if psm.episode.active_playbook_id:
            return psm.episode.active_playbook_id
        cluster = self._bundle.cluster_by_id.get(psm.situation.cluster_id) or {}
        return cluster.get("default_playbook")

    def current_step(self, psm: ProjectSituationModel) -> dict | None:
        playbook_id = self.select_playbook_id(psm)
        if not playbook_id:
            return None
        playbook = self._bundle.playbook_by_id.get(playbook_id)
        if not playbook:
            return None

        if psm.episode.active_step_id:
            for step in playbook.get("steps") or []:
                if step.get("step_id") == psm.episode.active_step_id:
                    return step

        for step in playbook.get("steps") or []:
            step_id = step.get("step_id")
            if step_id and step_id not in psm.episode.completed_step_ids:
                if self._sequence_allows(psm, playbook, step):
                    psm.episode.active_step_id = step_id
                    return step
        return None

    def mark_step_complete(self, psm: ProjectSituationModel, step_id: str) -> None:
        if step_id not in psm.episode.completed_step_ids:
            psm.episode.completed_step_ids.append(step_id)
        psm.episode.active_step_id = None

    def playbook_for_cluster(self, cluster_id: str) -> str | None:
        cluster = self._bundle.cluster_by_id.get(cluster_id) or {}
        return cluster.get("default_playbook")

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
