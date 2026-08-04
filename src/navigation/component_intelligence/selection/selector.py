"""Choose foundation LIBRARY first; optional starter component second.

Durable contract (closes Test 10–12 whack-a-mole):
  - Lock unit = library id (@shadcn, …), never aceternity/calendar/forgot-password blocks
  - Search results may supply an optional starter *inside* that library
  - Specialty packs only when the host explicitly asks
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..contracts import IntelligenceContracts
from ..guidance.collectors import collect_guidance
from ..guidance.synthesis import rank_key
from ..integration_models import CandidateGuidance, FoundationSelection
from ..models import ComponentCandidate, ParsedQuery
from .filter import (
	SELECT_MIN_RELEVANCE,
	_is_auth_oriented,
	is_chrome_only_matched_query,
	is_generic_matched_query,
	is_weak_foundation_candidate,
)
from .library_lock import (
	make_library_candidate,
	normalize_library_id,
	registry_matches_library,
	resolve_foundation_library,
)


async def select_foundation(
	candidates: list[ComponentCandidate],
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
	max_candidates: int = 12,
	contracts: IntelligenceContracts | None = None,
) -> FoundationSelection:
	page_context = list(parsed_query.page_context) if parsed_query else []
	resolution = resolve_foundation_library(repo_root, parsed_query)
	if resolution.refused or not resolution.library_id:
		return FoundationSelection(
			chosen=None,
			library_id=None,
			guidance=None,
			runner_ups=[],
			rationale=(
				resolution.refuse_reason
				or "Could not resolve a foundation library — do not lock foundation."
			),
			degraded=["foundation_library_unresolved"],
			usable=False,
			reject_reason=resolution.refuse_reason or "library_unresolved",
			lock_evidence=list(resolution.evidence),
		)

	library_id = normalize_library_id(resolution.library_id) or resolution.library_id
	library_candidate = make_library_candidate(
		library_id,
		confidence=resolution.confidence,
		evidence=resolution.evidence,
	)

	starters = _eligible_starters(
		candidates,
		library_id=library_id,
		parsed_query=parsed_query,
		page_context=page_context,
	)[: max(3, max_candidates)]

	degraded: list[str] = []
	starter: ComponentCandidate | None = None
	guidance: CandidateGuidance | None = None
	runner_ups: list[ComponentCandidate] = []

	if starters:
		guided: list[tuple[ComponentCandidate, CandidateGuidance]] = []
		guidance_tasks = [
			collect_guidance(
				candidate,
				repo_root=repo_root,
				parsed_query=parsed_query,
				contracts=contracts,
			)
			for candidate in starters[:3]
		]
		guidance_results = await asyncio.gather(*guidance_tasks, return_exceptions=True)
		for candidate, result in zip(starters[:3], guidance_results, strict=True):
			if isinstance(result, BaseException):
				degraded.append(f"guidance_error:{candidate.id}")
				continue
			guided.append((candidate, result))
			for layer in (result.framework, result.codebase, result.design_sense, result.consistency):
				degraded.extend(layer.degraded)

		eligible = [(c, g) for c, g in guided if g.synthesis.eligible] or guided
		if eligible:
			eligible.sort(
				key=lambda pair: rank_key(
					pair[0],
					pair[1],
					parsed_query=parsed_query,
					page_context=page_context,
				)
			)
			starter, guidance = eligible[0]
			runner_ups = [c for c, _ in eligible[1:4]]

	# HARD INVARIANT: chosen is always the library lock — never a specialty/auth block.
	rationale = (
		f"Locked foundation library {library_id} "
		f"(evidence: {', '.join(resolution.evidence) or 'default'}). "
	)
	if starter is not None:
		rationale += (
			f"Optional starter within library: {starter.title} "
			f"(rel {starter.relevance_score:.2f}). "
		)
	else:
		rationale += (
			"No in-library starter from search — library lock still valid; "
			"use perception_search_components for blocks. "
		)
	# Library lock without a starter previously left guidance=None and crashed
	# perception_integrate_component (selection.guidance.codebase).
	if guidance is None:
		from ..integration_models import (
			CodebaseGuidance,
			ConsistencyGuidance,
			DesignSenseGuidance,
			FrameworkGuidance,
			SynthesisResult,
		)

		guidance = CandidateGuidance(
			candidate_id=library_candidate.id,
			framework=FrameworkGuidance(compatible=True),
			codebase=CodebaseGuidance(),
			design_sense=DesignSenseGuidance(
				notes=["library_lock_without_starter_guidance"],
			),
			consistency=ConsistencyGuidance(),
			synthesis=SynthesisResult(
				eligible=True,
				summary=f"Foundation library {library_id} locked; no starter guidance collected.",
			),
		)
	else:
		rationale += guidance.synthesis.summary

	return FoundationSelection(
		chosen=library_candidate,
		library_id=library_id,
		starter=starter,
		guidance=guidance,
		runner_ups=runner_ups,
		rationale=rationale.strip(),
		degraded=list(dict.fromkeys(degraded)),
		usable=True,
		reject_reason=None,
		lock_evidence=list(resolution.evidence),
	)


def _eligible_starters(
	candidates: list[ComponentCandidate],
	*,
	library_id: str,
	parsed_query: ParsedQuery | None,
	page_context: list[str],
) -> list[ComponentCandidate]:
	"""Starters must live inside the locked library and not be weak packs."""
	out: list[ComponentCandidate] = []
	for c in candidates:
		if float(c.relevance_score or 0) < SELECT_MIN_RELEVANCE:
			continue
		if not registry_matches_library(c, library_id):
			continue
		if is_weak_foundation_candidate(
			c, parsed_query=parsed_query, page_context=page_context
		):
			continue
		# Auth blocks never starters on content pages.
		if page_context and _is_auth_oriented(c):
			contexts = [str(p).lower() for p in page_context]
			if "auth" not in contexts and "login" not in contexts:
				continue
		# Chrome-only matched queries are weak starters for content pages.
		if page_context and is_chrome_only_matched_query(c):
			raw = (parsed_query.raw or "").lower() if parsed_query else ""
			if not any(k in raw for k in ("navbar", "header", "footer", "nav", "sidebar")):
				continue
		# Generic-token matches (button→calendar) are not useful starters on content pages.
		if page_context and is_generic_matched_query(c):
			raw = (parsed_query.raw or "").lower() if parsed_query else ""
			mq = str((c.metadata or {}).get("matched_query") or "").lower()
			if mq and mq not in raw:
				continue
		# Prefer real UI primitives over blocks as starters.
		cat = str(c.category or "").lower()
		item = str(c.item_type or "").lower()
		if cat in ("library",):
			continue
		if cat in ("block", "page") and "block" in item:
			# Allow simple single-purpose blocks from foundation registry only if not composite.
			from .filter import is_composite_marketing_block

			if is_composite_marketing_block(c):
				continue
		out.append(c)

	out.sort(
		key=lambda c: (
			0 if c.category == "component" or str(c.item_type or "") in ("registry:ui", "ui") else 1,
			-float(c.relevance_score or 0),
		)
	)
	return out
