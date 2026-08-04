"""Objective chrome / layout conventions for perception_verify.

These are deterministic engineering checks — not Ship Council design taste.
See docs/superpowers/specs/2026-07-17-verify-conventions-vs-ship-council-design.md
"""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.section_checklist import (
    get_section_checklist,
)
from navigation.coordination_intelligence.planning.situation_policy import sticky_design_scope

CHROME_ROLES = frozenset({
    "aside",
    "sidebar",
    "nav",
    "navigation",
    "header",
})

NAV_CHROME_ROLES = frozenset({"aside", "sidebar", "nav", "navigation"})

# JS: chrome must remain near the top after a real scroll — catches
# "position:sticky" that is broken by overflow ancestors, and static chrome.
# JS: chrome must stay near the top after a *real* scroll of the scrollport.
# If scroll cannot move, require sticky/fixed with a non-auto top (not mere position:sticky).
# Prefer real sidebar chrome over decoy sticky breadcrumbs/navs.
CHROME_PERMANENCE_ASSERTION = (
    "() => { "
    "const nodes = Array.from(document.querySelectorAll("
    "'aside, nav, [role=\"complementary\"], [role=\"navigation\"], "
    "[class*=\"sidebar\" i], [class*=\"side-nav\" i]')); "
    "if (!nodes.length) return false; "
    "const score = (node) => { "
    "const r = node.getBoundingClientRect(); "
    "const tag = node.tagName.toLowerCase(); "
    "const role = (node.getAttribute('role') || '').toLowerCase(); "
    "const cls = String(node.className || '').toLowerCase(); "
    "let s = Math.max(0, r.height); "
    "if (tag === 'aside' || role === 'complementary') s += 1000; "
    "if (cls.includes('sidebar') || cls.includes('side-nav')) s += 500; "
    "if ((tag === 'nav' || role === 'navigation') && r.height < 72) s -= 800; "
    "return s; "
    "}; "
    "nodes.sort((a, b) => score(b) - score(a)); "
    "const el = nodes[0]; "
    "const stickyOk = (node) => { "
    "const st = getComputedStyle(node); "
    "const pos = st.position; "
    "if (pos === 'fixed') return true; "
    "if (pos === 'sticky' && st.top !== 'auto') { "
    "const topPx = parseFloat(st.top); "
    "if (!Number.isFinite(topPx) || topPx < -8) return false; "
    "return true; "
    "} "
    "return false; "
    "}; "
    "const hasTransformContainment = (node) => { "
    "let p = node.parentElement; "
    "while (p && p !== document.documentElement) { "
    "const st = getComputedStyle(p); "
    "const t = st.transform; "
    "const f = st.filter; "
    "const persp = st.perspective; "
    "if ((t && t !== 'none') || (f && f !== 'none') "
    "|| (persp && persp !== 'none')) return true; "
    "p = p.parentElement; "
    "} "
    "return false; "
    "}; "
    "const overflowBreaksViewportSticky = (node) => { "
    "let p = node.parentElement; "
    "while (p && p !== document.documentElement) { "
    "const st = getComputedStyle(p); "
    "const ox = st.overflowX; "
    "const oy = st.overflowY; "
    "const o = st.overflow; "
    "const bad = (v) => v === 'hidden' || v === 'clip' || v === 'scroll' || v === 'auto'; "
    "if (bad(ox) || bad(oy) || bad(o)) { "
    "const canY = (oy === 'auto' || oy === 'scroll' || oy === 'overlay') "
    "&& p.scrollHeight > p.clientHeight + 40; "
    "if (!canY) return true; "
    "} "
    "p = p.parentElement; "
    "} "
    "return false; "
    "}; "
    "const hasStickyChain = () => { "
    "if (hasTransformContainment(el)) return false; "
    "if (overflowBreaksViewportSticky(el)) return false; "
    "let p = el; "
    "while (p && p.nodeType === 1) { "
    "if (stickyOk(p)) return true; "
    "p = p.parentElement; "
    "} "
    "return false; "
    "}; "
    "let scrollRoot = null; "
    "let n = el.parentElement; "
    "while (n && n !== document.documentElement) { "
    "const st = getComputedStyle(n); "
    "const oy = st.overflowY; "
    "const canY = (oy === 'auto' || oy === 'scroll' || oy === 'overlay') "
    "&& n.scrollHeight > n.clientHeight + 40; "
    "if (canY) { scrollRoot = n; break; } "
    "n = n.parentElement; "
    "} "
    "const readTop = () => el.getBoundingClientRect().top; "
    "if (scrollRoot) { "
    "const y0 = scrollRoot.scrollTop; "
    "const room = scrollRoot.scrollHeight - scrollRoot.clientHeight; "
    "const delta = Math.min(480, Math.max(200, room * 0.4)); "
    "scrollRoot.scrollTop = y0 + delta; "
    "const moved = Math.abs(scrollRoot.scrollTop - y0); "
    "const top1 = readTop(); "
    "scrollRoot.scrollTop = y0; "
    "if (moved < 40) return hasStickyChain(); "
    "return top1 > -8 && top1 < 64; "
    "} "
    "const y0 = window.scrollY || window.pageYOffset || 0; "
    "const room = document.documentElement.scrollHeight - window.innerHeight; "
    "const delta = Math.min(480, Math.max(200, room * 0.35)); "
    "window.scrollTo(0, y0 + delta); "
    "const moved = Math.abs((window.scrollY || 0) - y0); "
    "const top1 = readTop(); "
    "window.scrollTo(0, y0); "
    "if (moved < 40) return hasStickyChain(); "
    "return top1 > -8 && top1 < 64; "
    "}"
)

HORIZONTAL_OVERFLOW_ASSERTION = (
    "() => document.documentElement.scrollWidth <= (window.innerWidth + 2)"
)


def episode_applies_chrome_conventions(
    psm: ProjectSituationModel,
    strategy: dict[str, Any] | None = None,
) -> bool:
    """True when verify must enforce objective chrome/layout conventions."""
    strategy = strategy or {}
    scope = str(strategy.get("task_scope") or sticky_design_scope(psm) or "")
    sticky = sticky_design_scope(psm)
    if sticky in ("design_driven", "redesign", "system_setup"):
        scope = sticky
    if scope in ("hotfix", "surgical", "debug"):
        return False
    if scope not in ("design_driven", "redesign", "system_setup"):
        influence = str(strategy.get("influence_level") or "")
        if influence not in ("structural", "balanced"):
            return False
    # Need a measured surface (snapshot) or a seeded chrome checklist.
    if psm.artifacts.snapshot_id:
        return True
    checklist = get_section_checklist(psm)
    if not checklist:
        return False
    return any(
        str(s.get("role") or "").lower() in CHROME_ROLES
        for s in (checklist.get("sections") or [])
    )


def section_needs_chrome_permanence(section: dict[str, Any]) -> bool:
    role = str(section.get("role") or "").lower()
    return role in NAV_CHROME_ROLES


def build_chrome_permanence_assertion() -> str:
    return CHROME_PERMANENCE_ASSERTION


def build_horizontal_overflow_assertion() -> str:
    return HORIZONTAL_OVERFLOW_ASSERTION


def build_chrome_convention_assertions(
    psm: ProjectSituationModel,
    *,
    section: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
) -> list[str]:
    """JS assertions for objective UX engineering conventions."""
    if not episode_applies_chrome_conventions(psm, strategy):
        return []

    asserts: list[str] = []
    checklist = get_section_checklist(psm)
    has_nav = bool(
        checklist
        and any(
            str(s.get("role") or "").lower() in NAV_CHROME_ROLES
            for s in (checklist.get("sections") or [])
        )
    )

    if section is not None:
        if section_needs_chrome_permanence(section):
            asserts.append(CHROME_PERMANENCE_ASSERTION)
    elif has_nav or psm.artifacts.snapshot_id:
        # Soft page verify: enforce permanence whenever nav chrome is in play.
        if has_nav:
            asserts.append(CHROME_PERMANENCE_ASSERTION)

    asserts.append(HORIZONTAL_OVERFLOW_ASSERTION)
    return list(dict.fromkeys(asserts))
