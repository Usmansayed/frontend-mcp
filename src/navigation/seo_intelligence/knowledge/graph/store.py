"""Persistent SEO Knowledge Graph — normalized evidence, not raw provider dumps."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation

DEFAULT_GRAPH_PATH = Path(os.environ.get('SEO_GRAPH_PATH', '.cache/seo_graph.json'))


class SeoKnowledgeGraphStore:
	def __init__(self, *, path: Path | None = None) -> None:
		self._path = path or DEFAULT_GRAPH_PATH
		self._data: dict[str, Any] | None = None

	def load(self) -> dict[str, Any]:
		if self._data is not None:
			return self._data
		if self._path.is_file():
			try:
				self._data = json.loads(self._path.read_text(encoding='utf-8'))
				return self._data
			except json.JSONDecodeError:
				pass
		self._data = self._empty_graph()
		return self._data

	def save(self) -> None:
		data = self.load()
		data['updated_at'] = time.time()
		self._path.parent.mkdir(parents=True, exist_ok=True)
		self._path.write_text(json.dumps(data, indent=2), encoding='utf-8')

	def _empty_graph(self) -> dict[str, Any]:
		return {
			'version': 1,
			'updated_at': time.time(),
			'website': None,
			'providers': {pid: meta.to_dict() for pid, meta in SEED_PROVIDERS.items()},
			'pages': {},
			'queries': {},
			'issues': {},
			'evidence': {},
			'opportunities': {},
			'recommendations': {},
			'verification': {},
		}

	def set_website(self, url: str, *, property_url: str = '') -> None:
		data = self.load()
		data['website'] = {'url': url, 'property_url': property_url, 'updated_at': time.time()}

	def upsert_evidence(self, evidence: SeoEvidenceRef) -> None:
		data = self.load()
		bucket: dict[str, Any] = data.setdefault('evidence', {})
		bucket[evidence.evidence_id] = evidence.to_dict()
		kind = evidence.kind.value
		if kind == 'search_query':
			queries: dict[str, Any] = data.setdefault('queries', {})
			queries[evidence.evidence_id] = bucket[evidence.evidence_id]
		elif kind in ('crawl_issue', 'technical_issue', 'rendering_issue'):
			issues: dict[str, Any] = data.setdefault('issues', {})
			issues[evidence.evidence_id] = bucket[evidence.evidence_id]

	def upsert_recommendation(self, rec: SeoRecommendation) -> None:
		data = self.load()
		recommendations: dict[str, Any] = data.setdefault('recommendations', {})
		recommendations[rec.recommendation_id] = rec.to_dict()

	def record_verification(self, recommendation_id: str, status: str, *, notes: str = '') -> None:
		data = self.load()
		verification: dict[str, Any] = data.setdefault('verification', {})
		verification[recommendation_id] = {
			'status': status,
			'notes': notes,
			'verified_at': time.time(),
		}

	def summary(self) -> dict[str, Any]:
		data = self.load()
		return {
			'website': data.get('website'),
			'provider_count': len(data.get('providers') or {}),
			'evidence_count': len(data.get('evidence') or {}),
			'issue_count': len(data.get('issues') or {}),
			'query_count': len(data.get('queries') or {}),
			'recommendation_count': len(data.get('recommendations') or {}),
			'updated_at': data.get('updated_at'),
			'path': str(self._path),
		}
