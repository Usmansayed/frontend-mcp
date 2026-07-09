"""Perception diagnosis report models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ArtifactRef:
	kind: str
	path: str
	uri: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return {'kind': self.kind, 'path': self.path, 'uri': self.uri}


@dataclass(slots=True)
class DiagnosisOptions:
	url: str | None = None
	include_screenshot: bool = True
	include_audits: bool = False
	audit_categories: tuple[str, ...] = ()
	audit_timeout_s: int = 120
	mode: str = 'debug'


@dataclass(slots=True)
class PerceptionReport:
	summary: str
	blocking: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)
	console: dict[str, Any] | None = None
	network: dict[str, Any] | None = None
	visual: dict[str, Any] | None = None
	audits: dict[str, dict[str, Any]] = field(default_factory=dict)
	verification: dict[str, Any] = field(default_factory=dict)
	suggested_fixes: list[str] = field(default_factory=list)
	artifacts: list[dict[str, Any]] = field(default_factory=list)
	scan_id: str | None = None
	url: str = ''
	mode: str = 'debug'
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'summary': self.summary,
			'blocking': list(self.blocking),
			'warnings': list(self.warnings),
			'console': self.console,
			'network': self.network,
			'visual': self.visual,
			'audits': dict(self.audits),
			'verification': dict(self.verification),
			'suggested_fixes': list(self.suggested_fixes),
			'artifacts': list(self.artifacts),
			'scan_id': self.scan_id,
			'url': self.url,
			'mode': self.mode,
			'degraded': list(self.degraded),
		}
