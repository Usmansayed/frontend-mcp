"""Engineering Knowledge — Spec contract, catalog, compiler, SpecDiff, adapters."""

from navigation.engineering_knowledge.adapters import (
    compile_figma_seed_spec,
    compile_from_snapshot_dict,
    compile_inspiration_seed_spec,
    compile_live_spec,
    compile_reference_spec,
)
from navigation.engineering_knowledge.catalog import (
    V1_DECISION_DEFS,
    catalog_as_dicts,
    catalog_by_id,
    catalog_ids,
)
from navigation.engineering_knowledge.compiler import EngineeringKnowledgeCompiler
from navigation.engineering_knowledge.models import (
    V1_GROUPS,
    EngineeringDecision,
    FrontendEngineeringSpec,
)
from navigation.engineering_knowledge.reference_binding import (
    bind_reference_spec,
    clear_reference_spec,
    evaluate_revision_gate,
    get_reference_spec,
    resolve_psm_for_session,
)
from navigation.engineering_knowledge.spec_diff import EngineeringDelta, SpecDeltaItem, diff_specs

__all__ = [
    "V1_DECISION_DEFS",
    "V1_GROUPS",
    "EngineeringDecision",
    "FrontendEngineeringSpec",
    "EngineeringKnowledgeCompiler",
    "EngineeringDelta",
    "SpecDeltaItem",
    "diff_specs",
    "catalog_as_dicts",
    "catalog_by_id",
    "catalog_ids",
    "compile_live_spec",
    "compile_reference_spec",
    "compile_from_snapshot_dict",
    "compile_inspiration_seed_spec",
    "compile_figma_seed_spec",
    "bind_reference_spec",
    "clear_reference_spec",
    "get_reference_spec",
    "evaluate_revision_gate",
    "resolve_psm_for_session",
]
