# Perfect Coordination Layer — Phase C Design (Route-aware Meridian)

**Date:** 2026-07-18  
**Status:** Approved (C1)  
**Depends on:** Phase A/B (`coordinator_card.v1`, `episode_card.v1`)

---

## 1. Problem

Episode `surface_type=mixed` is sticky but **not route-aware**. After `/dashboard` → `/settings`, Ship Council and backlog still lack an active-route surface, so dashboard heuristics can fire on settings pages (Meridian failure mode).

## 2. Goals

| ID | Goal |
|----|------|
| G1 | Record per-route surface + last evidence on observe/snapshot with URL |
| G2 | Episode stays `mixed` when ≥2 distinct route surfaces |
| G3 | Ship Council uses **active route** surface for detectors |
| G4 | `episode_card` exposes `active_route` + `routes[]` |
| G5 | Baseline stays green; new EXP-024 locks Meridian path |

## 3. Non-goals

- New claim gates  
- Splitting episodes per route  
- Requiring inspiration per route  

## 4. Data model

Store on `EpisodeState` (preferred) or `retry_counters["route_surfaces"]` for persistence:

```json
{
  "/dashboard": {
    "path": "/dashboard",
    "surface": "dashboard",
    "last_snapshot_id": "snap_dash",
    "last_scan_id": "scan_dash",
    "paid_families": ["observe", "snapshot"]
  },
  "/settings": {
    "path": "/settings",
    "surface": "settings_form",
    "last_snapshot_id": "snap_set",
    "paid_families": ["observe", "snapshot"]
  }
}
```

Also: `active_route_path: str | None` on episode (last upserted path).

## 5. Behavior

1. **Normalize / apply_envelope:** when tool is observe or design_snapshot and URL present → `upsert_route_surface(psm, url, snapshot=...)`.  
2. **derive per-route surface:** intent + path keywords (`/settings` → settings_form) + optional layout.  
3. **apply_surface_type:** if `len(unique surfaces among routes) >= 2` → episode `mixed`.  
4. **Ship:** `effective_surface = route_surfaces[active].surface or episode.surface_type`.  
5. **Cards:** `build_episode_card` / coordinator optional fields `active_route`, `routes`.  
6. **Fingerprint:** include `active_route_path` + sorted route surface map.

## 6. Testing

- Unit: path→surface; mixed promotion; ship uses settings on `/settings`  
- EXP-024 lab: Meridian dashboard then settings → active_route settings_form; ship_signals settings-aware / KPI absent  
- Baseline promote when green
