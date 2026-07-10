"""Rule evaluators — ported Design Lint checks for DOM/CSS."""
from __future__ import annotations

from ..models import ReviewFinding
from .context import LintContext, StyleSnapshot
from .meta import RULE_BY_ID


def evaluate_all(ctx: LintContext) -> list[ReviewFinding]:
	findings: list[ReviewFinding] = []
	for el in ctx.elements:
		findings.extend(_lint_element(el, ctx))
	return findings


def _lint_element(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	"""Design Lint determineType pattern — run applicable rules per element kind."""
	findings: list[ReviewFinding] = []
	is_text = el.tag in ('p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'a', 'button')

	if is_text:
		findings.extend(check_type(el, ctx))
		findings.extend(check_fills(el, ctx))
	if el.tag in ('div', 'section', 'article', 'button', 'input', 'a'):
		findings.extend(check_fills(el, ctx))
		findings.extend(check_radius(el, ctx))
		findings.extend(check_effects(el, ctx))
		findings.extend(check_strokes(el, ctx))
		findings.extend(check_spacing(el, ctx))
	return findings


def check_type(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['missing-text-style']
	if not el.font_size:
		return []
	if el.uses_css_var or _uses_tailwind_type(el.classes):
		return []
	px = _parse_px(el.font_size)
	if px is not None and px not in ctx.allowed_font_sizes:
		return [_finding(meta, el, f'font-size {el.font_size} off typography scale')]
	return [
		_finding(meta, el, f'text node {el.selector} may lack typography token')
	] if not el.uses_css_var and not _uses_tailwind_type(el.classes) else []


def check_fills(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['missing-color-token']
	out: list[ReviewFinding] = []
	for prop, val in (('color', el.color), ('background', el.background_color)):
		if not val or 'var(--' in val:
			continue
		if val.startswith('rgb') or val.startswith('#'):
			out.append(_finding(meta, el, f'{prop} uses raw value {val}'))
	return out


def check_spacing(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['off-scale-spacing']
	out: list[ReviewFinding] = []
	for prop, val in (('margin', el.margin), ('padding', el.padding)):
		if not val:
			continue
		for part in val.replace('px', ' px').split():
			px = _parse_px(part)
			if px is not None and px not in ctx.spacing_scale:
				out.append(_finding(meta, el, f'{prop} {val} off spacing scale'))
				break
	return out


def check_radius(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['off-scale-radius']
	if not el.border_radius:
		return []
	px = _parse_px(el.border_radius)
	if px is not None and px not in ctx.radius_scale:
		return [_finding(meta, el, f'border-radius {el.border_radius} off token scale')]
	return []


def check_effects(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['off-scale-shadow']
	if el.box_shadow and el.box_shadow != 'none' and 'var(--' not in el.box_shadow:
		return [_finding(meta, el, 'box-shadow not from design token')]
	return []


def check_strokes(el: StyleSnapshot, ctx: LintContext) -> list[ReviewFinding]:
	meta = RULE_BY_ID['stroke-without-token']
	if el.border and el.border != 'none' and 'var(--' not in el.border:
		return [_finding(meta, el, 'border not from design token')]
	return []


def _uses_tailwind_type(classes: list[str]) -> bool:
	prefixes = ('text-', 'font-', 'leading-', 'tracking-')
	return any(c.startswith(prefixes) for c in classes)


def _parse_px(value: str) -> int | None:
	v = value.strip().lower().replace('px', '').split()[0] if value else ''
	try:
		return int(float(v))
	except ValueError:
		return None


def _finding(meta, el: StyleSnapshot, detail: str) -> ReviewFinding:
	return ReviewFinding(
		id=f'{meta.id}:{el.selector}',
		category=meta.category,
		severity=meta.default_severity,
		message=meta.title,
		rationale=meta.rationale,
		recommendation=f'{detail} — {meta.when_triggered}',
		source='design_lint',
		selector=el.selector,
		metadata={'detail': detail, 'rule_id': meta.id},
	)
