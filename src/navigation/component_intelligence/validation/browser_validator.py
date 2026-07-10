"""Post-integration browser validation via Browser Intelligence contract."""
from __future__ import annotations

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import ValidationReport


async def validate_integration(
	*,
	preview_url: str | None,
	repo_root: str | Path,
	installed_files: list[str] | None = None,
	contracts: IntelligenceContracts | None = None,
) -> ValidationReport:
	c = contracts or IntelligenceContracts.default()
	root = Path(repo_root) if repo_root else Path.cwd()
	return await c.browser.validate_component_integration(
		preview_url=preview_url,
		repo_root=root,
		installed_files=installed_files,
	)
