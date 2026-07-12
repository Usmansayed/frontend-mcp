"""Persistent SEO Knowledge Graph — evidence-first page graph + audit snapshots (ADR-027)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.knowledge.graph.pages import merge_page_entity, page_entity_from_evidence
from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation

DEFAULT_GRAPH_PATH = Path(os.environ.get('SEO_GRAPH_PATH', '.cache/seo_graph.json'))
GRAPH_VERSION = 2


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
			'version': GRAPH_VERSION,
			'updated_at': time.time(),
			'website': None,
			'providers': {pid: meta.to_dict() for pid, meta in SEED_PROVIDERS.items()},
			'pages': {},
			'queries': {},
			'issues': {},
			'ai_signals': {},
			'evidence': {},
			'opportunities': {},
			'recommendations': {},
			'verification': {},
			'audits': {},
			'latest_audit_id': '',
		}

	def set_website(self, url: str, *, property_url: str = '') -> None:
		data = self.load()
		data['website'] = {'url': url, 'property_url': property_url, 'updated_at': time.time()}

	def upsert_evidence(self, evidence: SeoEvidenceRef, *, base_url: str = '') -> None:
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
		elif kind == 'ai_visibility':
			ai_signals: dict[str, Any] = data.setdefault('ai_signals', {})
			ai_signals[evidence.evidence_id] = bucket[evidence.evidence_id]

		page_key = page_url_for_evidence(evidence, base_url=base_url) or '__site__'
		pages: dict[str, Any] = data.setdefault('pages', {})
		incoming = page_entity_from_evidence(page_key, [evidence], base_url=base_url)
		incoming['updated_at'] = time.time()
		if page_key in pages:
			pages[page_key] = merge_page_entity(pages[page_key], incoming)
		else:
			pages[page_key] = incoming

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

	def save_audit_snapshot(
		self,
		audit_id: str,
		*,
		evidence: list[SeoEvidenceRef],
		recommendations: list[SeoRecommendation],
		reasoning_context_v2: dict[str, Any],
		mode: str,
		providers_queried: list[str],
	) -> None:
		data = self.load()
		audits: dict[str, Any] = data.setdefault('audits', {})
		audits[audit_id] = {
			'audit_id': audit_id,
			'collected_at': time.time(),
			'mode': mode,
			'providers_queried': list(providers_queried),
			'evidence_ids': [e.evidence_id for e in evidence],
			'evidence': {e.evidence_id: e.to_dict() for e in evidence},
			'recommendation_ids': [r.recommendation_id for r in recommendations],
			'recommendations': {r.recommendation_id: r.to_dict() for r in recommendations},
			'reasoning_context_v2': reasoning_context_v2,
		}
		data['latest_audit_id'] = audit_id

	def get_audit_snapshot(self, audit_id: str) -> dict[str, Any] | None:
		data = self.load()
		audit = (data.get('audits') or {}).get(audit_id)
		return audit if isinstance(audit, dict) else None

	def latest_audit_id(self) -> str:
		return str(self.load().get('latest_audit_id') or '')

	def previous_audit_id(self, current_audit_id: str) -> str:
		data = self.load()
		audits = data.get('audits') or {}
		ids = sorted(
			audits.keys(),
			key=lambda aid: float((audits[aid] or {}).get('collected_at') or 0),
		)
		if current_audit_id in ids:
			idx = ids.index(current_audit_id)
			if idx > 0:
				return ids[idx - 1]
		return ids[-2] if len(ids) >= 2 else ''

	def build_snapshot_diff(
		self,
		current_audit_id: str,
		previous_audit_id: str,
	) -> dict[str, Any] | None:
		if not previous_audit_id:
			return None
		prev = self.get_audit_snapshot(previous_audit_id)
		curr = self.get_audit_snapshot(current_audit_id)
		if not prev or not curr:
			return None

		prev_evidence = prev.get('evidence') or {}
		curr_evidence = curr.get('evidence') or {}
		improved: list[str] = []
		degraded: list[str] = []
		unchanged: list[str] = []

		all_ids = set(prev_evidence) | set(curr_evidence)
		for eid in sorted(all_ids):
			before = prev_evidence.get(eid)
			after = curr_evidence.get(eid)
			if before and not after:
				improved.append(eid)
			elif after and not before:
				degraded.append(eid)
			elif before and after:
				if _severity_rank(after.get('severity')) < _severity_rank(before.get('severity')):
					improved.append(eid)
				elif _severity_rank(after.get('severity')) > _severity_rank(before.get('severity')):
					degraded.append(eid)
				else:
					unchanged.append(eid)

		return {
			'previous_audit_id': previous_audit_id,
			'current_audit_id': current_audit_id,
			'evidence_improved': improved,
			'evidence_degraded': degraded,
			'evidence_unchanged': unchanged,
		}

	def summary(self) -> dict[str, Any]:
		data = self.load()
		return {
			'website': data.get('website'),
			'provider_count': len(data.get('providers') or {}),
			'evidence_count': len(data.get('evidence') or {}),
			'page_count': len(data.get('pages') or {}),
			'issue_count': len(data.get('issues') or {}),
			'query_count': len(data.get('queries') or {}),
			'recommendation_count': len(data.get('recommendations') or {}),
			'audit_count': len(data.get('audits') or {}),
			'latest_audit_id': data.get('latest_audit_id'),
			'updated_at': data.get('updated_at'),
			'path': str(self._path),
			'graph_version': data.get('version'),
		}


def _severity_rank(severity: Any) -> int:
	return {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}.get(str(severity or 'info'), 0)
