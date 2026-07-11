"""Consistency Intelligence — design knowledge engine facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.consistency_intelligence.consumers import ConsistencyAuditor, ConsistencyValidator, FixProposer
from navigation.consistency_intelligence.discovery.merge import MergeStats
from navigation.consistency_intelligence.graph.model import ProjectDesignGraph
from navigation.consistency_intelligence.graph.persistence import GraphStore
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.knowledge.envelope import KnowledgeResponse

from .models import ConsistencyReport


def _project_id_from_url(url: str | None) -> str:
	if not url:
		return 'default'
	from urllib.parse import urlparse

	parsed = urlparse(url)
	host = parsed.netloc or 'default'
	path = (parsed.path or '/').strip('/').split('/')[0] or 'root'
	return f'{host}_{path}'


def _build_pipeline():
	from navigation.consistency_intelligence.discovery import DiscoveryPipeline
	from navigation.consistency_intelligence.discovery.sources.codebase import CodebaseKnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.context7 import Context7KnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.figma import FigmaKnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.opendesign import OpenDesignKnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.snapshot import SnapshotKnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.tokens import TokensKnowledgeSource
	from navigation.consistency_intelligence.discovery.sources.user_corrections import UserCorrectionsKnowledgeSource

	return DiscoveryPipeline([
		SnapshotKnowledgeSource(),
		CodebaseKnowledgeSource(),
		TokensKnowledgeSource(),
		FigmaKnowledgeSource(),
		OpenDesignKnowledgeSource(),
		Context7KnowledgeSource(),
		UserCorrectionsKnowledgeSource(),
	])


class ConsistencyIntelligenceService:
	"""Project design knowledge engine — graph + Knowledge API."""

	def __init__(self, *, repo_root: str | Path | None = None) -> None:
		root = Path(repo_root) if repo_root else None
		self._store = GraphStore(storage_root=root)
		self._api = KnowledgeAPI(self._store)

	@property
	def knowledge(self) -> KnowledgeAPI:
		return self._api

	def query(
		self,
		query_id: str,
		params: dict[str, Any] | None = None,
		*,
		project_id: str = 'default',
	) -> KnowledgeResponse:
		return self._api.query(query_id, params, project_id=project_id, repo_root=self._store.storage_root)

	def graph_summary(self, *, project_id: str = 'default') -> KnowledgeResponse:
		return self._api.summary(project_id=project_id, repo_root=self._store.storage_root)

	def load_graph(self, project_id: str = 'default') -> ProjectDesignGraph:
		return self._api.load_graph(project_id, repo_root=self._store.storage_root)

	def list_queries(self) -> list[dict[str, Any]]:
		return self._api.list_queries()

	async def refresh_graph(
		self,
		*,
		project_id: str = 'default',
		design_snapshot: Any | None = None,
		scan_id: str | None = None,
		enabled_sources: frozenset[str] | None = None,
		repo_root: str | Path | None = None,
		options: dict[str, Any] | None = None,
	) -> tuple[ProjectDesignGraph, list[str], MergeStats]:
		"""Run Discovery Pipeline — ingest knowledge from enabled sources."""
		from navigation.consistency_intelligence.discovery import DiscoveryContext

		storage_root = Path(repo_root) if repo_root else self._store.storage_root
		graph = self.load_graph(project_id)
		if storage_root is not None and not graph.meta.repo_root:
			graph.meta.repo_root = str(storage_root)

		ctx = DiscoveryContext(
			project_id=project_id,
			repo_root=storage_root,
			design_snapshot=design_snapshot,
			scan_id=scan_id,
			enabled_sources=enabled_sources or frozenset({
				'snapshot', 'codebase', 'tokens', 'figma', 'opendesign', 'context7', 'user_corrections',
			}),
			options=dict(options or {}),
		)
		pipeline = _build_pipeline()
		graph, degraded, stats = await pipeline.run(ctx, graph)
		self._store.save(graph)
		return graph, degraded, stats

	@property
	def validator(self) -> ConsistencyValidator:
		return ConsistencyValidator(self._api)

	@property
	def fix_proposer(self) -> FixProposer:
		return FixProposer(self._api)

	@property
	def auditor(self) -> ConsistencyAuditor:
		return ConsistencyAuditor(self.validator)

	def assess_consistency(
		self,
		*,
		selector: str,
		actual: dict[str, str],
		context: str | None = None,
		properties: list[str] | None = None,
		project_id: str = 'default',
	) -> ConsistencyReport:
		assess, explain = self.validator.assess_with_explanation(
			selector=selector,
			actual=actual,
			context=context,
			properties=properties,
			project_id=project_id,
		)
		return self.validator.to_report(assess, explain)

	def audit_snapshot(
		self,
		snapshot: Any,
		*,
		project_id: str = 'default',
		max_elements: int = 40,
	) -> ConsistencyReport:
		"""Batch audit snapshot elements against Project Design Graph."""
		report, _ = self.auditor.audit_snapshot(
			snapshot, project_id=project_id, max_elements=max_elements,
		)
		return report

	def audit_snapshot_detail(
		self,
		snapshot: Any,
		*,
		project_id: str = 'default',
		max_elements: int = 40,
	) -> dict[str, Any]:
		return self.auditor.audit_report_with_groups(
			snapshot, project_id=project_id, max_elements=max_elements,
		)

	def propose_fix(
		self,
		*,
		standard_id: str,
		selector: str = '',
		actual: dict[str, str] | None = None,
		project_id: str = 'default',
	) -> KnowledgeResponse:
		return self.fix_proposer.recommend(
			standard_id=standard_id,
			selector=selector,
			actual=actual,
			project_id=project_id,
		)

	def audit(self, snapshot: Any = None) -> ConsistencyReport:
		"""Audit snapshot against populated graph (refresh first if needed)."""
		if snapshot is None:
			return ConsistencyReport(
				passed=True,
				summary='No snapshot provided.',
				degraded=['audit_no_snapshot'],
			)
		project_id = _project_id_from_url(getattr(snapshot, 'url', None))
		graph = self.load_graph(project_id)
		stats = self._store.summary_stats(graph)
		if stats['standard_count'] == 0 and stats['component_count'] == 0:
			return ConsistencyReport(
				passed=True,
				summary='Graph empty — run perception_design_graph_refresh first.',
				degraded=['graph_empty_run_refresh'],
			)
		return self.audit_snapshot(snapshot, project_id=project_id)
