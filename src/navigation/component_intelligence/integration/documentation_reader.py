"""Gather structured install documentation via Framework Intelligence contract."""
from __future__ import annotations

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import DocumentationBundle, FoundationSelection
from ..models import ComponentCandidate


async def read_documentation(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
	selection: FoundationSelection | None = None,
	contracts: IntelligenceContracts | None = None,
) -> DocumentationBundle:
	"""Delegate to Framework Intelligence contract — implementation may evolve independently."""
	c = contracts or IntelligenceContracts.default()
	return await c.framework.fetch_install_documentation(
		candidate,
		repo_root=repo_root,
		selection=selection,
	)
