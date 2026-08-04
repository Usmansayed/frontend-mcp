"""Map Design Sense ReviewRequest → UX KB retrieval params (ux.retrieve v1)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ...models import ReviewRequest

# Surfaces that have dedicated runtime packs today
KNOWN_SURFACES = frozenset({
	'forms',
	'checkout',
	'onboarding',
	'landing',
	'dashboard',
	'settings',
	'marketing',
	'app_shell',
	'admin',
	'analytics',
})


def infer_surface_from_text(text: str) -> str | None:
	t = (text or '').lower()
	if any(k in t for k in ('checkout', 'cart', 'payment')):
		return 'checkout'
	if any(k in t for k in ('onboarding', 'first-run', 'first run', 'welcome wizard')):
		return 'onboarding'
	if any(k in t for k in ('landing', 'marketing', 'homepage', 'hero', 'pricing page')):
		return 'landing'
	if any(k in t for k in ('dashboard', 'analytics', 'kpi', 'metrics', 'admin panel')):
		return 'dashboard'
	if any(k in t for k in ('settings', 'preferences', 'configuration')):
		return 'settings'
	if any(k in t for k in ('sign in', 'sign-in', 'login', 'signup', 'sign up', 'form', 'validation', 'password')):
		return 'forms'
	if any(k in t for k in ('nav', 'navigation', 'sidebar', 'menu', 'app shell')):
		return 'app_shell'
	return None


def infer_surface_from_url(url: str | None) -> str | None:
	if not url:
		return None
	path = urlparse(url).path.lower()
	if any(s in path for s in ('/checkout', '/cart', '/payment')):
		return 'checkout'
	if any(s in path for s in ('/onboard', '/welcome', '/getting-started')):
		return 'onboarding'
	if any(s in path for s in ('/login', '/signin', '/sign-in', '/signup', '/register', '/forms')):
		return 'forms'
	if any(s in path for s in ('/dashboard', '/analytics', '/admin', '/reports')):
		return 'dashboard'
	if any(s in path for s in ('/settings', '/preferences', '/account')):
		return 'settings'
	if path in ('/', '/home', '/landing') or 'landing' in path:
		return 'landing'
	return None


def infer_phase(task: str) -> str:
	t = (task or '').lower()
	if any(k in t for k in ('hotfix', 'bug', 'fix', 'broken')):
		return 'hotfix'
	if any(k in t for k in ('redesign', 'overhaul', 'rebrand')):
		return 'redesign'
	if any(k in t for k in ('polish', 'refine', 'tweak')):
		return 'polish'
	if any(k in t for k in ('greenfield', 'new page', 'from scratch', 'build')):
		return 'greenfield'
	return 'feature'


def infer_problem(task: str, surface: str) -> str | None:
	t = (task or '').lower()
	if any(k in t for k in ('a11y', 'accessib', 'wcag', 'contrast', 'focus', 'keyboard')):
		return 'accessibility'
	if any(k in t for k in ('hierarch', 'density', 'clutter', 'scan')):
		return 'information hierarchy'
	if any(k in t for k in ('readab', 'typography', 'font')):
		return 'typography'
	if any(k in t for k in ('motion', 'animat', 'transition')):
		return 'motion'
	if surface == 'dashboard' and 'hierarch' not in (t or ''):
		return 'information hierarchy'
	if surface == 'landing':
		return 'conversion'
	return None


def infer_psychology_category(task: str) -> str | None:
	t = (task or '').lower()
	if any(k in t for k in ('aesthetic', 'beauty', 'visual polish', 'looks good')):
		return 'aesthetic_usability'
	if any(k in t for k in ('workload', 'fatigue', 'nasa tlx', 'human factors')):
		return 'human_factors'
	if any(
		k in t
		for k in (
			'cognitive load',
			"hick",
			'miller',
			'choice overload',
			'progressive disclosure',
			'decision time',
			'too many options',
			'mental model',
		)
	):
		return 'cognitive_load'
	return None


def build_retrieval_params(request: ReviewRequest) -> dict[str, Any] | None:
	"""Build ux.retrieve params, or None when surface cannot be inferred."""
	task = request.user_task or ''
	psych = infer_psychology_category(task)
	surface = (
		infer_surface_from_text(task)
		or infer_surface_from_url(request.preview_url)
	)

	# Psychology-first: pack_psychology keys only on psychology_category —
	# omit surface_type so surface packs do not outscore it.
	if psych and (
		not surface
		or any(
			k in task.lower()
			for k in (
				'cognitive load',
				'hick',
				'miller',
				'choice overload',
				'psychology',
				'mental model',
			)
		)
	):
		return {
			'intent': task.strip() or 'Apply cognitive psychology constraints',
			'psychology_category': psych,
			'phase': infer_phase(task),
		}

	if not surface:
		if request.scope in ('page', 'flow', 'feature'):
			surface = 'landing'
		else:
			return None

	params: dict[str, Any] = {
		'intent': task.strip() or f'Review {surface} UI',
		'surface_type': surface,
		'phase': infer_phase(task),
	}
	if psych:
		params['psychology_category'] = psych
	problem = infer_problem(task, surface)
	if problem:
		params['problem'] = problem
	if surface == 'forms':
		params['ui_component'] = 'form'
	if surface == 'dashboard':
		params['ui_component'] = 'sidebar'
	if surface in ('landing', 'checkout') and 'conversion' in (problem or ''):
		params['user_flow'] = 'conversion'
	if surface == 'onboarding':
		params['user_flow'] = 'onboarding'
	if surface == 'checkout':
		params['user_flow'] = 'checkout'
	return params
