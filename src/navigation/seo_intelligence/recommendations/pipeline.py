"""Evidence-first recommendation pipeline — all paths consume reasoning_context_v2 (ADR-027)."""

from __future__ import annotations



from typing import Any



from navigation.seo_intelligence.ai_visibility.adapter import AiVisibilityAdapter

from navigation.seo_intelligence.ai_visibility.analysis import detect_ai_readiness

from navigation.seo_intelligence.ai_visibility.enrich import attach_ai_readiness_block

from navigation.seo_intelligence.analysis.cross_analyzer import run_cross_analysis

from navigation.seo_intelligence.analysis.development_practices import detect_development_practices

from navigation.seo_intelligence.analysis.opportunities import detect_opportunities

from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceRef, SeoRecommendation

from navigation.seo_intelligence.reasoning.context_v2 import build_reasoning_context_v2

from navigation.seo_intelligence.reasoning.enrichment import enrich_reasoning_context_v2

from navigation.seo_intelligence.reasoning.ai_reasoner import merge_ai_and_deterministic, try_ai_recommendations

from navigation.seo_intelligence.recommendations.dedupe import dedupe_correlations, dedupe_recommendations

from navigation.seo_intelligence.recommendations.engine import build_recommendations





def run_recommendation_pipeline(

	evidence: list[SeoEvidenceRef],

	*,

	audit_id: str,

	mode: SeoAuditMode = SeoAuditMode.DEVELOPMENT,

	website_url: str = '',

	repo_root: str = '',

	scan_id: str = '',

	providers: dict[str, str] | None = None,

	graph_summary: dict[str, Any] | None = None,

	verification_history: dict[str, Any] | None = None,

	snapshot_diff: dict[str, Any] | None = None,

	previous_audit_id: str = '',

	include_recommendations: bool = True,

	ai_reasoning: bool | None = None,

	include_ai_visibility: bool = True,

) -> tuple[list[SeoRecommendation], list[dict[str, object]], dict[str, Any]]:

	if include_ai_visibility and not any(e.kind.value == 'ai_visibility' for e in evidence):
		derived, _ = AiVisibilityAdapter().derive(evidence, base_url=website_url)
		if derived:
			evidence = evidence + derived

	correlations = run_cross_analysis(evidence, base_url=website_url)

	opportunities = detect_opportunities(evidence, base_url=website_url) if mode == SeoAuditMode.PROFESSIONAL else []

	dev_practices = detect_development_practices(evidence, base_url=website_url) if mode == SeoAuditMode.DEVELOPMENT else []

	ai_readiness = detect_ai_readiness(evidence, base_url=website_url) if include_ai_visibility else []

	all_correlations = dedupe_correlations(correlations + opportunities + dev_practices + ai_readiness)



	reasoning_context_v2 = build_reasoning_context_v2(

		audit_id=audit_id,

		evidence=evidence,

		correlations=all_correlations,

		mode=mode,

		website_url=website_url,

		providers=providers or {},

		graph_summary=graph_summary,

		verification_history=verification_history,

		snapshot_diff=snapshot_diff,

		previous_audit_id=previous_audit_id,

	)



	reasoning_context_v2 = enrich_reasoning_context_v2(

		reasoning_context_v2,

		evidence=evidence,

		repo_root=repo_root,

		scan_id=scan_id,

		base_url=website_url,

		include_crg=mode == SeoAuditMode.PROFESSIONAL,

		fast_codebase=mode == SeoAuditMode.DEVELOPMENT,

	)

	if include_ai_visibility:

		reasoning_context_v2 = attach_ai_readiness_block(reasoning_context_v2, evidence=evidence)



	recommendations: list[SeoRecommendation] = []

	if include_recommendations:

		deterministic = build_recommendations(

			evidence,

			all_correlations,

			reasoning_units=reasoning_context_v2.get('reasoning_units') or [],

		)

		effective_ai = ai_reasoning

		if effective_ai is None and mode == SeoAuditMode.DEVELOPMENT:

			effective_ai = False

		ai_recs, ai_meta = try_ai_recommendations(

			reasoning_context_v2,

			evidence,

			ai_reasoning=effective_ai,

		)

		reasoning_context_v2['ai_reasoning'] = ai_meta

		if ai_recs is not None:
			reasoning_context_v2['sprint'] = 'agent_ready_v4'
			merged = merge_ai_and_deterministic(ai_recs, deterministic)
			recommendations = dedupe_recommendations(merged)
		else:

			recommendations = dedupe_recommendations(deterministic)



	return recommendations, all_correlations, reasoning_context_v2

