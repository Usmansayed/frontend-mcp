"""Strict post-deploy section checklist — observe + verify each block before claim-done."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

SECTION_CHECKLIST_KEY = "section_checklist"
MAX_SECTIONS = 5
PREFERRED_ROLES = ("header", "nav", "aside", "sidebar", "main", "footer", "section", "form")


def _role_key(region: dict[str, Any], index: int) -> str:
    role = str(region.get("role") or region.get("label") or "section").lower().strip() or "section"
    return f"{role}:{index}"


def seed_section_checklist_from_regions(
    psm: ProjectSituationModel,
    regions: list[dict[str, Any]] | None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Build a 3–5 section checklist from layout regions. Idempotent unless force=True."""
    existing = psm.episode.retry_counters.get(SECTION_CHECKLIST_KEY)
    if isinstance(existing, dict) and existing.get("sections") and not force:
        return existing

    picked: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for region in regions or []:
        if not isinstance(region, dict):
            continue
        role = str(region.get("role") or region.get("label") or "").lower()
        if role not in PREFERRED_ROLES and role not in {"navigation", "complementary", "content"}:
            continue
        # Prefer one of each chrome role; allow multiple sections up to cap.
        if role in {"header", "nav", "aside", "sidebar", "main", "footer", "form", "navigation"}:
            if role in seen_roles or role == "sidebar" and "aside" in seen_roles:
                continue
            seen_roles.add(role if role != "sidebar" else "aside")
        rect = region.get("rect") if isinstance(region.get("rect"), dict) else {}
        section_id = _role_key(region, len(picked))
        picked.append({
            "section_id": section_id,
            "role": role or "section",
            "label": str(region.get("label") or region.get("text") or role or "section")[:60],
            "rect": rect,
            "observed": False,
            "verified": False,
            "updated_at": None,
        })
        if len(picked) >= MAX_SECTIONS:
            break

    # Fallback minimal checklist when regions are sparse but draft exists.
    if not picked and psm.artifacts.snapshot_id:
        picked = [
            {
                "section_id": "main:0",
                "role": "main",
                "label": "main",
                "rect": {},
                "observed": False,
                "verified": False,
                "updated_at": None,
            },
        ]

    checklist = {
        "sections": picked,
        "required": bool(picked),
        "seeded_at": _utc_now(),
        "complete": False,
    }
    psm.episode.retry_counters[SECTION_CHECKLIST_KEY] = checklist
    return checklist


def get_section_checklist(psm: ProjectSituationModel) -> dict[str, Any] | None:
    raw = psm.episode.retry_counters.get(SECTION_CHECKLIST_KEY)
    return raw if isinstance(raw, dict) else None


def mark_section_observed(psm: ProjectSituationModel, *, section_id: str | None = None) -> dict[str, Any] | None:
    checklist = get_section_checklist(psm)
    if not checklist:
        return None
    sections = list(checklist.get("sections") or [])
    now = _utc_now()
    if section_id:
        for item in sections:
            if item.get("section_id") == section_id:
                item["observed"] = True
                item["updated_at"] = now
                break
    else:
        # Page-level observe advances the first incomplete section.
        for item in sections:
            if not item.get("observed"):
                item["observed"] = True
                item["updated_at"] = now
                break
    checklist["sections"] = sections
    checklist["complete"] = section_checklist_complete(checklist)
    psm.episode.retry_counters[SECTION_CHECKLIST_KEY] = checklist
    return checklist


def mark_section_verified(
    psm: ProjectSituationModel,
    *,
    section_id: str | None = None,
    verified: bool,
) -> dict[str, Any] | None:
    checklist = get_section_checklist(psm)
    if not checklist or not verified:
        return checklist
    sections = list(checklist.get("sections") or [])
    now = _utc_now()
    target = None
    if section_id:
        target = next((s for s in sections if s.get("section_id") == section_id), None)
    if target is None:
        # Prefer first observed-but-unverified; else first unverified.
        target = next((s for s in sections if s.get("observed") and not s.get("verified")), None)
        if target is None:
            target = next((s for s in sections if not s.get("verified")), None)
    if target is None:
        return checklist
    target["observed"] = True
    target["verified"] = True
    target["updated_at"] = now
    checklist["sections"] = sections
    checklist["complete"] = section_checklist_complete(checklist)
    psm.episode.retry_counters[SECTION_CHECKLIST_KEY] = checklist
    return checklist


def section_checklist_complete(checklist: dict[str, Any] | None) -> bool:
    if not checklist or not checklist.get("required"):
        return True
    sections = list(checklist.get("sections") or [])
    if not sections:
        return True
    return all(bool(s.get("observed")) and bool(s.get("verified")) for s in sections)


def episode_needs_section_checklist(
    psm: ProjectSituationModel,
    strategy: dict[str, Any],
) -> bool:
    scope = str(strategy.get("task_scope") or "")
    influence = str(strategy.get("influence_level") or "")
    if scope in ("hotfix", "surgical", "debug"):
        return False
    if influence == "minimal" and scope not in ("design_driven", "redesign", "system_setup"):
        return False
    checklist = get_section_checklist(psm)
    if checklist is None or not checklist.get("required"):
        return False
    return not section_checklist_complete(checklist)


def incomplete_sections(psm: ProjectSituationModel) -> list[str]:
    checklist = get_section_checklist(psm)
    if not checklist:
        return []
    out: list[str] = []
    for item in checklist.get("sections") or []:
        if not (item.get("observed") and item.get("verified")):
            out.append(str(item.get("section_id") or item.get("role") or "section"))
    return out


def build_section_verify_assertions(section: dict[str, Any]) -> list[str]:
    """JS assertions that prove a section node is present and laid out."""
    role = str(section.get("role") or "main").lower()
    tag = {
        "nav": "nav",
        "navigation": "nav",
        "aside": "aside",
        "sidebar": "aside",
        "header": "header",
        "footer": "footer",
        "main": "main",
        "form": "form",
        "section": "section",
        "content": "main",
    }.get(role, "main")
    return [
        f"() => {{ const el = document.querySelector('{tag}'); "
        f"if (!el) return false; const r = el.getBoundingClientRect(); "
        f"return r.width > 8 && r.height > 8; }}",
    ]
