"""Candidate filtering before cross-module guidance."""
from __future__ import annotations

from ..models import ComponentCandidate, ParsedQuery

# Admit floor for raw search noise (provider may return weak hits).
DEFAULT_MIN_SCORE = 0.12
# Select/search-sufficiency floor — below this, do not lock foundation (Test 10: 0.29 auth block).
SELECT_MIN_RELEVANCE = 0.35
# Foundation select prefers reusable UI primitives over marketing composition blocks.
PREFER_COMPONENT_FOR_FOUNDATION = True

_AUTH_MARKERS = (
	"forgot-password",
	"forgot_password",
	"login",
	"sign-in",
	"signin",
	"sign-up",
	"signup",
	"password-reset",
	"password_reset",
	"otp",
	"2fa",
)
_NON_AUTH_PAGE_CONTEXTS = frozenset({
	"portfolio",
	"marketing",
	"landing page",
	"about",
	"blog",
	"dashboard",
	"settings",
	"checkout",
	"onboarding",
})
# Single-token planned queries that inflate scores for unrelated registry items
# (Test 11: calendar-10 matched_query="button" at rel 1.0 on portfolio about).
_GENERIC_MATCH_QUERIES = frozenset({
	"button",
	"cta",
	"action button",
	"input",
	"ui",
	"interactive",
	"layout",
	"content",
	"card",
	"panel",
	"tile",
})
# Chrome-only matches are shell pieces, not a design-system foundation
# (Test 12: aceternity hero+navbar via matched_query "navbar").
_CHROME_ONLY_QUERIES = frozenset({
	"navbar",
	"nav",
	"header",
	"footer",
	"menubar",
	"sidebar",
	"navigation",
	"floating-navbar",
})
_CONTEXT_AFFINITY_MARKERS: dict[str, tuple[str, ...]] = {
	"portfolio": ("portfolio", "about", "hero", "gallery", "project", "work", "showcase"),
	"about": ("about", "bio", "profile", "story", "portfolio", "hero", "team"),
	"marketing": ("marketing", "landing", "hero", "pricing", "cta", "feature"),
	"landing page": ("landing", "hero", "marketing", "feature"),
	"dashboard": ("dashboard", "analytics", "admin", "sidebar", "overview"),
	"blog": ("blog", "article", "post", "content"),
	"checkout": ("checkout", "cart", "payment", "commerce"),
	"onboarding": ("onboarding", "welcome", "setup", "getting started"),
	"settings": ("settings", "preferences", "account"),
}
# Core libraries suitable as project foundations (not specialty effect packs).
FOUNDATION_REGISTRIES = frozenset({
	"@shadcn",
	"shadcn",
	"@ui",
	"@radix-ui",
})
# Specialty registries — fine for search, weak as default foundation locks.
DECORATIVE_REGISTRIES = frozenset({
	"@aceternity",
	"@magicui",
	"@kokonutui",
	"@cult-ui",
	"@motion-primitives",
})
_SPECIALTY_QUERY_MARKERS = (
	"aceternity",
	"magicui",
	"magic ui",
	"kokonut",
	"glassmorphism",
	"glass ",
	"animated",
	"premium block",
	"motion primitive",
)


def _candidate_blob(candidate: ComponentCandidate) -> str:
	return " ".join(
		[
			str(candidate.id or ""),
			str(candidate.name or ""),
			str(candidate.title or ""),
			str(candidate.description or ""),
			" ".join(candidate.tags or []),
		]
	).lower()


def _is_auth_oriented(candidate: ComponentCandidate) -> bool:
	return any(m in _candidate_blob(candidate) for m in _AUTH_MARKERS)


def matched_query_text(candidate: ComponentCandidate) -> str:
	meta = candidate.metadata if isinstance(candidate.metadata, dict) else {}
	return str(meta.get("matched_query") or "").strip().lower()


def is_generic_matched_query(candidate: ComponentCandidate) -> bool:
	mq = matched_query_text(candidate)
	if not mq:
		return False
	if mq in _GENERIC_MATCH_QUERIES:
		return True
	tokens = mq.split()
	return len(tokens) == 1 and tokens[0] in _GENERIC_MATCH_QUERIES


def is_chrome_only_matched_query(candidate: ComponentCandidate) -> bool:
	mq = matched_query_text(candidate)
	if not mq:
		return False
	if mq in _CHROME_ONLY_QUERIES:
		return True
	tokens = mq.split()
	return len(tokens) == 1 and tokens[0] in _CHROME_ONLY_QUERIES


def context_affinity(candidate: ComponentCandidate, page_context: list[str] | None) -> float:
	"""1.0 when candidate text overlaps page context; 0.0 when page-contexted with no overlap."""
	contexts = [str(p).lower() for p in (page_context or []) if str(p).strip()]
	if not contexts:
		return 1.0
	blob = _candidate_blob(candidate)
	for ctx in contexts:
		markers = _CONTEXT_AFFINITY_MARKERS.get(ctx, (ctx,))
		if any(m in blob for m in markers):
			return 1.0
	return 0.0


def query_allows_specialty_foundation(parsed_query: ParsedQuery | None) -> bool:
	"""Specialty registries/blocks only win foundation when the host asked for them."""
	if parsed_query is None:
		return False
	raw = f"{parsed_query.raw or ''} {' '.join(parsed_query.styles or [])}".lower()
	return any(m in raw for m in _SPECIALTY_QUERY_MARKERS)


def is_foundation_registry(candidate: ComponentCandidate) -> bool:
	reg = str(candidate.registry or "").strip().lower()
	if not reg:
		return False
	if not reg.startswith("@"):
		reg = f"@{reg}"
	return reg in {r.lower() for r in FOUNDATION_REGISTRIES} or reg.lstrip("@") in {
		"shadcn",
		"ui",
		"radix-ui",
	}


def is_decorative_registry(candidate: ComponentCandidate) -> bool:
	reg = str(candidate.registry or "").strip().lower()
	if not reg.startswith("@"):
		reg = f"@{reg}"
	return reg in {r.lower() for r in DECORATIVE_REGISTRIES}


def is_composite_marketing_block(candidate: ComponentCandidate) -> bool:
	"""Hero+navbar / section-with-X-and-Y packs are page compositions, not DS foundations."""
	name = str(candidate.name or "").lower()
	title = str(candidate.title or "").lower()
	blob = f"{name} {title}"
	if "hero" in blob and any(k in blob for k in ("navbar", "nav", "header", "menu")):
		return True
	if candidate.category in ("block", "page") or "block" in str(candidate.item_type or ""):
		# Long multi-role composition names from specialty registries.
		if blob.count("-") >= 4 and any(k in blob for k in ("section", "with", "and", "grid")):
			return True
	return False


def foundation_suitability(
	candidate: ComponentCandidate,
	*,
	parsed_query: ParsedQuery | None = None,
	page_context: list[str] | None = None,
) -> int:
	"""Higher = better foundation lock. Used to prefer libraries over page packs."""
	score = 0
	contexts = [str(p).lower() for p in (page_context or [])]
	content_page = bool(contexts) and any(c in _NON_AUTH_PAGE_CONTEXTS for c in contexts)
	allow_specialty = query_allows_specialty_foundation(parsed_query)

	if is_foundation_registry(candidate):
		score += 4
	elif is_decorative_registry(candidate) and not allow_specialty:
		score -= 3

	cat = str(candidate.category or "").lower()
	item = str(candidate.item_type or "").lower()
	if cat == "component" or item in ("registry:ui", "ui"):
		score += 3
	elif cat in ("block", "page") or "block" in item or "page" in item:
		score -= 2

	if is_composite_marketing_block(candidate) and not allow_specialty:
		score -= 6

	if content_page and is_chrome_only_matched_query(candidate):
		raw = (parsed_query.raw or "").lower() if parsed_query else ""
		# Explicit chrome request in the host query is fine.
		if not any(k in raw for k in _CHROME_ONLY_QUERIES):
			score -= 4

	if content_page and context_affinity(candidate, contexts) > 0:
		score += 1

	return score


def is_weak_foundation_candidate(
	candidate: ComponentCandidate,
	*,
	parsed_query: ParsedQuery | None = None,
	page_context: list[str] | None = None,
) -> bool:
	"""True when locking this candidate would misrepresent the project foundation."""
	if query_allows_specialty_foundation(parsed_query):
		return False
	if is_composite_marketing_block(candidate):
		return True
	if is_decorative_registry(candidate) and (
		candidate.category in ("block", "page") or "block" in str(candidate.item_type or "")
	):
		return True
	contexts = [str(p).lower() for p in (page_context or [])]
	if contexts and any(c in _NON_AUTH_PAGE_CONTEXTS for c in contexts):
		raw = (parsed_query.raw or "").lower() if parsed_query else ""
		if is_chrome_only_matched_query(candidate) and not any(k in raw for k in _CHROME_ONLY_QUERIES):
			return True
	return False


def filter_candidates(
	candidates: list[ComponentCandidate],
	*,
	min_score: float = DEFAULT_MIN_SCORE,
	max_count: int = 12,
	page_context: list[str] | None = None,
	parsed_query: ParsedQuery | None = None,
) -> list[ComponentCandidate]:
	"""Reduce search results to a foundation-oriented shortlist."""
	if not candidates:
		return []

	scored = [c for c in candidates if c.relevance_score >= min_score]
	scored.sort(
		key=lambda c: (
			-foundation_suitability(c, parsed_query=parsed_query, page_context=page_context),
			-c.relevance_score,
		)
	)

	contexts = [str(p).lower() for p in (page_context or [])]
	# Portfolio/marketing/about must not prefer auth blocks over weakly related hits.
	if contexts and any(c in _NON_AUTH_PAGE_CONTEXTS for c in contexts):
		if "auth" not in contexts:
			non_auth = [c for c in scored if not _is_auth_oriented(c)]
			if non_auth:
				scored = non_auth
		# Prefer context-overlapping candidates; drop generic-query-only misses.
		contextual = [c for c in scored if context_affinity(c, contexts) > 0]
		if contextual:
			# Keep non-context foundation libs too — affinity alone favored aceternity hero packs.
			# Still drop generic-token matches with no context (Test 11 calendar via "button").
			libs = [
				c
				for c in scored
				if is_foundation_registry(c)
				and not is_composite_marketing_block(c)
				and (
					context_affinity(c, contexts) > 0
					or not is_generic_matched_query(c)
				)
			]
			merged: list[ComponentCandidate] = []
			seen: set[str] = set()
			for c in libs + contextual:
				if c.id in seen:
					continue
				# Generic no-affinity hits must not re-enter via contextual false positives.
				if (
					is_generic_matched_query(c)
					and context_affinity(c, contexts) <= 0
				):
					continue
				seen.add(c.id)
				merged.append(c)
			scored = merged
		else:
			scored = [c for c in scored if not is_generic_matched_query(c)]

	# Drop weak specialty/composite packs when stronger foundation options exist.
	strong = [
		c
		for c in scored
		if not is_weak_foundation_candidate(c, parsed_query=parsed_query, page_context=page_context)
	]
	if strong:
		scored = strong

	if PREFER_COMPONENT_FOR_FOUNDATION:
		components = [
			c
			for c in scored
			if c.category == "component" or str(c.item_type or "") in ("registry:ui", "ui")
		]
		others = [c for c in scored if c not in components]
		scored = components + others

	seen_names: set[str] = set()
	deduped: list[ComponentCandidate] = []
	for candidate in scored:
		key = f"{candidate.registry}:{candidate.name}".lower()
		if key in seen_names:
			continue
		seen_names.add(key)
		deduped.append(candidate)
		if len(deduped) >= max_count:
			break
	return deduped
