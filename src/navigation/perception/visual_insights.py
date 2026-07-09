"""Deterministic layout/visual signals for coding agents (no LLM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .verification import evaluate_js

_COLLECT_JS = r"""(() => {
  const issues = [];
  const boxes = [];
  const doc = document.documentElement;
  const body = document.body;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  if (doc && doc.scrollWidth > vw + 2) {
    issues.push({
      kind: 'horizontal_overflow',
      severity: 'blocking',
      detail: `scrollWidth=${doc.scrollWidth} viewport=${vw}`,
    });
  }
  if (body && body.scrollHeight > vh + 200) {
    issues.push({
      kind: 'tall_page',
      severity: 'advisory',
      detail: `scrollHeight=${body.scrollHeight} viewport=${vh}`,
    });
  }

  const interactiveSel = [
    'button', 'a[href]', 'input', 'select', 'textarea',
    '[role="button"]', '[role="link"]', '[role="tab"]', '[onclick]',
    '[data-testid]', 'label[for]',
  ].join(',');

  const nodes = Array.from(document.querySelectorAll(interactiveSel));
  const seen = new Set();

  for (const el of nodes) {
    if (!(el instanceof HTMLElement)) continue;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 && r.height < 1) {
      const label = (el.getAttribute('aria-label') || el.innerText || el.id || el.tagName).trim().slice(0, 60);
      issues.push({ kind: 'zero_size_clickable', severity: 'blocking', detail: label || el.tagName });
      continue;
    }
    if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;

    const label = (
      el.getAttribute('data-testid') ||
      el.getAttribute('aria-label') ||
      el.getAttribute('name') ||
      el.getAttribute('placeholder') ||
      (el.innerText || '').trim().slice(0, 40) ||
      el.tagName
    ).trim();

    const key = `${Math.round(r.x)}:${Math.round(r.y)}:${label}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const truncated = (el.scrollWidth > el.clientWidth + 2) || (el.scrollHeight > el.clientHeight + 2);
    if (truncated && label) {
      issues.push({ kind: 'truncated_text', severity: 'advisory', detail: label });
    }

    boxes.push({
      x: Math.max(0, Math.round(r.x)),
      y: Math.max(0, Math.round(r.y)),
      width: Math.max(1, Math.round(r.width)),
      height: Math.max(1, Math.round(r.height)),
      label: label.slice(0, 48),
      role: el.getAttribute('role') || el.tagName.toLowerCase(),
      interactive: true,
    });
  }

  // Simple overlap among visible interactive boxes (sample cap for perf)
  const cap = boxes.slice(0, 80);
  for (let i = 0; i < cap.length; i++) {
    for (let j = i + 1; j < cap.length; j++) {
      const a = cap[i], b = cap[j];
      const ox = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
      const oy = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
      const overlap = ox * oy;
      const minArea = Math.min(a.width * a.height, b.width * b.height);
      if (minArea > 0 && overlap / minArea > 0.35) {
        issues.push({
          kind: 'overlapping_interactive',
          severity: 'advisory',
          detail: `${a.label} ∩ ${b.label}`,
        });
      }
    }
  }

  const errorSel = '.error-text, .error, [role="alert"], .validation-error, .alert-danger';
  for (const el of document.querySelectorAll(errorSel)) {
    const t = (el.innerText || el.textContent || '').trim();
    if (!t) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    boxes.push({
      x: Math.round(r.x),
      y: Math.round(r.y),
      width: Math.round(r.width),
      height: Math.round(r.height),
      label: t.slice(0, 48),
      role: 'error',
      interactive: false,
      highlight: 'blocking',
    });
  }

  return { issues: issues.slice(0, 40), element_boxes: boxes.slice(0, 120) };
})()"""


@dataclass(slots=True)
class VisualInsights:
	issues: list[dict[str, Any]] = field(default_factory=list)
	element_boxes: list[dict[str, Any]] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	@property
	def blocking(self) -> list[str]:
		return [f"{i['kind']}: {i['detail']}" for i in self.issues if i.get('severity') == 'blocking']

	@property
	def advisory(self) -> list[str]:
		return [f"{i['kind']}: {i['detail']}" for i in self.issues if i.get('severity') == 'advisory']

	def to_dict(self) -> dict[str, Any]:
		return {
			'issues': self.issues,
			'element_boxes': self.element_boxes,
			'blocking': self.blocking,
			'advisory': self.advisory,
			'degraded': list(self.degraded),
		}


async def collect_visual_insights(session: Any) -> VisualInsights:
	degraded: list[str] = []
	try:
		raw = await evaluate_js(session, _COLLECT_JS)
	except Exception:
		return VisualInsights(degraded=['visual_insights_unavailable'])

	if not isinstance(raw, dict):
		return VisualInsights(degraded=['visual_insights_invalid'])

	issues = raw.get('issues') if isinstance(raw.get('issues'), list) else []
	boxes = raw.get('element_boxes') if isinstance(raw.get('element_boxes'), list) else []
	return VisualInsights(
		issues=[i for i in issues if isinstance(i, dict)],
		element_boxes=[b for b in boxes if isinstance(b, dict)],
		degraded=degraded,
	)
