"""Engineering Knowledge Compiler — measurements → engineering decisions (deterministic)."""
from __future__ import annotations

import re
from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.engineering_knowledge.catalog import V1_DECISION_DEFS, DecisionDef
from navigation.engineering_knowledge.models import EngineeringDecision, FrontendEngineeringSpec


class EngineeringKnowledgeCompiler:
    """Universal compiler into FrontendEngineeringSpec.

    V1: DesignSnapshot is the primary measurement input.
    Future adapters (Inspiration/Figma/project) must funnel measurements
    through DesignSnapshot or supply equivalent structured facts — never
    invent private engineering languages.
    """

    def compile_from_snapshot(
        self,
        snapshot: DesignSnapshot,
        *,
        source_kind: str = "live_dom",
        provenance: dict[str, Any] | None = None,
        foundation_hint: dict[str, Any] | None = None,
    ) -> FrontendEngineeringSpec:
        base = self.empty_spec(
            source_kind=source_kind,
            provenance={
                "url": snapshot.url,
                "scan_id": snapshot.scan_id,
                **(provenance or {}),
            },
        )
        ctx = _CompileContext(snapshot=snapshot, foundation_hint=foundation_hint or {})
        for ddef in V1_DECISION_DEFS:
            compiled = _compile_decision(ddef, ctx)
            base.decisions[ddef.decision_id] = compiled
        if snapshot.degraded:
            base.degraded.extend(f"snapshot:{d}" for d in snapshot.degraded)
        return base

    def empty_spec(
        self,
        *,
        source_kind: str = "unmeasured",
        provenance: dict[str, Any] | None = None,
    ) -> FrontendEngineeringSpec:
        """All V1 decisions unresolved — used before measurement / greenfield."""
        decisions: dict[str, EngineeringDecision] = {}
        for ddef in V1_DECISION_DEFS:
            decisions[ddef.decision_id] = EngineeringDecision(
                decision_id=ddef.decision_id,
                group=ddef.group,
                status="unresolved",
                value=None,
                unit=ddef.unit,
                confidence=0.0,
                importance=ddef.importance,
                impact_weight=ddef.impact_weight,
                evidence=[],
                why=ddef.why_unresolved,
                why_code="unmeasured",
                provenance=dict(provenance or {}),
            )
        return FrontendEngineeringSpec(
            source_kind=source_kind,
            provenance=dict(provenance or {}),
            decisions=decisions,
        )


class _CompileContext:
    __slots__ = ("snapshot", "foundation_hint")

    def __init__(
        self,
        *,
        snapshot: DesignSnapshot,
        foundation_hint: dict[str, Any],
    ) -> None:
        self.snapshot = snapshot
        self.foundation_hint = foundation_hint


def _compile_decision(ddef: DecisionDef, ctx: _CompileContext) -> EngineeringDecision:
    handlers = {
        "layout.archetype": _layout_archetype,
        "layout.sidebar_width_px": _layout_sidebar_width,
        "layout.content_max_width_px": _layout_content_max_width,
        "layout.header_height_px": _layout_header_height,
        "layout.grid_columns": _layout_grid_columns,
        "hierarchy.primary_focus": _hierarchy_primary,
        "hierarchy.secondary_focus": _hierarchy_secondary,
        "hierarchy.reading_order": _hierarchy_reading_order,
        "hierarchy.heading_levels_present": _hierarchy_levels,
        "nav.pattern": _nav_pattern,
        "nav.density": _nav_density,
        "nav.primary_landmarks": _nav_landmarks,
        "spacing.base_unit_px": _spacing_base,
        "spacing.scale_px": _spacing_scale,
        "spacing.section_gap_px": _spacing_section_gap,
        "spacing.card_gap_px": _spacing_card_gap,
        "type.font_families": _type_fonts,
        "type.heading_scale_px": _type_heading_scale,
        "type.body_size_px": _type_body,
        "type.line_height_ratio": _type_line_height,
        "color.background": _color_bg,
        "color.text": _color_text,
        "color.accent": _color_accent,
        "color.surface": _color_surface,
        "color.palette_size": _color_palette_size,
        "component.foundation_status": lambda c, d: _component_foundation(c, d, ctx.foundation_hint),
        "component.pattern_families": _component_patterns,
        "component.interactive_density": _component_interactive_density,
        "density.band": _density_band,
        "density.score": _density_score,
    }
    fn = handlers.get(ddef.decision_id)
    if fn is None:
        return _unresolved(ddef, why_code="no_compiler_rule")
    return fn(ctx, ddef)


def _base(ddef: DecisionDef, **kwargs: Any) -> EngineeringDecision:
    return EngineeringDecision(
        decision_id=ddef.decision_id,
        group=ddef.group,
        unit=ddef.unit,
        importance=ddef.importance,
        impact_weight=ddef.impact_weight,
        **kwargs,
    )


def _unresolved(ddef: DecisionDef, *, why_code: str = "insufficient_evidence") -> EngineeringDecision:
    return _base(
        ddef,
        status="unresolved",
        value=None,
        confidence=0.0,
        evidence=[],
        why=ddef.why_unresolved,
        why_code=why_code,
    )


def _resolved(
    ddef: DecisionDef,
    *,
    value: Any,
    confidence: float,
    evidence: list[str],
    why: str,
    why_code: str,
    status: str = "resolved",
    raw_refs: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
) -> EngineeringDecision:
    return _base(
        ddef,
        status=status,
        value=value,
        confidence=max(0.0, min(1.0, confidence)),
        evidence=evidence,
        why=why,
        why_code=why_code,
        raw_refs=list(raw_refs or []),
        constraints=dict(constraints or {}),
    )


# --- Layout ---


def _region(snap: DesignSnapshot, role: str) -> dict[str, Any] | None:
    for r in snap.layout.regions:
        if r.get("role") == role:
            return r
    return None


def _rect_width(region: dict[str, Any] | None) -> float | None:
    if not region:
        return None
    rect = region.get("rect") or {}
    w = rect.get("width")
    try:
        return float(w) if w is not None else None
    except (TypeError, ValueError):
        return None


def _rect_height(region: dict[str, Any] | None) -> float | None:
    if not region:
        return None
    rect = region.get("rect") or {}
    h = rect.get("height")
    try:
        return float(h) if h is not None else None
    except (TypeError, ValueError):
        return None


def _layout_archetype(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    snap = ctx.snapshot
    nav = _region(snap, "nav")
    header = _region(snap, "header")
    main = _region(snap, "main")
    nav_w = _rect_width(nav)
    header_h = _rect_height(header)
    roles = {r.get("role") for r in snap.layout.regions}

    evidence = ["snapshot.layout.regions"]
    if nav_w and nav_w >= 180 and "main" in roles:
        return _resolved(
            ddef,
            value="left_sidebar_dashboard",
            confidence=0.88 if nav_w >= 220 else 0.75,
            evidence=evidence,
            why=f"Detected nav region width≈{nav_w:.0f}px with main content — sidebar dashboard archetype.",
            why_code="rule.nav_wide_with_main",
            constraints={"nav_width_px": round(nav_w)},
            raw_refs=["layout.regions"],
        )
    if header_h and header_h >= 48 and "nav" not in roles:
        return _resolved(
            ddef,
            value="top_nav_marketing",
            confidence=0.72,
            evidence=evidence,
            why=f"Header height≈{header_h:.0f}px without aside nav — marketing/top-nav archetype.",
            why_code="rule.header_without_nav",
            raw_refs=["layout.regions"],
        )
    if "form" in roles and main is None and len(roles) <= 2:
        return _resolved(
            ddef,
            value="centered_auth_form",
            confidence=0.7,
            evidence=evidence,
            why="Form-dominant landmark set without main — auth/form archetype.",
            why_code="rule.form_dominant",
        )
    if roles:
        return _resolved(
            ddef,
            value="generic_document",
            confidence=0.45,
            evidence=evidence,
            why=f"Landmarks present ({sorted(roles)}) but no strong archetype match.",
            why_code="rule.generic_landmarks",
            status="partial",
        )
    return _unresolved(ddef, why_code="no_landmarks")


def _layout_sidebar_width(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    w = _rect_width(_region(ctx.snapshot, "nav"))
    if w is None or w < 120:
        return _unresolved(ddef, why_code="no_nav_width")
    return _resolved(
        ddef,
        value=int(round(w)),
        confidence=0.92 if 180 <= w <= 360 else 0.7,
        evidence=["dom_geometry", "snapshot.layout.regions"],
        why=f"Measured nav region width {w:.0f}px.",
        why_code="measure.nav_rect_width",
        constraints={"min": 180, "max": 360},
        raw_refs=["layout.regions[nav].rect.width"],
    )


def _layout_content_max_width(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    main_w = _rect_width(_region(ctx.snapshot, "main"))
    vp_w = float((ctx.snapshot.layout.viewport or {}).get("width") or 0)
    if main_w and main_w > 0:
        return _resolved(
            ddef,
            value=int(round(main_w)),
            confidence=0.8,
            evidence=["dom_geometry"],
            why=f"Measured main content width {main_w:.0f}px.",
            why_code="measure.main_rect_width",
            raw_refs=["layout.regions[main].rect.width"],
        )
    if vp_w >= 1024:
        # Infer comfortable content max for wide viewports without main rect
        return _resolved(
            ddef,
            value=1440 if vp_w >= 1440 else int(vp_w),
            confidence=0.4,
            evidence=["viewport"],
            why="No main region; inferred from viewport width (partial).",
            why_code="infer.viewport_as_content_max",
            status="partial",
        )
    return _unresolved(ddef)


def _layout_header_height(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    h = _rect_height(_region(ctx.snapshot, "header"))
    if h is None or h < 32:
        return _unresolved(ddef, why_code="no_header_height")
    return _resolved(
        ddef,
        value=int(round(h)),
        confidence=0.9,
        evidence=["dom_geometry"],
        why=f"Measured header height {h:.0f}px.",
        why_code="measure.header_rect_height",
        raw_refs=["layout.regions[header].rect.height"],
    )


def _layout_grid_columns(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    counts = list(ctx.snapshot.grid.column_counts or [])
    if not counts:
        return _unresolved(ddef, why_code="no_grid")
    # Prefer 12 if present else mode
    value = 12 if 12 in counts else max(set(counts), key=counts.count)
    return _resolved(
        ddef,
        value=int(value),
        confidence=0.65 if ctx.snapshot.grid.alignment_score >= 0.5 else 0.45,
        evidence=["snapshot.grid"],
        why=f"Detected column counts {counts}; selected {value}.",
        why_code="measure.grid_column_counts",
        status="partial" if ctx.snapshot.grid.alignment_score < 0.5 else "resolved",
        raw_refs=["grid.column_counts"],
    )


# --- Hierarchy ---


def _hierarchy_primary(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    tree = ctx.snapshot.hierarchy.heading_tree or []
    prom = ctx.snapshot.hierarchy.prominence_scores or []
    if prom:
        top = max(prom, key=lambda p: float(p.get("score") or 0))
        text = str(top.get("text") or top.get("selector") or "").strip()
        if text:
            return _resolved(
                ddef,
                value=text[:120],
                confidence=min(0.95, 0.5 + float(top.get("score") or 0) / 2),
                evidence=["snapshot.hierarchy.prominence_scores"],
                why="Highest prominence score element treated as primary focus.",
                why_code="measure.prominence_max",
                raw_refs=["hierarchy.prominence_scores"],
            )
    h1 = next((h for h in tree if str(h.get("level") or h.get("tag") or "").lower() in ("1", "h1")), None)
    if not h1 and tree:
        h1 = tree[0]
    if h1:
        text = str(h1.get("text") or "").strip()
        if text:
            return _resolved(
                ddef,
                value=text[:120],
                confidence=0.75,
                evidence=["snapshot.hierarchy.heading_tree"],
                why="Primary H1/first heading text.",
                why_code="measure.first_heading",
            )
    return _unresolved(ddef)


def _hierarchy_secondary(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    tree = ctx.snapshot.hierarchy.heading_tree or []
    candidates = [
        h
        for h in tree
        if str(h.get("level") or h.get("tag") or "").lower() in ("2", "h2")
    ]
    if not candidates and len(tree) > 1:
        candidates = tree[1:2]
    if not candidates:
        return _unresolved(ddef, why_code="no_secondary_heading")
    text = str(candidates[0].get("text") or "").strip()
    if not text:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=text[:120],
        confidence=0.7,
        evidence=["snapshot.hierarchy.heading_tree"],
        why="First H2 (or second heading) as secondary focus.",
        why_code="measure.secondary_heading",
    )


def _hierarchy_reading_order(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    tree = ctx.snapshot.hierarchy.heading_tree or []
    order = [str(h.get("text") or "").strip() for h in tree if str(h.get("text") or "").strip()]
    if len(order) < 2:
        return _unresolved(ddef, why_code="insufficient_headings")
    return _resolved(
        ddef,
        value=order[:12],
        confidence=0.8,
        evidence=["snapshot.hierarchy.heading_tree"],
        why="Heading document order as reading-order proxy.",
        why_code="measure.heading_order",
        raw_refs=["hierarchy.heading_tree"],
    )


def _hierarchy_levels(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    levels = ctx.snapshot.typography.heading_levels or []
    if not levels:
        tree = ctx.snapshot.hierarchy.heading_tree or []
        tags = sorted({str(h.get("tag") or h.get("level") or "") for h in tree if h})
        if not tags:
            return _unresolved(ddef)
        return _resolved(
            ddef,
            value=tags,
            confidence=0.6,
            evidence=["snapshot.hierarchy.heading_tree"],
            why="Heading tags from hierarchy tree.",
            why_code="measure.heading_tags",
            status="partial",
        )
    return _resolved(
        ddef,
        value=levels,
        confidence=0.85,
        evidence=["snapshot.typography.heading_levels"],
        why="Typography heading level samples.",
        why_code="measure.heading_levels",
    )


# --- Navigation ---


def _nav_pattern(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    snap = ctx.snapshot
    nav_w = _rect_width(_region(snap, "nav"))
    header_h = _rect_height(_region(snap, "header"))
    roles = {r.get("role") for r in snap.layout.regions}
    if nav_w and nav_w >= 180:
        return _resolved(
            ddef,
            value="left_sidebar",
            confidence=0.9,
            evidence=["dom_geometry"],
            why=f"Wide nav landmark ({nav_w:.0f}px) → left sidebar navigation.",
            why_code="rule.nav_wide",
        )
    if header_h and header_h >= 40 and ("nav" in roles or "header" in roles):
        return _resolved(
            ddef,
            value="top_bar",
            confidence=0.8,
            evidence=["dom_geometry"],
            why="Header/nav height suggests top-bar navigation.",
            why_code="rule.header_nav",
        )
    if "nav" in roles and "header" in roles:
        return _resolved(
            ddef,
            value="hybrid",
            confidence=0.55,
            evidence=["snapshot.layout.regions"],
            why="Both header and nav landmarks present — hybrid (partial).",
            why_code="rule.header_and_nav",
            status="partial",
        )
    return _unresolved(ddef)


def _nav_density(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    boxes = ctx.snapshot.layout.interactive_boxes or []
    nav = _region(ctx.snapshot, "nav")
    if not nav:
        return _unresolved(ddef, why_code="no_nav")
    # Count interactive near low-x if rects exist; else use total interactive as proxy
    count = len(boxes)
    if count >= 18:
        band = "dense"
        conf = 0.7
    elif count >= 8:
        band = "comfortable"
        conf = 0.65
    elif count > 0:
        band = "sparse"
        conf = 0.55
    else:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=band,
        confidence=conf,
        evidence=["snapshot.layout.interactive_boxes"],
        why=f"Interactive control count≈{count} → nav/surface density '{band}'.",
        why_code="measure.interactive_count_band",
    )


def _nav_landmarks(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    roles = [str(r.get("role")) for r in ctx.snapshot.layout.regions if r.get("role")]
    if not roles:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=roles,
        confidence=0.85,
        evidence=["snapshot.layout.regions"],
        why=f"Landmark roles: {roles}.",
        why_code="measure.landmarks",
    )


# --- Spacing ---


def _spacing_base(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    base = ctx.snapshot.spacing.base_unit_px
    if base is None:
        scale = ctx.snapshot.design_tokens.spacing_scale or []
        if scale:
            base = min(scale)
        else:
            return _unresolved(ddef)
    return _resolved(
        ddef,
        value=int(base),
        confidence=0.9 if ctx.snapshot.spacing.base_unit_px else 0.65,
        evidence=["snapshot.spacing", "snapshot.design_tokens"],
        why=f"Base spacing unit {base}px.",
        why_code="measure.spacing_base_unit",
        constraints={"common": [4, 8]},
        raw_refs=["spacing.base_unit_px"],
    )


def _spacing_scale(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    scale = list(ctx.snapshot.design_tokens.spacing_scale or [])
    if not scale:
        vals = sorted(
            set(
                int(v)
                for v in (
                    list(ctx.snapshot.spacing.padding_values_px or [])
                    + list(ctx.snapshot.spacing.gap_values_px or [])
                )
                if isinstance(v, (int, float)) and v > 0
            )
        )[:12]
        if len(vals) < 2:
            return _unresolved(ddef)
        return _resolved(
            ddef,
            value=vals,
            confidence=0.55,
            evidence=["snapshot.spacing"],
            why="Inferred spacing scale from padding/gap samples.",
            why_code="infer.spacing_from_samples",
            status="partial",
        )
    return _resolved(
        ddef,
        value=scale,
        confidence=0.88,
        evidence=["snapshot.design_tokens.spacing_scale"],
        why=f"Token/inferred spacing scale {scale}.",
        why_code="measure.token_spacing_scale",
    )


def _pick_gap_from_values(values: list[float], *, prefer_high: bool) -> int | None:
    clean = sorted({int(round(v)) for v in values if isinstance(v, (int, float)) and v >= 8})
    if not clean:
        return None
    if prefer_high:
        return clean[-1] if clean else None
    # median-ish
    return clean[len(clean) // 2]


def _spacing_section_gap(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    gaps = list(ctx.snapshot.spacing.margin_values_px or []) + list(
        ctx.snapshot.spacing.gap_values_px or []
    )
    chosen = _pick_gap_from_values([float(g) for g in gaps], prefer_high=True)
    if chosen is None or chosen < 24:
        return _unresolved(ddef, why_code="no_large_gap")
    return _resolved(
        ddef,
        value=chosen,
        confidence=0.6,
        evidence=["snapshot.spacing"],
        why=f"Largest common gap/margin {chosen}px treated as section gap (partial).",
        why_code="infer.large_gap_as_section",
        status="partial",
    )


def _spacing_card_gap(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    gaps = [float(g) for g in (ctx.snapshot.spacing.gap_values_px or [])]
    mid = _pick_gap_from_values(gaps, prefer_high=False)
    if mid is None:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=mid,
        confidence=0.58,
        evidence=["snapshot.spacing.gap_values_px"],
        why=f"Mid gap sample {mid}px as card gap (partial).",
        why_code="infer.mid_gap_as_card",
        status="partial",
    )


# --- Typography ---


def _type_fonts(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    families = [f for f in (ctx.snapshot.typography.font_families or []) if f]
    if not families:
        return _unresolved(ddef)
    # Normalize first family token
    cleaned = []
    for fam in families[:4]:
        primary = re.split(r",", fam)[0].strip().strip("'\"")
        if primary and primary.lower() not in ("sans-serif", "serif", "monospace", "system-ui"):
            cleaned.append(primary)
        elif primary:
            cleaned.append(primary)
    if not cleaned:
        cleaned = families[:2]
    return _resolved(
        ddef,
        value=cleaned,
        confidence=0.9,
        evidence=["snapshot.typography.font_families"],
        why=f"Observed font families: {cleaned}.",
        why_code="measure.font_families",
    )


def _type_heading_scale(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    levels = ctx.snapshot.typography.heading_levels or []
    sizes: list[float] = []
    for lvl in levels:
        if isinstance(lvl, dict):
            fs = lvl.get("fontSize") or lvl.get("font_size") or lvl.get("size")
            try:
                if fs is not None:
                    sizes.append(float(fs))
            except (TypeError, ValueError):
                pass
    if not sizes:
        # Fall back to larger font sizes
        all_sizes = sorted(
            {float(s) for s in (ctx.snapshot.typography.font_sizes_px or []) if isinstance(s, (int, float))},
            reverse=True,
        )
        sizes = all_sizes[:5]
    if len(sizes) < 1:
        return _unresolved(ddef)
    sizes = sorted({int(round(s)) for s in sizes}, reverse=True)
    return _resolved(
        ddef,
        value=sizes,
        confidence=0.82 if levels else 0.55,
        evidence=["snapshot.typography"],
        why=f"Heading scale (px desc): {sizes}.",
        why_code="measure.heading_sizes",
        status="resolved" if levels else "partial",
    )


def _type_body(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    samples = ctx.snapshot.typography.body_samples or []
    for s in samples:
        if isinstance(s, dict):
            try:
                fs = float(s.get("fontSize") or s.get("font_size") or 0)
            except (TypeError, ValueError):
                fs = 0
            if 12 <= fs <= 20:
                return _resolved(
                    ddef,
                    value=int(round(fs)),
                    confidence=0.85,
                    evidence=["snapshot.typography.body_samples"],
                    why=f"Body sample font-size {fs}px.",
                    why_code="measure.body_sample",
                )
    sizes = [
        float(s)
        for s in (ctx.snapshot.typography.font_sizes_px or [])
        if isinstance(s, (int, float)) and 12 <= float(s) <= 18
    ]
    if not sizes:
        return _unresolved(ddef)
    body = sorted(sizes)[len(sizes) // 2]
    return _resolved(
        ddef,
        value=int(round(body)),
        confidence=0.65,
        evidence=["snapshot.typography.font_sizes_px"],
        why=f"Median mid-range size {body}px as body.",
        why_code="infer.body_from_size_band",
        status="partial",
    )


def _type_line_height(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    lhs = [float(x) for x in (ctx.snapshot.typography.line_heights or []) if isinstance(x, (int, float))]
    if not lhs:
        return _unresolved(ddef)
    # If absolute px-ish (>5), convert using body size guess
    median = sorted(lhs)[len(lhs) // 2]
    if median > 5:
        body = 16.0
        sizes = ctx.snapshot.typography.font_sizes_px or []
        mid = [float(s) for s in sizes if isinstance(s, (int, float)) and 12 <= float(s) <= 18]
        if mid:
            body = sorted(mid)[len(mid) // 2]
        ratio = round(median / max(body, 1.0), 2)
    else:
        ratio = round(median, 2)
    return _resolved(
        ddef,
        value=ratio,
        confidence=0.7,
        evidence=["snapshot.typography.line_heights"],
        why=f"Line-height ratio ≈ {ratio}.",
        why_code="measure.line_height",
    )


# --- Color ---


def _first_color(values: list[str]) -> str | None:
    for v in values:
        if v and v not in ("transparent", "rgba(0, 0, 0, 0)"):
            return v
    return None


def _color_bg(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    c = _first_color(list(ctx.snapshot.colors.background_colors or []))
    if not c:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=c,
        confidence=0.8,
        evidence=["snapshot.colors.background_colors"],
        why=f"Dominant background {c}.",
        why_code="measure.bg_color",
    )


def _color_text(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    c = _first_color(list(ctx.snapshot.colors.text_colors or []))
    if not c:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=c,
        confidence=0.8,
        evidence=["snapshot.colors.text_colors"],
        why=f"Dominant text color {c}.",
        why_code="measure.text_color",
    )


def _color_accent(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    accents = list(ctx.snapshot.colors.accent_colors or [])
    tokens = ctx.snapshot.design_tokens.color_tokens or {}
    for key in ("--primary", "--accent", "--brand", "primary", "accent"):
        if key in tokens and tokens[key]:
            return _resolved(
                ddef,
                value=tokens[key],
                confidence=0.9,
                evidence=["snapshot.design_tokens.color_tokens"],
                why=f"Accent from token {key}={tokens[key]}.",
                why_code="measure.token_accent",
                raw_refs=[f"design_tokens.color_tokens.{key}"],
            )
    c = _first_color(accents)
    if not c:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=c,
        confidence=0.7,
        evidence=["snapshot.colors.accent_colors"],
        why=f"Accent from palette sample {c}.",
        why_code="measure.accent_sample",
    )


def _color_surface(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    bgs = list(ctx.snapshot.colors.background_colors or [])
    if len(bgs) < 2:
        return _unresolved(ddef, why_code="single_surface")
    # second distinct bg as surface
    primary = bgs[0]
    for c in bgs[1:]:
        if c != primary and c not in ("transparent", "rgba(0, 0, 0, 0)"):
            return _resolved(
                ddef,
                value=c,
                confidence=0.55,
                evidence=["snapshot.colors.background_colors"],
                why=f"Secondary background {c} as surface.",
                why_code="infer.secondary_bg_surface",
                status="partial",
            )
    return _unresolved(ddef)


def _color_palette_size(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    n = len(ctx.snapshot.colors.palette or [])
    if n <= 0:
        n = ctx.snapshot.colors.raw_color_count
    if n <= 0:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=int(n),
        confidence=0.75,
        evidence=["snapshot.colors"],
        why=f"Palette size {n}.",
        why_code="measure.palette_size",
    )


# --- Component / density ---


def _component_foundation(
    ctx: _CompileContext,
    ddef: DecisionDef,
    hint: dict[str, Any],
) -> EngineeringDecision:
    if hint.get("library") or hint.get("foundation"):
        return _resolved(
            ddef,
            value={
                "status": "selected",
                "library": hint.get("library") or hint.get("foundation"),
            },
            confidence=float(hint.get("confidence") or 0.85),
            evidence=["component_foundation_hint"],
            why="Foundation provided by component selection context.",
            why_code="hint.foundation_selected",
        )
    pats = ctx.snapshot.components.patterns or []
    if pats:
        return _resolved(
            ddef,
            value={"status": "inferred_patterns", "patterns": [p.get("name") or p for p in pats[:8]]},
            confidence=0.45,
            evidence=["snapshot.components.patterns"],
            why="Patterns observed but explicit foundation library not selected.",
            why_code="infer.patterns_without_foundation",
            status="partial",
        )
    return _unresolved(ddef, why_code="foundation_unknown")


def _component_patterns(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    pats = ctx.snapshot.components.patterns or []
    names: list[str] = []
    for p in pats:
        if isinstance(p, dict):
            n = str(p.get("name") or p.get("pattern") or "").strip()
            if n:
                names.append(n)
        elif isinstance(p, str):
            names.append(p)
    if not names:
        return _unresolved(ddef)
    return _resolved(
        ddef,
        value=names[:16],
        confidence=0.7,
        evidence=["snapshot.components.patterns"],
        why=f"Observed component pattern families: {names[:16]}.",
        why_code="measure.component_patterns",
    )


def _component_interactive_density(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    n = int(ctx.snapshot.components.interactive_count or 0)
    if n <= 0:
        n = len(ctx.snapshot.layout.interactive_boxes or [])
    if n <= 0:
        return _unresolved(ddef)
    if n >= 40:
        band = "high"
    elif n >= 15:
        band = "medium"
    else:
        band = "low"
    return _resolved(
        ddef,
        value=band,
        confidence=0.7,
        evidence=["snapshot.components.interactive_count"],
        why=f"Interactive count {n} → density '{band}'.",
        why_code="measure.interactive_density",
    )


def _density_band(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    base = ctx.snapshot.spacing.base_unit_px
    body = None
    samples = ctx.snapshot.typography.body_samples or []
    for s in samples:
        if isinstance(s, dict):
            try:
                body = float(s.get("fontSize") or s.get("font_size") or 0) or None
            except (TypeError, ValueError):
                body = None
            if body:
                break
    # Heuristic: smaller base + smaller body → compact
    score_parts = []
    if base:
        score_parts.append(0.0 if base <= 4 else 0.5 if base <= 8 else 1.0)
    if body:
        score_parts.append(0.0 if body <= 13 else 0.5 if body <= 16 else 1.0)
    interactive = int(ctx.snapshot.components.interactive_count or 0)
    if interactive:
        score_parts.append(0.0 if interactive >= 40 else 0.5 if interactive >= 15 else 1.0)
    if not score_parts:
        return _unresolved(ddef)
    avg = sum(score_parts) / len(score_parts)
    if avg < 0.35:
        band = "compact"
    elif avg < 0.7:
        band = "comfortable"
    else:
        band = "spacious"
    return _resolved(
        ddef,
        value=band,
        confidence=0.65,
        evidence=["snapshot.spacing", "snapshot.typography", "snapshot.components"],
        why=f"Density band '{band}' from spacing/type/interactive heuristics.",
        why_code="infer.density_band",
        status="partial",
    )


def _density_score(ctx: _CompileContext, ddef: DecisionDef) -> EngineeringDecision:
    band_dec = _density_band(ctx, ddef)
    if band_dec.status == "unresolved":
        return _unresolved(ddef)
    mapping = {"compact": 0.25, "comfortable": 0.55, "spacious": 0.85}
    score = mapping.get(str(band_dec.value), 0.5)
    return _resolved(
        ddef,
        value=score,
        confidence=band_dec.confidence,
        evidence=band_dec.evidence,
        why=f"Numeric density score {score} from band {band_dec.value}.",
        why_code="derive.density_score",
        status="partial",
    )
