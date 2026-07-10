"""Collect guidance from peer intelligence modules via stable contracts."""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import CandidateGuidance
from ..models import ComponentCandidate, ParsedQuery
from .synthesis import synthesize_guidance


async def collect_guidance(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
	contracts: IntelligenceContracts | None = None,
) -> CandidateGuidance:
	"""Consult all intelligence layers in parallel through stable contracts."""
	c = contracts or IntelligenceContracts.default()

	framework, codebase, design_sense, consistency = await asyncio.gather(
		c.framework.evaluate_component(candidate, repo_root=repo_root),
		asyncio.to_thread(
			c.codebase.evaluate_component,
			candidate,
			repo_root=repo_root,
			parsed_query=parsed_query,
		),
		asyncio.to_thread(
			c.design_sense.evaluate_component,
			candidate,
			parsed_query=parsed_query,
		),
		asyncio.to_thread(
			c.consistency.evaluate_component,
			candidate,
			repo_root=repo_root,
			parsed_query=parsed_query,
		),
	)
	synthesis = synthesize_guidance(
		candidate,
		framework,
		codebase,
		design_sense,
		consistency,
		parsed_query=parsed_query,
	)
	return CandidateGuidance(
		candidate_id=candidate.id,
		framework=framework,
		codebase=codebase,
		design_sense=design_sense,
		consistency=consistency,
		synthesis=synthesis,
	)
