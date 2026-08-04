"""Raw browser context — collected once, consumed by all extractors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url

_COLLECT_ELEMENTS_JS = r"""(() => {
  const MAX = 500;
  const selectors = [
    'h1','h2','h3','h4','h5','h6','p','span','a','button','input','select','textarea','label',
    'nav','aside','header','footer','main','section','article','form',
    '[role="button"]','[role="link"]','[role="navigation"]','[role="complementary"]',
    '.card','.primary','.field','.grid','.row','[class*="sidebar"]','[class*="side-nav"]',
  ];
  const seen = new Set();
  const elements = [];
  const cssVars = {};
  const root = document.documentElement;
  const rootStyle = getComputedStyle(root);
  for (let i = 0; i < rootStyle.length; i++) {
    const prop = rootStyle[i];
    if (prop.startsWith('--')) {
      cssVars[prop] = rootStyle.getPropertyValue(prop).trim();
    }
  }
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const doc = document.documentElement;
  const body = document.body;

  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      if (!(el instanceof HTMLElement)) continue;
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 && r.height < 1) continue;
      const key = el.tagName + ':' + (el.className || '') + ':' + Math.round(r.top) + ':' + Math.round(r.left);
      if (seen.has(key)) continue;
      seen.add(key);
      const classes = typeof el.className === 'string' ? el.className.split(/\s+/).filter(Boolean) : [];
      elements.push({
        selector: sel,
        tag: el.tagName.toLowerCase(),
        id: el.id || null,
        classes,
        role: el.getAttribute('role'),
        ariaLabel: el.getAttribute('aria-label'),
        text: (el.innerText || el.value || el.getAttribute('placeholder') || '').trim().slice(0, 80),
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        style: {
          color: style.color,
          backgroundColor: style.backgroundColor,
          fontSize: style.fontSize,
          fontFamily: style.fontFamily,
          fontWeight: style.fontWeight,
          lineHeight: style.lineHeight,
          padding: style.padding,
          margin: style.margin,
          gap: style.gap,
          borderRadius: style.borderRadius,
          border: style.border,
          boxShadow: style.boxShadow,
          transition: style.transition,
          animation: style.animation,
          animationDuration: style.animationDuration,
          display: style.display,
          position: style.position,
          top: style.top,
          left: style.left,
          zIndex: style.zIndex,
          gridTemplateColumns: style.gridTemplateColumns,
          columnGap: style.columnGap,
          rowGap: style.rowGap,
        },
      });
      if (elements.length >= MAX) break;
    }
    if (elements.length >= MAX) break;
  }

  return {
    url: location.href,
    viewport: { width: vw, height: vh },
    document: {
      scrollWidth: doc ? doc.scrollWidth : 0,
      scrollHeight: doc ? doc.scrollHeight : 0,
      clientWidth: doc ? doc.clientWidth : 0,
      clientHeight: doc ? doc.clientHeight : 0,
    },
    css_variables: cssVars,
    elements,
    prefers_reduced_motion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  };
})()"""


@dataclass(slots=True)
class RawBrowserContext:
	"""Single collection pass from browser intelligence."""

	url: str = ''
	viewport: dict[str, int] = field(default_factory=dict)
	document: dict[str, int] = field(default_factory=dict)
	elements: list[dict[str, Any]] = field(default_factory=list)
	css_variables: dict[str, str] = field(default_factory=dict)
	prefers_reduced_motion: bool = False
	visual_insights: dict[str, Any] | None = None
	a11y_tree: str = ''
	dom_text: str = ''
	screenshot_ref: str | None = None
	scan_id: str | None = None
	degraded: list[str] = field(default_factory=list)

	@classmethod
	async def from_session(
		cls,
		session: Any,
		*,
		visual_insights: dict[str, Any] | None = None,
		a11y_tree: str = '',
		dom_text: str = '',
		screenshot_ref: str | None = None,
		scan_id: str | None = None,
	) -> RawBrowserContext:
		degraded: list[str] = []
		url = ''
		try:
			url = await read_current_url(session)
		except Exception:
			degraded.append('url_unavailable')

		raw: dict[str, Any] = {}
		try:
			result = await evaluate_js(session, _COLLECT_ELEMENTS_JS)
			raw = result if isinstance(result, dict) else {}
		except Exception:
			degraded.append('element_collection_failed')

		if not raw:
			degraded.append('empty_element_collection')

		return cls(
			url=str(raw.get('url') or url),
			viewport=dict(raw.get('viewport') or {}),
			document=dict(raw.get('document') or {}),
			elements=[e for e in (raw.get('elements') or []) if isinstance(e, dict)],
			css_variables={k: str(v) for k, v in (raw.get('css_variables') or {}).items()},
			prefers_reduced_motion=bool(raw.get('prefers_reduced_motion')),
			visual_insights=visual_insights,
			a11y_tree=a11y_tree,
			dom_text=dom_text,
			screenshot_ref=screenshot_ref,
			scan_id=scan_id,
			degraded=degraded,
		)

	@classmethod
	def from_fixture(cls, data: dict[str, Any]) -> RawBrowserContext:
		"""Build context from test fixtures without a browser."""
		return cls(
			url=str(data.get('url') or ''),
			viewport=dict(data.get('viewport') or {'width': 1280, 'height': 720}),
			document=dict(data.get('document') or {}),
			elements=list(data.get('elements') or []),
			css_variables=dict(data.get('css_variables') or {}),
			prefers_reduced_motion=bool(data.get('prefers_reduced_motion')),
			visual_insights=data.get('visual_insights'),
			degraded=list(data.get('degraded') or []),
		)
