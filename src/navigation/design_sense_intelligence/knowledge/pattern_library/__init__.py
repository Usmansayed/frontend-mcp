"""Design pattern references — from Knowledge Map sections 5–6."""
from __future__ import annotations

from ...models import ReviewRequest
from .dashboard import DASHBOARD_PATTERNS
from .ecommerce import ECOMMERCE_PATTERNS
from .enterprise import ENTERPRISE_PATTERNS
from .landing import LANDING_PATTERNS
from .mobile import MOBILE_PATTERNS
from .saas import SAAS_PATTERNS

ALL_PATTERNS = (
	SAAS_PATTERNS
	+ DASHBOARD_PATTERNS
	+ LANDING_PATTERNS
	+ ECOMMERCE_PATTERNS
	+ MOBILE_PATTERNS
	+ ENTERPRISE_PATTERNS
)


def match_patterns(request: ReviewRequest) -> list[dict]:
	task = (request.user_task or '').lower()
	scope = request.scope or ''
	matched: list[dict] = []
	for pattern in ALL_PATTERNS:
		if any(kw in task for kw in pattern.get('keywords', [])):
			matched.append(pattern)
		elif pattern.get('scope') and pattern['scope'] == scope:
			matched.append(pattern)
	return matched[:6]
