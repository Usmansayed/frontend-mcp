"""Visual browser intelligence service facade."""
from __future__ import annotations

from navigation.visual_browser_intelligence.observe.scan import scan_page
from navigation.visual_browser_intelligence.observe.observation import collect_observation
from navigation.visual_browser_intelligence.verify.verification import verify


class VisualBrowserService:
	"""Facade for browser observation, verification, and session runtime."""

	scan_page = staticmethod(scan_page)
	collect_observation = staticmethod(collect_observation)
	verify = staticmethod(verify)
