"""Stable contracts for cross-intelligence orchestration."""
from .protocols import (
	BrowserIntelligenceContract,
	CodebaseIntelligenceContract,
	CONTRACT_VERSION,
	ConsistencyIntelligenceContract,
	DesignSenseIntelligenceContract,
	FrameworkIntelligenceContract,
)
from .registry import IntelligenceContracts

__all__ = [
	'CONTRACT_VERSION',
	'BrowserIntelligenceContract',
	'CodebaseIntelligenceContract',
	'ConsistencyIntelligenceContract',
	'DesignSenseIntelligenceContract',
	'FrameworkIntelligenceContract',
	'IntelligenceContracts',
]
