"""Selection context from sibling intelligence modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelectionContext:
	repo_root: str = ''
	project_id: str = 'default'
	framework: str = ''
	primary_package: str = ''
	icon_family_hint: str = ''
	design_sense_styles: list[str] = field(default_factory=list)
	pdg_summary: dict[str, Any] = field(default_factory=dict)
	pdg_queries: dict[str, Any] = field(default_factory=dict)
	reasoning: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'repo_root': self.repo_root,
			'project_id': self.project_id,
			'framework': self.framework,
			'primary_package': self.primary_package,
			'icon_family_hint': self.icon_family_hint,
			'design_sense_styles': list(self.design_sense_styles),
			'pdg_summary': dict(self.pdg_summary),
			'pdg_queries': dict(self.pdg_queries),
			'reasoning': list(self.reasoning),
		}
