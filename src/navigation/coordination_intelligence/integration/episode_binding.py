"""Session and project bindings to PSM Runtime episodes."""

from __future__ import annotations


class EpisodeBindingStore:
    """Maps runtime identifiers to coordinator episode IDs."""

    def __init__(self) -> None:
        self._by_session: dict[str, str] = {}
        self._by_project: dict[str, str] = {}

    def bind_session(self, session_id: str, episode_id: str) -> None:
        self._by_session[session_id] = episode_id

    def bind_project(self, project_id: str, episode_id: str) -> None:
        self._by_project[project_id] = episode_id

    def unbind_session(self, session_id: str) -> None:
        self._by_session.pop(session_id, None)

    def resolve(
        self,
        *,
        session_id: str | None = None,
        project_id: str | None = None,
        episode_id: str | None = None,
    ) -> str | None:
        if episode_id:
            return episode_id
        if session_id:
            found = self._by_session.get(session_id)
            if found:
                return found
        if project_id:
            return self._by_project.get(project_id)
        return self._by_project.get("default")

    def clear(self) -> None:
        self._by_session.clear()
        self._by_project.clear()
