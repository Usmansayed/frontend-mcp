"""Design Sense guidance for component foundation selection."""
from __future__ import annotations

from navigation.component_intelligence.integration_models import DesignSenseGuidance
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery


def evaluate_component(
	candidate: ComponentCandidate,
	*,
	parsed_query: ParsedQuery | None = None,
) -> DesignSenseGuidance:
	degraded = ['design_sense_guidance_heuristic']
	notes: list[str] = []

	ux = 'neutral'
	layout = ''
	interaction = ''

	if parsed_query:
		if parsed_query.page_context and candidate.category == 'block':
			layout = 'prefer_block_for_page_context'
			ux = 'block-level foundation suits section/page request'
		elif parsed_query.page_context:
			layout = 'consider_block_over_primitive_for_page_context'
		if parsed_query.animations:
			interaction = 'prefer_motion_capable_component'
			if not any(k in candidate.name.lower() for k in ('motion', 'animated', 'hover')):
				notes.append('request asks for animation; candidate may need motion additions')
		if parsed_query.styles:
			ux = f'style_intent:{",".join(parsed_query.styles[:3])}'
	else:
		ux = 'insufficient_query_context_for_ux_recommendation'

	return DesignSenseGuidance(
		ux_recommendation=ux,
		layout_recommendation=layout,
		interaction_recommendation=interaction,
		notes=notes,
		degraded=degraded,
	)
