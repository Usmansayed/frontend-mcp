"""Design Reference Registry — store and compare structured design snapshots."""
from __future__ import annotations

from navigation.design_reference_registry.comparison import compare_snapshots, find_similar_references
from navigation.design_reference_registry.models import ReferenceEntry, SnapshotComparison
from navigation.design_reference_registry.registry import DesignReferenceRegistry

__all__ = [
	'DesignReferenceRegistry',
	'ReferenceEntry',
	'SnapshotComparison',
	'compare_snapshots',
	'find_similar_references',
]
