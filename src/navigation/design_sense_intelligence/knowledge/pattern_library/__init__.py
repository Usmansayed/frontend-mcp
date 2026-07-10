"""Design pattern references — not components, but layout/UX archetypes."""
from __future__ import annotations

from .saas import SAAS_PATTERNS
from .dashboard import DASHBOARD_PATTERNS
from .landing import LANDING_PATTERNS
from .ecommerce import ECOMMERCE_PATTERNS
from .mobile import MOBILE_PATTERNS
from .enterprise import ENTERPRISE_PATTERNS

from ...models import ReviewRequest

ALL_PATTERNS = (
	SAAS_PATTERNS + DASHBOARD_PATTERNS + LANDING_PATTERNS + ECOMMERCE_PATTERNS + MOBILE_PATTERNS + ENTERPRISE_PATTERNS
)


def match_patterns(request: ReviewRequest) -> list[dict]:
	task = (request.user_task or '').lower()
	matched: list[dict] = []
	for pattern in ALL_PATTERNS:
		if any(kw in task for kw in pattern.get('keywords', [])):
			matched.append(pattern)
	return matched[:5]
