"""Design Snapshot Engine service facade."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .engine import DesignSnapshotEngine
from .models import DesignSnapshot

if TYPE_CHECKING:
    from navigation.visual_browser_intelligence.observe.observation import PageObservation


class DesignSnapshotService:
	"""Public API for intelligence modules."""

	def __init__(self, *, engine: DesignSnapshotEngine | None = None) -> None:
		self._engine = engine or DesignSnapshotEngine()

	async def capture(
		self,
		session: Any,
		*,
		observation: "PageObservation | None" = None,
		scan_id: str | None = None,
	) -> DesignSnapshot:
		obs_dict = observation.to_dict() if observation else {}
		return await self._engine.capture_from_session(
			session,
			visual_insights=obs_dict.get('visual_insights'),
			a11y_tree=obs_dict.get('a11y_tree', ''),
			dom_text=obs_dict.get('dom_text', ''),
			screenshot_ref=obs_dict.get('screenshot_path') or obs_dict.get('annotated_screenshot_path'),
			scan_id=scan_id,
		)

	def capture_fixture(self, data: dict[str, Any]) -> DesignSnapshot:
		return self._engine.capture_from_fixture(data)
