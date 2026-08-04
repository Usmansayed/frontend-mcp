"""Viewport region focus for live inspiration screenshots.

Maps query scope → CSS selector candidates. Used when capturing live pages so
navbar/hero/section asks get a cropped visual instead of a full marketing page.
"""
from __future__ import annotations

from typing import Any

# Ordered preference — first match with a usable bounding box wins.
SCOPE_SELECTORS: dict[str, tuple[str, ...]] = {
	'chrome': (
		'header',
		'nav',
		'[role="banner"]',
		'[role="navigation"]',
		'[class*="navbar" i]',
		'[class*="nav-bar" i]',
		'[id*="nav" i]',
		'button',
		'[role="button"]',
		'input:not([type="hidden"])',
		'textarea',
		'form',
	),
	'component': (
		'header',
		'nav',
		'[role="banner"]',
		'[role="navigation"]',
		'[class*="navbar" i]',
		'[class*="sidebar" i]',
		'[role="dialog"]',
		'[class*="modal" i]',
		'form',
		'input:not([type="hidden"])',
		'main',
	),
	'section': (
		'[class*="hero" i]',
		'section',
		'[class*="pricing" i]',
		'[class*="footer" i]',
		'[class*="login" i]',
		'[class*="auth" i]',
		'[class*="checkout" i]',
		'form',
		'footer',
		'main',
		'[role="main"]',
	),
	'page': (),
}

_BUTTON_TOKENS = ('button', 'btn', 'cta', 'hover')
_NAV_TOKENS = ('nav', 'navbar', 'menu', 'header')
_MODAL_TOKENS = ('modal', 'dialog')
_SIDEBAR_TOKENS = ('sidebar', 'drawer')
_HERO_TOKENS = ('hero', 'above the fold')
_PRICING_TOKENS = ('pricing', 'price')
_FOOTER_TOKENS = ('footer',)
_INPUT_TOKENS = ('input', 'text field', 'placeholder', 'textarea', 'text area', 'multiline')
_FORM_TOKENS = ('form', 'login', 'signup', 'checkout', 'password', 'email field')
_SEARCH_TOKENS = ('search bar', 'search field', 'search input', 'search box', 'type=search')


def selectors_for_scope(scope: str | None, query: str | None = None) -> tuple[str, ...]:
	"""Return CSS candidates; reorder by query so button asks don't crop the nav."""
	key = (scope or 'page').strip().lower()
	base = list(SCOPE_SELECTORS.get(key, ()))
	# Section/chrome/component may still want form crops even if base empty for page
	q = (query or '').lower()
	boost: list[str] = []
	# Search / input / form before button — "...clear button" must not win
	if any(t in q for t in _SEARCH_TOKENS):
		boost = [
			'input[type="search"]',
			'[role="search"]',
			'[class*="search" i]',
			'input',
			'form',
		]
	elif any(t in q for t in _INPUT_TOKENS):
		boost = [
			'textarea',
			'input:not([type="hidden"])',
			'[role="textbox"]',
			'[class*="input" i]',
			'form',
			'label',
		]
	elif any(t in q for t in _FORM_TOKENS):
		boost = [
			'form',
			'[class*="form" i]',
			'[class*="login" i]',
			'[class*="auth" i]',
			'[class*="checkout" i]',
			'input',
			'section',
		]
	elif any(t in q for t in _BUTTON_TOKENS):
		boost = ['button', '[role="button"]', '[class*="btn" i]', 'a.button']
	elif any(t in q for t in _MODAL_TOKENS):
		boost = ['[role="dialog"]', '[class*="modal" i]']
	elif any(t in q for t in _SIDEBAR_TOKENS):
		boost = ['[class*="sidebar" i]', 'aside', '[role="complementary"]']
	elif any(t in q for t in _NAV_TOKENS):
		boost = ['nav', 'header', '[role="navigation"]', '[role="banner"]']
	elif any(t in q for t in _HERO_TOKENS):
		boost = ['[class*="hero" i]', 'section', 'main']
	elif any(t in q for t in _PRICING_TOKENS):
		boost = ['[class*="pricing" i]', 'section']
	elif any(t in q for t in _FOOTER_TOKENS):
		boost = ['footer', '[class*="footer" i]']
	if not base and not boost:
		return ()
	if not boost:
		return tuple(base)
	seen: set[str] = set()
	out: list[str] = []
	for sel in boost + base:
		if sel in seen:
			continue
		seen.add(sel)
		out.append(sel)
	return tuple(out)


def should_crop_scope(scope: str | None) -> bool:
	return bool(selectors_for_scope(scope))


REGION_CLIP_SCRIPT = """
(selectors) => {
  const list = Array.isArray(selectors) ? selectors : [];
  const pad = 8;
  const vw = window.innerWidth || document.documentElement.clientWidth || 0;
  const vh = window.innerHeight || document.documentElement.clientHeight || 0;
  for (const sel of list) {
    let el = null;
    try { el = document.querySelector(sel); } catch (_) { continue; }
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 24 || r.height < 16) continue;
    const x = Math.max(0, Math.floor(r.x - pad));
    const y = Math.max(0, Math.floor(r.y - pad));
    const width = Math.min(vw - x, Math.ceil(r.width + pad * 2));
    const height = Math.min(vh - y, Math.ceil(r.height + pad * 2));
    if (width < 24 || height < 16) continue;
    const cappedH = Math.min(height, Math.max(180, Math.floor(vh * 0.85)));
    return { x, y, width, height: cappedH, selector: sel };
  }
  return null;
}
"""


def clip_from_script_result(raw: Any) -> dict[str, float] | None:
	"""Normalize JS rect → CDP Page.captureScreenshot clip (scale=1)."""
	if not isinstance(raw, dict):
		return None
	try:
		x = float(raw['x'])
		y = float(raw['y'])
		width = float(raw['width'])
		height = float(raw['height'])
	except (KeyError, TypeError, ValueError):
		return None
	if width < 24 or height < 16:
		return None
	return {
		'x': max(0.0, x),
		'y': max(0.0, y),
		'width': width,
		'height': height,
		'scale': 1,
	}
