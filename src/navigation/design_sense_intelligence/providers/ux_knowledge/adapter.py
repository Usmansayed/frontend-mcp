"""UX Knowledge Brain provider — universal playbooks/principles for Design Sense.

Peer to Project Design Graph (Consistency). Does not merge into PDG.
Maps ReviewRequest → deterministic ux.retrieve traversal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ...models import FindingSeverity, ProviderContribution, ReviewFinding, ReviewRequest
from .mapping import build_retrieval_params


class UxKnowledgeProvider:
	"""Subjective knowledge provider backed by ForOpenCode UX KB (no embeddings)."""

	name = 'ux_knowledge'
	kind = 'knowledge'
	lane = 'subjective'

	def __init__(self, *, max_principle_findings: int = 5, max_conflict_findings: int = 3) -> None:
		self._max_principles = max_principle_findings
		self._max_conflicts = max_conflict_findings

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		params = build_retrieval_params(request)
		if not params:
			return ProviderContribution(
				provider=self.name,
				degraded=['ux_knowledge_no_surface'],
				notes=['ux_kb:skipped_no_surface'],
			)

		repo_root = (request.repo_root or '').strip() or None
		# Prefer repo ForOpenCode when present; otherwise packaged corpus ships with the wheel.
		if repo_root and not _repo_corpus_present(repo_root) and not _packaged_corpus_present():
			return ProviderContribution(
				provider=self.name,
				degraded=['ux_knowledge_missing_corpus'],
				notes=[f'ux_kb:missing_corpus:{repo_root}'],
			)

		try:
			from navigation.ux_knowledge.retrieval_engine import retrieve_ux_knowledge
		except ImportError as exc:
			return ProviderContribution(
				provider=self.name,
				degraded=[f'ux_knowledge_import_error:{type(exc).__name__}'],
			)

		try:
			result = retrieve_ux_knowledge(params, repo_root=repo_root)
		except Exception as exc:  # noqa: BLE001
			return ProviderContribution(
				provider=self.name,
				degraded=[f'ux_knowledge_error:{type(exc).__name__}'],
				notes=[f'ux_kb:error:{exc}'[:200]],
			)

		return _contribution_from_retrieval(result, params=params, max_principles=self._max_principles, max_conflicts=self._max_conflicts)


def _repo_corpus_present(repo_root: str) -> bool:
	from navigation.ux_knowledge.paths import corpus_usable

	root = Path(repo_root)
	return corpus_usable(root / 'ForOpenCode' / '08_graphs', root / 'ForOpenCode' / '09_runtime')


def _packaged_corpus_present() -> bool:
	from navigation.ux_knowledge.paths import corpus_usable, packaged_data_root

	root = packaged_data_root()
	return corpus_usable(root / '08_graphs', root / '09_runtime')


def _contribution_from_retrieval(
	result: dict[str, Any],
	*,
	params: dict[str, Any],
	max_principles: int,
	max_conflicts: int,
) -> ProviderContribution:
	meta = result.get('meta') or {}
	pb = result.get('matched_playbook') or {}
	notes: list[str] = []
	degraded: list[str] = []
	findings: list[ReviewFinding] = []

	if meta.get('stopped_reason') == 'no_match_fallback' or not pb.get('id'):
		degraded.append('ux_knowledge_no_match')
		notes.append(f'ux_kb:no_match:surface={params.get("surface_type")}')
		return ProviderContribution(provider='ux_knowledge', notes=notes, degraded=degraded)

	pack_id = meta.get('pack_id') or ''
	pb_id = pb.get('id') or ''
	notes.append(f'ux_kb:playbook:{pb_id}')
	if pack_id:
		notes.append(f'ux_kb:pack:{pack_id}')
	notes.append(f'ux_kb:match_score:{pb.get("match_score", 0)}')
	if meta.get('corpus_source'):
		notes.append(f'ux_kb:corpus:{meta.get("corpus_source")}')

	for d in (result.get('decisions') or [])[:4]:
		notes.append(f'ux_kb:decision:{d.get("id")}:{d.get("label", "")[:60]}')

	for p in (result.get('patterns') or [])[:6]:
		notes.append(f'ux_kb:pattern:{p.get("id")}:{p.get("label", "")[:50]}')

	evidence_by_principle: dict[str, str] = {}
	for ev in result.get('evidence') or []:
		pid = ev.get('principle_id') or ''
		quote = (ev.get('quote') or '').strip()
		if pid and quote and pid not in evidence_by_principle:
			evidence_by_principle[pid] = quote[:400]

	for i, princ in enumerate((result.get('principles') or [])[:max_principles]):
		pid = princ.get('id') or f'principle_{i}'
		title = princ.get('title') or pid
		rule = (princ.get('rule') or '').strip()
		detect = (princ.get('detect') or '').strip()
		strength = int(princ.get('evidence_strength') or 2)
		quote = evidence_by_principle.get(pid, '')
		severity = (
			FindingSeverity.MAJOR.value
			if strength >= 4 and detect
			else FindingSeverity.ADVISORY.value
		)
		findings.append(
			ReviewFinding(
				id=f'ux_kb_{pid}',
				category='ux_knowledge',
				severity=severity,
				message=f'Apply principle: {title}',
				rationale=rule[:500] if rule else f'From playbook {pb_id}',
				recommendation=detect[:400] if detect else rule[:300],
				source='ux_knowledge',
				evidence=quote or detect[:300],
				confidence=float(princ.get('confidence') or 0.75),
				metadata={
					'principle_id': pid,
					'playbook_id': pb_id,
					'pack_id': pack_id,
					'evidence_strength': strength,
					'contract': 'ux.retrieve_v1',
				},
			)
		)

	for c in (result.get('conflicts') or [])[:max_conflicts]:
		a, b = c.get('a') or '', c.get('b') or ''
		hint = (c.get('decision_hint') or '').strip()
		findings.append(
			ReviewFinding(
				id=f'ux_kb_conflict_{a}_{b}'[:80],
				category='ux_knowledge_conflict',
				severity=FindingSeverity.ADVISORY.value,
				message=f'Principle tension: {a} ↔ {b}',
				rationale=hint or 'Conflicting principles retrieved for this surface — choose explicitly.',
				recommendation=hint or 'Document which principle wins for this surface and why.',
				source='ux_knowledge',
				evidence=hint,
				confidence=0.8,
				metadata={'conflict_a': a, 'conflict_b': b, 'playbook_id': pb_id},
			)
		)

	degraded.append('ux_knowledge_structured')
	return ProviderContribution(
		provider='ux_knowledge',
		findings=findings,
		notes=notes,
		degraded=degraded,
	)
