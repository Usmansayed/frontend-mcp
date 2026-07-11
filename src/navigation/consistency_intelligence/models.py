"""Legacy consistency report models — validation consumers use KnowledgeResponse in Phase 3+."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ConsistencyFinding:
	id: str
	category: str
	severity: str
	message: str
	recommendation: str = ''
	rule_id: str = ''
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'category': self.category,
			'severity': self.severity,
			'message': self.message,
			'recommendation': self.recommendation,
			'rule_id': self.rule_id,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class ConsistencyReport:
	passed: bool
	summary: str
	findings: list[ConsistencyFinding] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'passed': self.passed,
			'summary': self.summary,
			'findings': [f.to_dict() for f in self.findings],
			'degraded': list(self.degraded),
		}
