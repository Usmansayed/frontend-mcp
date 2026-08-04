"""Source adapters into FrontendEngineeringSpec — never invent private CAD formats.

Every path funnels through DesignSnapshot measurements when possible.
Seed Specs are allowed for discovery stages (inspiration/figma) with low-confidence priors.
"""
from __future__ import annotations

from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.engineering_knowledge.compiler import EngineeringKnowledgeCompiler
from navigation.engineering_knowledge.models import EngineeringDecision, FrontendEngineeringSpec

_COMPILER = EngineeringKnowledgeCompiler()


def compile_live_spec(
    snapshot: DesignSnapshot,
    *,
    foundation_hint: dict[str, Any] | None = None,
) -> FrontendEngineeringSpec:
    return _COMPILER.compile_from_snapshot(
        snapshot,
        source_kind="live_dom",
        foundation_hint=foundation_hint,
    )


def compile_reference_spec(
    snapshot: DesignSnapshot,
    *,
    provenance: dict[str, Any] | None = None,
) -> FrontendEngineeringSpec:
    return _COMPILER.compile_from_snapshot(
        snapshot,
        source_kind="reference",
        provenance=provenance,
    )


def compile_from_snapshot_dict(
    data: dict[str, Any],
    *,
    source_kind: str = "reference",
    provenance: dict[str, Any] | None = None,
) -> FrontendEngineeringSpec:
    snapshot = DesignSnapshot.from_dict(data)
    return _COMPILER.compile_from_snapshot(
        snapshot,
        source_kind=source_kind,
        provenance=provenance,
    )


def compile_inspiration_seed_spec(
    *,
    query: str,
    hits: list[dict[str, Any]] | None = None,
    profiles: list[dict[str, Any]] | None = None,
) -> FrontendEngineeringSpec:
    """Pre-measurement Spec from inspiration discovery/collect.

    Does NOT invent geometry. Soft priors only (partial, low confidence).
    Host must open agent_view_url → build_design_snapshot for resolved Spec.
    """
    spec = _COMPILER.empty_spec(
        source_kind="inspiration_seed",
        provenance={
            "query": query,
            "hit_count": len(hits or []),
            "next_step": (
                "Open top agent_view_url in session, run perception_build_design_snapshot, "
                "then use data.engineering_spec as the reference Spec."
            ),
        },
    )
    profiles = list(profiles or [])
    if not profiles and hits:
        for h in hits[:5]:
            meta = h.get("metadata") or {}
            profile = meta.get("profile") or h.get("profile") or {}
            if isinstance(profile, dict) and profile:
                profiles.append(profile)

    _apply_soft_priors(spec, profiles, query=query)
    # Keep unresolved geometry decisions explicit with next-step evidence path
    for did in (
        "layout.sidebar_width_px",
        "layout.content_max_width_px",
        "spacing.base_unit_px",
        "type.heading_scale_px",
        "color.accent",
    ):
        dec = spec.decisions.get(did)
        if dec and dec.status == "unresolved":
            dec.evidence = ["requires_live_measure"]
            dec.why = (
                f"{dec.why} Measure via DesignSnapshot after opening inspiration agent_view_url."
            )
            dec.why_code = "inspiration.requires_snapshot"
    return spec


def compile_figma_seed_spec(context: dict[str, Any] | None) -> FrontendEngineeringSpec:
    """Seed Spec from Figma context payload — partial priors only until DOM measure."""
    ctx = context or {}
    spec = _COMPILER.empty_spec(
        source_kind="figma_seed",
        provenance={
            "file_key": ctx.get("file_key") or ctx.get("fileKey"),
            "node_id": ctx.get("node_id") or ctx.get("nodeId"),
            "next_step": "Implement from Figma + verify with live DesignSnapshot → Spec.",
        },
    )
    # Map common figma-ish fields if present (deterministic, no LLM)
    frames = ctx.get("frames") or ctx.get("nodes") or []
    if isinstance(frames, list) and frames:
        first = frames[0] if isinstance(frames[0], dict) else {}
        size = first.get("size") or first.get("absoluteBoundingBox") or {}
        w = size.get("width")
        try:
            if w is not None and float(w) >= 180:
                _set_partial(
                    spec,
                    "layout.content_max_width_px",
                    int(round(float(w))),
                    confidence=0.4,
                    evidence=["figma_frame_size"],
                    why=f"Figma frame width {w} as content max prior (partial).",
                    why_code="figma.frame_width",
                )
        except (TypeError, ValueError):
            pass

    tokens = ctx.get("tokens") or ctx.get("variables") or {}
    if isinstance(tokens, dict):
        for key in ("primary", "accent", "--primary", "brand"):
            if key in tokens and tokens[key]:
                _set_partial(
                    spec,
                    "color.accent",
                    str(tokens[key]),
                    confidence=0.55,
                    evidence=["figma_tokens"],
                    why=f"Accent prior from Figma token {key}.",
                    why_code="figma.token_accent",
                )
                break

    fonts = ctx.get("fonts") or ctx.get("font_families") or []
    if isinstance(fonts, list) and fonts:
        _set_partial(
            spec,
            "type.font_families",
            [str(f) for f in fonts[:4]],
            confidence=0.5,
            evidence=["figma_fonts"],
            why="Font stack prior from Figma context.",
            why_code="figma.fonts",
        )

    return spec


def _apply_soft_priors(
    spec: FrontendEngineeringSpec,
    profiles: list[dict[str, Any]],
    *,
    query: str,
) -> None:
    styles = []
    page_types = []
    components = []
    for p in profiles:
        if p.get("style"):
            styles.append(str(p["style"]).lower())
        if p.get("page_type"):
            page_types.append(str(p["page_type"]).lower())
        for c in p.get("components") or []:
            components.append(str(c).lower())

    q = query.lower()
    joined = " ".join(styles + page_types + [q])

    # Layout archetype priors (enum only, partial)
    if any(k in joined for k in ("dashboard", "saas", "admin", "sidebar")):
        _set_partial(
            spec,
            "layout.archetype",
            "left_sidebar_dashboard",
            confidence=0.35,
            evidence=["inspiration_profile", "query"],
            why="Inspiration/query suggests dashboard sidebar archetype (unverified).",
            why_code="inspiration.soft.dashboard",
        )
        _set_partial(
            spec,
            "nav.pattern",
            "left_sidebar",
            confidence=0.35,
            evidence=["inspiration_profile", "query"],
            why="Dashboard inspiration usually implies left nav (unverified).",
            why_code="inspiration.soft.nav_sidebar",
        )
        _set_partial(
            spec,
            "density.band",
            "comfortable",
            confidence=0.3,
            evidence=["inspiration_profile"],
            why="Product UI density prior: comfortable (unverified).",
            why_code="inspiration.soft.density",
        )
    elif any(k in joined for k in ("landing", "marketing", "homepage", "hero")):
        _set_partial(
            spec,
            "layout.archetype",
            "top_nav_marketing",
            confidence=0.35,
            evidence=["inspiration_profile", "query"],
            why="Landing/marketing inspiration → top-nav marketing archetype (unverified).",
            why_code="inspiration.soft.landing",
        )
        _set_partial(
            spec,
            "nav.pattern",
            "top_bar",
            confidence=0.35,
            evidence=["inspiration_profile", "query"],
            why="Marketing pages typically use top navigation (unverified).",
            why_code="inspiration.soft.nav_top",
        )
        _set_partial(
            spec,
            "density.band",
            "spacious",
            confidence=0.3,
            evidence=["inspiration_profile"],
            why="Marketing density prior: spacious (unverified).",
            why_code="inspiration.soft.density_spacious",
        )

    if components:
        unique = list(dict.fromkeys(components))[:12]
        _set_partial(
            spec,
            "component.pattern_families",
            unique,
            confidence=0.4,
            evidence=["inspiration_profile.components"],
            why=f"Component pattern tags from inspiration profiles: {unique[:6]}.",
            why_code="inspiration.soft.components",
        )
        _set_partial(
            spec,
            "component.foundation_status",
            {"status": "inspiration_tagged", "patterns": unique[:8]},
            confidence=0.25,
            evidence=["inspiration_profile"],
            why="Foundation still unset; pattern tags only.",
            why_code="inspiration.soft.foundation",
        )

    if "linear" in joined or "minimal" in styles:
        # Still no adjectives as values — map to density/type priors
        _set_partial(
            spec,
            "density.band",
            "compact",
            confidence=0.28,
            evidence=["inspiration_style_tag"],
            why="Style tags associated with compact product UI (unverified).",
            why_code="inspiration.soft.compact",
        )


def _set_partial(
    spec: FrontendEngineeringSpec,
    decision_id: str,
    value: Any,
    *,
    confidence: float,
    evidence: list[str],
    why: str,
    why_code: str,
) -> None:
    dec = spec.decisions.get(decision_id)
    if dec is None:
        return
    dec.status = "partial"
    dec.value = value
    dec.confidence = confidence
    dec.evidence = list(evidence)
    dec.why = why
    dec.why_code = why_code
