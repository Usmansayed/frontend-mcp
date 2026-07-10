"""Registry of intelligence module contracts — swap implementations without changing orchestration."""
from __future__ import annotations

from dataclasses import dataclass

from .protocols import (
	BrowserIntelligenceContract,
	CodebaseIntelligenceContract,
	ConsistencyIntelligenceContract,
	DesignSenseIntelligenceContract,
	FrameworkIntelligenceContract,
)


@dataclass(frozen=True, slots=True)
class IntelligenceContracts:
	"""Stable contract bundle consumed by Component Intelligence orchestration."""

	framework: FrameworkIntelligenceContract
	codebase: CodebaseIntelligenceContract
	design_sense: DesignSenseIntelligenceContract
	consistency: ConsistencyIntelligenceContract
	browser: BrowserIntelligenceContract

	@classmethod
	def default(cls) -> IntelligenceContracts:
		from navigation.codebase_intelligence.contract import CodebaseIntelligenceAdapter
		from navigation.consistency_intelligence.contract import ConsistencyIntelligenceAdapter
		from navigation.design_sense_intelligence.contract import DesignSenseIntelligenceAdapter
		from navigation.framework_intelligence.contract import FrameworkIntelligenceAdapter
		from navigation.visual_browser_intelligence.contract import BrowserIntelligenceAdapter

		return cls(
			framework=FrameworkIntelligenceAdapter(),
			codebase=CodebaseIntelligenceAdapter(),
			design_sense=DesignSenseIntelligenceAdapter(),
			consistency=ConsistencyIntelligenceAdapter(),
			browser=BrowserIntelligenceAdapter(),
		)
