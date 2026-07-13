"""PSM Runtime — in-memory single source of truth for coordinator episodes."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle, load_runtime_artifacts
from navigation.coordination_intelligence.models import (
    ArtifactsState,
    EpisodeState,
    IntentFrame,
    ProjectSituationModel,
    SituationState,
    _utc_now,
)
from navigation.coordination_intelligence.psm.normalize import apply_envelope
from navigation.coordination_intelligence.psm.signature import refresh_cluster_signature


class PSMRuntime:
    """Owns live PSM documents. All coordinator components read/write through here."""

    def __init__(self, bundle: RuntimeArtifactBundle | None = None) -> None:
        self._bundle = bundle or load_runtime_artifacts()
        self._episodes: dict[str, ProjectSituationModel] = {}

    @property
    def bundle(self) -> RuntimeArtifactBundle:
        return self._bundle

    def create_episode(
        self,
        *,
        project_id: str = "default",
        cluster_id: str | None = None,
        playbook_id: str | None = None,
        situation_class: str = "new_feature",
        lifecycle_stage: str = "S05_implementation",
        project_maturity: str = "M3",
        repo_root: str | None = None,
        website_url: str | None = None,
        session_id: str | None = None,
        intent: str | None = None,
        leaf_hint: str | None = None,
    ) -> ProjectSituationModel:
        situation = SituationState(
            situation_class=situation_class,
            lifecycle_stage=lifecycle_stage,
            project_maturity=project_maturity,
            cluster_id=cluster_id or "cluster.feature.form_pipeline",
            leaf_hint=leaf_hint,
        )
        episode = EpisodeState()
        if playbook_id:
            episode.active_playbook_id = playbook_id
        elif cluster_id:
            cluster = self._bundle.cluster_by_id.get(cluster_id) or {}
            episode.active_playbook_id = cluster.get("default_playbook")

        psm = ProjectSituationModel(
            project_id=project_id,
            situation=situation,
            episode=episode,
            artifacts=ArtifactsState(
                repo_root=repo_root,
                website_url=website_url,
                session_id=session_id,
            ),
        )
        if intent:
            psm.episode.intent_stack.append(IntentFrame(intent=intent, pushed_at=_utc_now()))

        refresh_cluster_signature(psm)
        self._episodes[psm.episode_id] = psm
        return psm

    def get(self, episode_id: str) -> ProjectSituationModel | None:
        return self._episodes.get(episode_id)

    def require(self, episode_id: str) -> ProjectSituationModel:
        psm = self.get(episode_id)
        if psm is None:
            raise KeyError(f"Unknown episode_id: {episode_id}")
        return psm

    def save(self, psm: ProjectSituationModel) -> None:
        psm.touch()
        refresh_cluster_signature(psm)
        self._episodes[psm.episode_id] = psm

    def apply_envelope(
        self,
        episode_id: str,
        envelope: dict[str, Any],
        *,
        capability_id: str | None = None,
    ) -> ProjectSituationModel:
        psm = self.require(episode_id)
        apply_envelope(psm, envelope, self._bundle, capability_id=capability_id)
        self.save(psm)
        return psm

    def list_episodes(self) -> list[str]:
        return list(self._episodes.keys())
