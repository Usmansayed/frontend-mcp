"""Intent parsing — agent query → structured FigmaIntent."""
from __future__ import annotations

import re

from navigation.figma_intelligence.models import FigmaIntent, FigmaIntentKind

_STYLE_HINTS = {
	'dashboard': 'dashboard',
	'saas': 'saas',
	'mobile': 'mobile',
	'landing': 'landing',
	'ecommerce': 'ecommerce',
	'admin': 'admin',
	'onboarding': 'onboarding',
}


def parse_intent(
	query: str,
	*,
	kind: FigmaIntentKind | None = None,
	repo_root: str = '',
	project_id: str = 'default',
) -> FigmaIntent:
	text = (query or '').strip().lower()
	resolved = kind or _infer_kind(text)
	styles = [tag for word, tag in _STYLE_HINTS.items() if word in text]
	return FigmaIntent(
		kind=resolved,
		raw_query=query,
		target_styles=styles,
		project_id=project_id,
		repo_root=repo_root,
	)


def _infer_kind(text: str) -> FigmaIntentKind:
	if re.search(r'\b(token|variable|design[\s-]?system)\b', text):
		return FigmaIntentKind.EXTRACT_DS
	if re.search(r'\b(compare|diff|match)\b', text):
		return FigmaIntentKind.COMPARE
	if re.search(r'\b(component|reuse|install)\b', text):
		return FigmaIntentKind.REUSE_COMPONENT
	if re.search(r'\b(pattern|learn|ingest)\b', text):
		return FigmaIntentKind.LEARN_PATTERNS
	return FigmaIntentKind.INSPIRE
