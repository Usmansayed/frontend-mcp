"""Per-route surface ledger — Meridian multi-route episode awareness."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.surface_type import derive_surface_type

ROUTE_SURFACES_ATTR = "route_surfaces"
ACTIVE_ROUTE_ATTR = "active_route_path"


def normalize_route_path(url: str | None) -> str | None:
    if not url:
        return None
    text = str(url).strip()
    if not text:
        return None
    if "://" in text or text.startswith("//"):
        parsed = urlparse(text if "://" in text else f"http:{text}")
        path = parsed.path or "/"
    else:
        path = text.split("?", 1)[0].split("#", 1)[0] or "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def _path_surface_hint(path: str) -> str | None:
    lower = path.lower()
    if any(k in lower for k in ("/settings", "/preferences", "/account", "/workspace")):
        return "settings_form"
    if any(k in lower for k in ("/login", "/signin", "/sign-in", "/signup", "/sign-up", "/auth")):
        return "auth"
    if any(k in lower for k in ("/dashboard", "/analytics", "/metrics", "/overview")):
        return "dashboard"
    if any(
        k in lower
        for k in ("/about", "/portfolio", "/work", "/landing", "/marketing", "/journey")
    ):
        return "marketing"
    if any(k in lower for k in ("/", "/home", "/landing", "/marketing")) and lower in (
        "/",
        "/home",
        "/landing",
        "/marketing",
    ):
        return "marketing"
    if any(k in lower for k in ("/customers", "/table", "/records", "/list")):
        return "data_table"
    return None


def derive_route_surface(
    path: str,
    *,
    intent: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> str:
    hint = _path_surface_hint(path)
    # Path-first for multi-route episodes; snapshot/intent refine when path is generic.
    if hint and hint != "unknown":
        if snapshot:
            refined = derive_surface_type(intent or path, snapshot=snapshot)
            # Prefer path hint unless snapshot strongly contradicts with settings/dashboard form cues
            if refined in ("settings_form", "auth", "dashboard", "marketing", "data_table"):
                if hint == "dashboard" and refined == "settings_form":
                    return "settings_form"
                if hint == "settings_form" and refined == "dashboard":
                    return "settings_form"
        return hint
    return derive_surface_type(intent or path, snapshot=snapshot)


def get_route_surfaces(psm: ProjectSituationModel) -> dict[str, Any]:
    raw = getattr(psm.episode, ROUTE_SURFACES_ATTR, None)
    if isinstance(raw, dict):
        return dict(raw)
    # Fallback for older episodes that only had retry_counters
    legacy = psm.episode.retry_counters.get("route_surfaces")
    return dict(legacy) if isinstance(legacy, dict) else {}


def active_route_path(psm: ProjectSituationModel) -> str | None:
    path = getattr(psm.episode, ACTIVE_ROUTE_ATTR, None)
    if path:
        return str(path)
    surfaces = get_route_surfaces(psm)
    if not surfaces:
        return None
    # Last inserted order not guaranteed; prefer most recently updated if present
    best = None
    best_ts = ""
    for entry in surfaces.values():
        if not isinstance(entry, dict):
            continue
        ts = str(entry.get("updated_at") or "")
        if ts >= best_ts:
            best_ts = ts
            best = entry.get("path")
    return str(best) if best else None


def active_route_surface(psm: ProjectSituationModel) -> str | None:
    path = active_route_path(psm)
    if not path:
        return None
    entry = get_route_surfaces(psm).get(path)
    if isinstance(entry, dict) and entry.get("surface"):
        return str(entry["surface"])
    return None


def routes_summary(psm: ProjectSituationModel) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for path, entry in sorted(get_route_surfaces(psm).items()):
        if not isinstance(entry, dict):
            continue
        out.append({
            "path": str(entry.get("path") or path),
            "surface": str(entry.get("surface") or "unknown"),
        })
    return out


def promote_mixed_from_routes(psm: ProjectSituationModel) -> str:
    """If ≥2 distinct route surfaces, set episode surface_type to mixed."""
    surfaces = {
        str(e.get("surface"))
        for e in get_route_surfaces(psm).values()
        if isinstance(e, dict) and e.get("surface") and e.get("surface") != "unknown"
    }
    if len(surfaces) >= 2:
        psm.episode.surface_type = "mixed"
        return "mixed"
    return str(getattr(psm.episode, "surface_type", None) or "unknown")


def upsert_route_surface(
    psm: ProjectSituationModel,
    url: str | None,
    *,
    snapshot: dict[str, Any] | None = None,
    family: str | None = None,
    scan_id: str | None = None,
    snapshot_id: str | None = None,
    intent: str | None = None,
    set_active: bool = True,
) -> dict[str, Any] | None:
    """Record a route surface. When ``set_active`` is False, ledger is updated
    without changing ``active_route_path`` (e.g. historical snapshot during ship).
    """
    path = normalize_route_path(url)
    if not path:
        return None
    from navigation.coordination_intelligence.models import _utc_now

    intent_text = intent
    if intent_text is None:
        intent_text = " ".join(f.intent for f in psm.episode.intent_stack)
    surface = derive_route_surface(path, intent=intent_text, snapshot=snapshot)
    routes = get_route_surfaces(psm)
    existing = routes.get(path) if isinstance(routes.get(path), dict) else {}
    paid = list(existing.get("paid_families") or [])
    if family and family not in paid:
        paid.append(family)
    entry = {
        "path": path,
        "surface": surface,
        "last_snapshot_id": snapshot_id or existing.get("last_snapshot_id"),
        "last_scan_id": scan_id or existing.get("last_scan_id"),
        "paid_families": paid,
        "updated_at": _utc_now(),
    }
    routes[path] = entry
    setattr(psm.episode, ROUTE_SURFACES_ATTR, routes)
    # Mirror into retry_counters for fingerprint / legacy readers
    psm.episode.retry_counters["route_surfaces"] = routes
    if set_active:
        setattr(psm.episode, ACTIVE_ROUTE_ATTR, path)
        psm.episode.retry_counters["active_route_path"] = path
    promote_mixed_from_routes(psm)
    return entry
