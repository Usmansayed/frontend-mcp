"""Envelope normalization into PSM Runtime — no raw MCP responses leave this layer."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import (
    POSTURE_REGRESSED,
    ProjectSituationModel,
    _utc_now,
)
from navigation.coordination_intelligence.psm.signature import refresh_cluster_signature

VERIFY_CAPABILITIES = frozenset({"browser_verify", "seo_recommendation_verify", "design_consistency_audit"})


def _merge_unique(target: list[str], items: list[str]) -> None:
    for item in items:
        if item and item not in target:
            target.append(item)


def _domain_producers(bundle: RuntimeArtifactBundle) -> dict[str, list[str]]:
    matrix = bundle.capability_graph.get("evidence_capability_matrix") or {}
    out: dict[str, list[str]] = {}
    for domain, spec in matrix.items():
        out[domain] = list(spec.get("primary_producers") or [])
    return out


def infer_capability_from_envelope(
    bundle: RuntimeArtifactBundle,
    envelope: dict[str, Any],
    *,
    capability_hint: str | None = None,
) -> str | None:
    if capability_hint:
        return capability_hint
    tool = envelope.get("tool")
    if isinstance(tool, str):
        return bundle.tool_to_capability.get(tool)
    return None


def _posture_for_capability(
    bundle: RuntimeArtifactBundle,
    capability_id: str,
    envelope: dict[str, Any],
) -> dict[str, str]:
    contract = bundle.capability_by_id.get(capability_id) or {}
    produces = contract.get("produces") or {}
    evidence_spec = produces.get("evidence") or {}
    out: dict[str, str] = {}
    for domain, spec in evidence_spec.items():
        if isinstance(spec, dict) and "posture" in spec:
            posture = spec["posture"]
            if isinstance(posture, str) and "|" in posture:
                left, right = [p.strip() for p in posture.split("|", 1)]
                posture = left if envelope.get("ok") else right
            out[domain] = posture
        elif capability_id in VERIFY_CAPABILITIES:
            data = envelope.get("data") or {}
            if "verified" in data:
                passed = bool(data.get("verified"))
            else:
                passed = bool(envelope.get("ok"))
            out[domain] = "verified" if passed else POSTURE_REGRESSED
        else:
            out[domain] = "known" if envelope.get("ok") else "partial"
    if not out and envelope.get("ok"):
        producers = _domain_producers(bundle)
        for domain, caps in producers.items():
            if capability_id in caps:
                out[domain] = "known"
    return out


def _snapshot_evidence_quality(data: dict[str, Any]) -> dict[str, Any]:
    """Host-facing snapshot quality — does not change advancement rules."""
    summary = data.get("snapshot_summary") or {}
    spec = data.get("engineering_spec") or {}
    gate = data.get("spec_revision_gate") or {}
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    layout = snap.get("layout") if isinstance(snap.get("layout"), dict) else {}
    if not layout and isinstance(data.get("layout"), dict):
        layout = data["layout"]
    regions = list(layout.get("regions") or [])
    degraded = list(summary.get("degraded") or snap.get("degraded") or data.get("degraded") or [])
    coverage = spec.get("coverage")
    coverage_ratio: float | None = None
    if isinstance(coverage, dict):
        for key in ("ratio", "resolved_ratio", "coverage_ratio"):
            if coverage.get(key) is not None:
                try:
                    coverage_ratio = float(coverage[key])
                except (TypeError, ValueError):
                    coverage_ratio = None
                break
        if coverage_ratio is None and coverage.get("resolved") is not None and coverage.get("total"):
            try:
                coverage_ratio = float(coverage["resolved"]) / max(float(coverage["total"]), 1.0)
            except (TypeError, ValueError):
                coverage_ratio = None
    layout_issues = summary.get("layout_issues")
    if layout_issues is None:
        layout_issues = len(list(layout.get("issues") or layout.get("overflow_issues") or []))
    interactive = summary.get("interactive_count")
    if interactive is None:
        interactive = len(list(layout.get("interactive_boxes") or []))
    thin = len(regions) == 0 and int(interactive or 0) < 5 and int(layout_issues or 0) == 0
    quality = {
        "snapshot_id": data.get("snapshot_id") or snap.get("snapshot_id"),
        "region_count": len(regions),
        "interactive_count": int(interactive or 0),
        "layout_issues": int(layout_issues or 0),
        "wcag_failures": int(summary.get("wcag_failures") or 0),
        "spacing_off_scale": int(summary.get("spacing_off_scale") or 0),
        "degraded_count": len(degraded),
        "degraded": degraded[:8],
        "engineering_spec_coverage": coverage,
        "coverage_ratio": coverage_ratio,
        "revision_required": bool(gate.get("revision_required")),
        "unresolved_engineering_decisions": len(
            list(
                spec.get("unresolved_by_impact")
                or (data.get("agent_summary") or {}).get("unresolved_engineering_decisions")
                or []
            )
        ),
        "thin": bool(thin),
        "evidence_useful": not thin and len(degraded) == 0,
    }
    quality.update(_specdiff_quality_fields(data))
    return quality


def _specdiff_quality_fields(data: dict[str, Any]) -> dict[str, Any]:
    """SpecDiff / revision honesty — advisory only, never changes advancement."""
    gate = data.get("spec_revision_gate") if isinstance(data.get("spec_revision_gate"), dict) else {}
    delta = data.get("engineering_delta")
    if not isinstance(delta, dict):
        delta = gate.get("engineering_delta") if isinstance(gate.get("engineering_delta"), dict) else {}
    top = list(delta.get("top_by_impact") or [])
    items = list(delta.get("items") or [])
    blocking = list(gate.get("blocking_drifts") or [])
    major = list(gate.get("major_drifts") or [])
    soft_skipped = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("severity") not in ("blocking", "major"):
            continue
        if item.get("from_value") is None or item.get("to_value") is None:
            soft_skipped += 1
    top_ids: list[str] = []
    for item in top[:8]:
        if isinstance(item, dict) and item.get("decision_id"):
            top_ids.append(str(item["decision_id"]))
        elif isinstance(item, str):
            top_ids.append(item)
    for bucket in (blocking, major):
        for item in bucket:
            if isinstance(item, dict) and item.get("decision_id"):
                did = str(item["decision_id"])
                if did not in top_ids:
                    top_ids.append(did)
            if len(top_ids) >= 8:
                break
    revision_required = bool(gate.get("revision_required"))
    reference_bound = gate.get("reference_bound")
    if reference_bound is None and gate:
        reference_bound = bool(gate.get("evaluated") or blocking or major or top)
    return {
        "specdiff_reference_bound": bool(reference_bound) if reference_bound is not None else bool(gate),
        "specdiff_evaluated": bool(gate.get("evaluated")),
        "revision_required": revision_required,
        "specdiff_passed": bool(gate.get("passed")) if "passed" in gate else (not revision_required if gate else None),
        "delta_top_count": len(top) or len(top_ids),
        "delta_top_ids": top_ids[:8],
        "blocking_drift_count": len(blocking),
        "major_drift_count": len(major),
        "soft_seed_skipped_count": soft_skipped,
        "soft_seed_partial": bool(soft_skipped > 0 and not revision_required),
    }


def _capability_outcome(
    capability_id: str,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    """Separate evidence quality from envelope transport success."""
    data = envelope.get("data") or {}
    explicit = data.get("coordination_evidence")
    if isinstance(explicit, dict):
        outcome = dict(explicit)
        raw = outcome.get("outcome") or outcome.get("status") or "noop"
        status = str(raw)
        outcome["status"] = {
            "success": "succeeded",
            "succeeded": "succeeded",
            "degraded": "provisional",
            "provisional": "provisional",
            "failure": "failed",
            "failed": "failed",
            "noop": "noop",
        }.get(status, status)
    else:
        summary = data.get("agent_summary") or {}
        degraded = list(envelope.get("degraded") or []) + list(summary.get("degraded") or [])
        blocking = list(summary.get("blocking") or [])
        tool = str(envelope.get("tool") or "")
        quality: dict[str, Any] = {}
        noop_tools = {
            "perception_inspiration_session_end",
            "perception_resource_session_end",
            "perception_figma_status",
            "perception_figma_connect",
        }
        if tool in noop_tools and envelope.get("ok"):
            status = "noop"
        elif not envelope.get("ok"):
            status = "failed"
        elif tool == "perception_inspiration_collect":
            collection = data.get("inspiration_collection") or {}
            hits = list(collection.get("hits") or [])
            usable_refs = sum(
                1 for hit in hits
                if isinstance(hit, dict) and bool(hit.get("inspiration_blob"))
            )
            eng = data.get("engineering_spec") or {}
            unresolved = list(
                eng.get("unresolved_by_impact")
                or (data.get("agent_summary") or {}).get("unresolved_engineering_decisions")
                or []
            )
            profiles = sum(
                1 for hit in hits
                if isinstance(hit, dict) and (hit.get("profile") or hit.get("extracted_profile"))
            )
            quality = {
                "usable_image_refs": usable_refs,
                "total_hits": len(hits),
                "minimum_required": 3,
                "profiles_extracted": profiles,
                "seed_unresolved_count": len(unresolved),
                "reference_bind_quality": (
                    (data.get("reference_bind") or {}).get("quality")
                    or (data.get("reference_bind") or {}).get("meta", {}).get("quality")
                ),
                "implementation_ready": bool(
                    (data.get("reference_bind") or {}).get("implementation_ready")
                ),
            }
            status = "succeeded" if usable_refs >= 3 and not blocking else "provisional"
        elif tool == "perception_build_design_snapshot":
            # Transport ok still advances; thin/degraded honesty lives in quality only.
            quality = _snapshot_evidence_quality(data)
            status = "succeeded" if not blocking else "provisional"
        elif tool == "perception_design_review" and (data.get("mode") or "") == "ship":
            ship_gate = data.get("ship_gate") or {}
            council_clear = bool(ship_gate.get("council_clear"))
            quality = {
                "mode": "ship",
                "challenges_emitted": len(data.get("challenges") or []),
                "open_high_roi": int(ship_gate.get("open_high_roi") or 0),
                "council_clear": council_clear,
                "coverage": ship_gate.get("coverage"),
                "coverage_checks": ship_gate.get("coverage_checks"),
                "surface_type": ship_gate.get("surface_type"),
                "thin_clear": bool(
                    council_clear and str(ship_gate.get("coverage") or "") == "thin"
                ),
            }
            status = "succeeded" if council_clear else "provisional"
        elif tool == "perception_design_review":
            delta = data.get("engineering_delta") or {}
            top = list(delta.get("top_by_impact") or [])
            gate = data.get("spec_revision_gate") or {}
            findings = list(data.get("top_findings") or data.get("findings") or [])
            quality = {
                "mode": str(data.get("mode") or "review"),
                "passed": data.get("passed"),
                "blocking_findings": len(data.get("blocking_findings") or []),
                "findings_count": len(findings),
            }
            quality.update(_specdiff_quality_fields(data))
            # Prefer count from SpecDiff fields when delta present
            if quality.get("delta_top_count") == 0 and top:
                quality["delta_top_count"] = len(top)
            if data.get("passed") is False:
                status = "provisional"
            elif degraded or blocking:
                status = "provisional"
            else:
                status = "succeeded"
        elif tool == "perception_select_component_foundation":
            fs = data.get("foundation_selection") if isinstance(data.get("foundation_selection"), dict) else {}
            chosen = fs.get("chosen")
            library_id = fs.get("library_id") or (
                chosen.get("registry") if isinstance(chosen, dict) else None
            )
            if not chosen and not library_id:
                selected = data.get("selected")
                if isinstance(selected, dict):
                    chosen = selected.get("id") or selected.get("name") or selected
                    library_id = selected.get("library_id") or selected.get("registry")
                else:
                    chosen = selected
            usable_flag = fs.get("usable")
            relevance = None
            if isinstance(chosen, dict):
                try:
                    relevance = float(chosen.get("relevance_score"))
                except (TypeError, ValueError):
                    relevance = None
            if usable_flag is None:
                # Legacy envelopes: require relevance floor when score present.
                from navigation.component_intelligence.selection.filter import (
                    SELECT_MIN_RELEVANCE,
                )

                if isinstance(chosen, dict) and relevance is not None:
                    usable_flag = relevance >= SELECT_MIN_RELEVANCE
                else:
                    usable_flag = bool(chosen) or bool(library_id)
            # Library-first: usable when library locked even without a block starter.
            usable = bool(usable_flag) and (bool(chosen) or bool(library_id)) and not blocking
            # Persist library id as the foundation — never a specialty block name.
            selection_payload: dict[str, Any] | None = None
            if usable:
                if isinstance(chosen, dict):
                    selection_payload = dict(chosen)
                else:
                    selection_payload = {}
                selection_payload["library"] = library_id or selection_payload.get("registry")
                selection_payload["library_id"] = library_id or selection_payload.get("library")
                selection_payload["lock_evidence"] = list(fs.get("lock_evidence") or [])
                starter = fs.get("starter")
                if isinstance(starter, dict):
                    selection_payload["starter_name"] = starter.get("name") or starter.get("title")
            quality = {
                "chosen": bool(chosen) or bool(library_id),
                "usable": usable,
                "selection": selection_payload if usable else chosen,
                "library_id": library_id,
                "relevance_score": relevance,
                "reject_reason": fs.get("reject_reason"),
            }
            status = "succeeded" if usable else "provisional"
        elif capability_id in VERIFY_CAPABILITIES or tool == "perception_verify":
            # Transport ok ≠ criteria pass — only data.verified=true is success.
            if "verified" in data:
                verified = bool(data.get("verified"))
                quality = {"verified": verified}
                status = "succeeded" if verified and not blocking else "failed"
            elif degraded or blocking:
                status = "provisional"
            else:
                status = "succeeded"
        elif degraded or blocking:
            status = "provisional"
        else:
            status = "succeeded"
        outcome = {
            "status": status,
            "advancement_eligible": status == "succeeded",
            "quality": quality,
            "artifact_refs": {},
        }

    outcome.setdefault("capability_id", capability_id)
    outcome.setdefault("advancement_eligible", outcome.get("status") == "succeeded")
    outcome.setdefault("quality", {})
    outcome.setdefault("artifact_refs", {})
    outcome.setdefault("degraded_reasons", list(envelope.get("degraded") or []))
    outcome.setdefault("failure_reason", str(envelope.get("error") or "") or None)
    outcome["updated_at"] = _utc_now()
    return outcome


def apply_envelope(
    psm: ProjectSituationModel,
    envelope: dict[str, Any],
    bundle: RuntimeArtifactBundle,
    *,
    capability_id: str | None = None,
) -> str | None:
    """Mutate PSM from a normalized MCP envelope. Returns resolved capability_id."""
    cap = infer_capability_from_envelope(bundle, envelope, capability_hint=capability_id)
    if not cap:
        return None

    attempts = psm.episode.retry_counters.setdefault("capability_attempts", {})
    attempts[cap] = int(attempts.get(cap, 0)) + 1
    capability_outcome = _capability_outcome(cap, envelope)
    psm.evidence.capability_ledger[cap] = capability_outcome

    # Persist usable foundation select for live Spec / catalog sync.
    if (
        str(envelope.get("tool") or "") == "perception_select_component_foundation"
        or cap == "component_select"
    ):
        quality = capability_outcome.get("quality") if isinstance(capability_outcome.get("quality"), dict) else {}
        if capability_outcome.get("status") == "succeeded" and quality.get("usable") is not False:
            selection = quality.get("selection")
            if isinstance(selection, dict):
                from navigation.engineering_knowledge.reference_binding import (
                    store_foundation_selection,
                )

                store_foundation_selection(selection, psm=psm)

    data = envelope.get("data") or {}
    ship_gate = data.get("ship_gate") if isinstance(data.get("ship_gate"), dict) else {}
    if (data.get("mode") == "ship") or ("council_clear" in ship_gate):
        clear = bool(ship_gate.get("council_clear"))
        if not ship_gate and isinstance(capability_outcome.get("quality"), dict):
            clear = bool((capability_outcome.get("quality") or {}).get("council_clear"))
        psm.episode.retry_counters["ship_council_run"] = True
        psm.episode.retry_counters["ship_council_clear"] = clear

    if envelope.get("session_id"):
        psm.artifacts.session_id = envelope["session_id"]
    if envelope.get("scan_id"):
        psm.artifacts.scan_id = envelope["scan_id"]
    if envelope.get("url"):
        psm.artifacts.website_url = envelope["url"]

    if data.get("snapshot_id"):
        psm.artifacts.snapshot_id = data["snapshot_id"]
    if data.get("audit_id"):
        psm.artifacts.audit_id = data["audit_id"]

    # Per-route surface ledger (Meridian multi-route)
    url = envelope.get("url") or data.get("url") or psm.artifacts.website_url
    snap_payload = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else None
    if not snap_payload and isinstance(data.get("layout"), dict):
        snap_payload = {"layout": data.get("layout")}
    tool = str(envelope.get("tool") or "")
    family = None
    if cap == "browser_observe" or tool in (
        "perception_navigate_and_observe",
        "perception_observe",
        "perception_execute_actions",
        "perception_execute_script",
    ):
        family = "observe"
    elif cap == "design_snapshot" or tool == "perception_build_design_snapshot":
        family = "snapshot"
    if url and family:
        from navigation.coordination_intelligence.planning.route_surfaces import (
            upsert_route_surface,
        )

        upsert_route_surface(
            psm,
            str(url),
            snapshot=snap_payload,
            family=family,
            scan_id=envelope.get("scan_id") or data.get("scan_id"),
            snapshot_id=data.get("snapshot_id"),
        )

    summary = data.get("agent_summary") or {}
    _merge_unique(psm.evidence.blocking, list(summary.get("blocking") or []))
    _merge_unique(psm.evidence.degraded, list(envelope.get("degraded") or []))
    _merge_unique(psm.evidence.degraded, list(summary.get("degraded") or []))

    if envelope.get("error"):
        psm.evidence.blocking.append(str(envelope["error"]))

    if cap == "auth_gate":
        auth = data.get("auth_gate") or data
        if auth.get("requires_human"):
            psm.episode.auth_status = "requires_human"
            psm.constraints.human_gates.append("auth_gate_requires_human")
        else:
            psm.episode.auth_status = "clear"

    if cap == "browser_observe" and envelope.get("ok"):
        from navigation.coordination_intelligence.planning.section_checklist import (
            mark_section_observed,
        )

        section_id = data.get("section_id")
        mark_section_observed(
            psm,
            section_id=str(section_id) if section_id else None,
        )

    if cap in VERIFY_CAPABILITIES:
        data = envelope.get("data") or {}
        # Strict: transport ok does not mean criteria passed.
        if "verified" in data:
            passed = bool(data.get("verified"))
        else:
            passed = bool(envelope.get("ok"))
        psm.episode.verification_status = "passed" if passed else "failed"
        if not passed:
            psm.episode.retry_counters["verify_loop"] = int(
                psm.episode.retry_counters.get("verify_loop", 0)
            ) + 1
        # Section progress only when section_id is explicit (page-level verify does not close blocks).
        section_id = data.get("section_id") or (data.get("criteria") or {}).get("section_id")
        if passed and section_id:
            from navigation.coordination_intelligence.planning.section_checklist import (
                mark_section_verified,
            )

            mark_section_verified(
                psm,
                section_id=str(section_id),
                verified=True,
            )

    if cap == "form_probe" and envelope.get("ok"):
        psm.evidence.unknown_gaps = [
            g for g in psm.evidence.unknown_gaps if g != "form_rules"
        ]

    postures = (
        {}
        if capability_outcome.get("status") in ("failed", "noop")
        else _posture_for_capability(bundle, cap, envelope)
    )
    if cap == "component_select" and capability_outcome.get("status") == "succeeded":
        postures["design_system"] = "known"
    now = _utc_now()
    for domain, posture in postures.items():
        if domain not in psm.evidence.domains:
            continue
        state = psm.evidence.domains[domain]
        if capability_outcome.get("status") == "provisional" and posture in ("known", "verified"):
            posture = "partial"
        if psm.evidence.degraded and cap in VERIFY_CAPABILITIES and posture == "verified":
            posture = "partial"
        state.posture = posture
        state.updated_at = now
        state.source_capability = cap
        if psm.artifacts.scan_id:
            state.artifact_refs["scan_id"] = psm.artifacts.scan_id

    psm.touch()
    refresh_cluster_signature(psm)
    return cap
