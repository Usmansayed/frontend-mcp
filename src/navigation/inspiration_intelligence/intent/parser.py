"""Intent parsing — agent query → structured InspirationIntent."""
from __future__ import annotations

import re

from navigation.inspiration_intelligence.models import InspirationIntent, InspirationIntentKind

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
	kind: InspirationIntentKind | None = None,
	repo_root: str = '',
	project_id: str = 'default',
) -> InspirationIntent:
	text = (query or '').strip().lower()
	resolved = kind or _infer_kind(text)
	styles = [tag for word, tag in _STYLE_HINTS.items() if word in text]
	return InspirationIntent(
		kind=resolved,
		raw_query=query,
		target_styles=styles,
		project_id=project_id,
		repo_root=repo_root,
	)


def _infer_kind(text: str) -> InspirationIntentKind:
	if re.search(r'\b(compare|diff|match)\b', text):
		return InspirationIntentKind.COMPARE
	if re.search(r'\b(learn|ingest)\b', text) or re.search(r'\blearn[\s-]?patterns?\b', text):
		return InspirationIntentKind.LEARN_PATTERNS
	if re.search(r'\b(reuse|component|install|pattern)\b', text):
		return InspirationIntentKind.REUSE_PATTERN
	return InspirationIntentKind.INSPIRE
