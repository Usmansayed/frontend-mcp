"""Frozen V1 Pareto decision catalog — high-impact frontend engineering decisions only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisionDef:
    decision_id: str
    group: str
    importance: str
    impact_weight: float
    unit: str | None = None
    value_type: str = "any"  # number | string | list | object | enum
    why_unresolved: str = "No measurement yet — resolve before broad implementation."


# ~28 decisions across 8 groups. Do NOT expand V1 without A/B evidence.
V1_DECISION_DEFS: tuple[DecisionDef, ...] = (
    # Layout
    DecisionDef(
        "layout.archetype",
        "layout",
        "critical",
        0.98,
        value_type="enum",
        why_unresolved="Page structure archetype unknown — drives all section implementation.",
    ),
    DecisionDef(
        "layout.sidebar_width_px",
        "layout",
        "critical",
        0.94,
        unit="px",
        value_type="number",
        why_unresolved="Sidebar width unset — nav vs content balance undefined.",
    ),
    DecisionDef(
        "layout.content_max_width_px",
        "layout",
        "high",
        0.86,
        unit="px",
        value_type="number",
    ),
    DecisionDef(
        "layout.header_height_px",
        "layout",
        "high",
        0.78,
        unit="px",
        value_type="number",
    ),
    DecisionDef(
        "layout.grid_columns",
        "layout",
        "medium",
        0.62,
        value_type="number",
    ),
    # Information hierarchy
    DecisionDef(
        "hierarchy.primary_focus",
        "information_hierarchy",
        "critical",
        0.97,
        value_type="string",
        why_unresolved="Primary focus unknown — risk of competing headlines and flat hierarchy.",
    ),
    DecisionDef(
        "hierarchy.secondary_focus",
        "information_hierarchy",
        "high",
        0.82,
        value_type="string",
    ),
    DecisionDef(
        "hierarchy.reading_order",
        "information_hierarchy",
        "high",
        0.88,
        value_type="list",
        why_unresolved="Reading order unset — section composition will be guessed.",
    ),
    DecisionDef(
        "hierarchy.heading_levels_present",
        "information_hierarchy",
        "medium",
        0.58,
        value_type="list",
    ),
    # Navigation
    DecisionDef(
        "nav.pattern",
        "navigation_model",
        "critical",
        0.95,
        value_type="enum",
        why_unresolved="Navigation pattern unset (sidebar/top/hybrid) — IA foundation missing.",
    ),
    DecisionDef(
        "nav.density",
        "navigation_model",
        "high",
        0.74,
        value_type="enum",
    ),
    DecisionDef(
        "nav.primary_landmarks",
        "navigation_model",
        "medium",
        0.60,
        value_type="list",
    ),
    # Spacing
    DecisionDef(
        "spacing.base_unit_px",
        "spacing_system",
        "critical",
        0.93,
        unit="px",
        value_type="number",
        why_unresolved="Base spacing unit unknown — rhythm and density will drift.",
    ),
    DecisionDef(
        "spacing.scale_px",
        "spacing_system",
        "high",
        0.84,
        value_type="list",
    ),
    DecisionDef(
        "spacing.section_gap_px",
        "spacing_system",
        "high",
        0.80,
        unit="px",
        value_type="number",
    ),
    DecisionDef(
        "spacing.card_gap_px",
        "spacing_system",
        "medium",
        0.68,
        unit="px",
        value_type="number",
    ),
    # Typography
    DecisionDef(
        "type.font_families",
        "typography",
        "critical",
        0.90,
        value_type="list",
        why_unresolved="Font stack unset — brand voice and hierarchy typography undefined.",
    ),
    DecisionDef(
        "type.heading_scale_px",
        "typography",
        "critical",
        0.91,
        value_type="list",
        why_unresolved="Heading scale unset — hierarchy will be invented.",
    ),
    DecisionDef(
        "type.body_size_px",
        "typography",
        "high",
        0.79,
        unit="px",
        value_type="number",
    ),
    DecisionDef(
        "type.line_height_ratio",
        "typography",
        "medium",
        0.64,
        value_type="number",
    ),
    # Color
    DecisionDef(
        "color.background",
        "color_system",
        "high",
        0.83,
        value_type="string",
    ),
    DecisionDef(
        "color.text",
        "color_system",
        "high",
        0.85,
        value_type="string",
    ),
    DecisionDef(
        "color.accent",
        "color_system",
        "critical",
        0.89,
        value_type="string",
        why_unresolved="Accent color unset — CTAs and focus states will be arbitrary.",
    ),
    DecisionDef(
        "color.surface",
        "color_system",
        "medium",
        0.66,
        value_type="string",
    ),
    DecisionDef(
        "color.palette_size",
        "color_system",
        "low",
        0.42,
        value_type="number",
    ),
    # Component foundation
    DecisionDef(
        "component.foundation_status",
        "component_foundation",
        "critical",
        0.96,
        value_type="enum",
        why_unresolved="UI foundation unset — every component choice may reverse later.",
    ),
    DecisionDef(
        "component.pattern_families",
        "component_foundation",
        "high",
        0.72,
        value_type="list",
    ),
    DecisionDef(
        "component.interactive_density",
        "component_foundation",
        "medium",
        0.55,
        value_type="enum",
    ),
    # Visual density
    DecisionDef(
        "density.band",
        "visual_density",
        "high",
        0.81,
        value_type="enum",
        why_unresolved="Density band unknown (compact/comfortable/spacious) — spacing+type coupling unset.",
    ),
    DecisionDef(
        "density.score",
        "visual_density",
        "medium",
        0.56,
        value_type="number",
    ),
)


def catalog_by_id() -> dict[str, DecisionDef]:
    return {d.decision_id: d for d in V1_DECISION_DEFS}


def catalog_ids() -> list[str]:
    return [d.decision_id for d in V1_DECISION_DEFS]


def catalog_as_dicts() -> list[dict[str, Any]]:
    return [
        {
            "decision_id": d.decision_id,
            "group": d.group,
            "importance": d.importance,
            "impact_weight": d.impact_weight,
            "unit": d.unit,
            "value_type": d.value_type,
            "why_unresolved": d.why_unresolved,
        }
        for d in V1_DECISION_DEFS
    ]
