"""Audit report models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuditCategory(str, Enum):
	ACCESSIBILITY = 'accessibility'
	PERFORMANCE = 'performance'
	SEO = 'seo'
	BEST_PRACTICES = 'best-practices'

	@classmethod
	def from_tool_name(cls, name: str) -> 'AuditCategory':
		mapping = {
			'accessibility': cls.ACCESSIBILITY,
			'performance': cls.PERFORMANCE,
			'seo': cls.SEO,
			'best_practices': cls.BEST_PRACTICES,
			'best-practices': cls.BEST_PRACTICES,
		}
		key = name.strip().lower().replace('perception_audit_', '')
		if key not in mapping:
			raise ValueError(f'unknown audit category: {name}')
		return mapping[key]


@dataclass(slots=True)
class AuditIssue:
	id: str
	title: str
	description: str = ''
	score: float | None = None
	impact: str = 'moderate'
	selector: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'title': self.title,
			'description': self.description,
			'score': self.score,
			'impact': self.impact,
			'selector': self.selector,
		}


@dataclass(slots=True)
class AuditReport:
	category: str
	url: str
	score: float
	blocking: list[str] = field(default_factory=list)
	warnings: list[dict[str, Any]] = field(default_factory=list)
	metrics: dict[str, Any] = field(default_factory=dict)
	audit_counts: dict[str, int] = field(default_factory=dict)
	artifacts: dict[str, str] = field(default_factory=dict)
	lighthouse_version: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'category': self.category,
			'url': self.url,
			'score': self.score,
			'blocking': list(self.blocking),
			'warnings': list(self.warnings),
			'metrics': dict(self.metrics),
			'audit_counts': dict(self.audit_counts),
			'artifacts': dict(self.artifacts),
			'lighthouse_version': self.lighthouse_version,
			'degraded': list(self.degraded),
		}
