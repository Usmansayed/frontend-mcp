"""Component intelligence service facade."""
from __future__ import annotations

from navigation.component_intelligence.probes.form_probe import probe_validation_form


class ComponentIntelligenceService:
	"""Facade for component discovery, probes, and adaptation."""

	probe_validation_form = staticmethod(probe_validation_form)
