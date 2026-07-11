# License Intelligence — Architecture

Required layer for Resource Intelligence. **No provider adapter ships without a `LicenseProfile`.**

---

## Goals

Answer agent questions deterministically:

| Question | Field |
|----------|-------|
| Can I use this commercially? | `commercial_use` |
| Is attribution required? | `attribution_required` + `attribution_template` |
| Can MCP download this for the agent? | `mcp_download_allowed` |
| Can I redistribute it? | `redistribution_allowed` |
| Can AI use this? | `ai_training_allowed`, `dataset_use_allowed` |
| Can we automate API access? | `api_automation_allowed` |

---

## License classes

```text
MIT | ISC | Apache-2.0 | CC0 | CC-BY | CC-BY-SA | CC-BY-NC | OFL-1.1
Custom | Proprietary | Editorial | Unknown
```

Mapped to SPDX where possible. `Custom` requires `notes[]` citing official clause.

---

## Enforcement pipeline

**Default:** `ResourceDiscoveryRequest.commercial_required=True` (all MCP tools).

```text
Provider returns raw asset
  → resolve_license(asset, provider_default)
  → if provider.excluded or not license.commercial_use: drop (default catalog)
  → apply_policy(request.commercial_required, request.attribution_ok)
  → if blocked: drop asset + add license_warnings[]
  → if allowed: attach LicenseProfile + attribution_text
  → rank remaining candidates
```

### Policy gates

```python
def allows_use(profile: LicenseProfile, request: ResourceDiscoveryRequest) -> tuple[bool, str]:
    if request.commercial_required and not profile.commercial_use:
        return False, 'commercial_use_denied'
    if profile.attribution_required and not request.attribution_ok:
        return False, 'attribution_required'
    return True, ''

def automation_advisory(profile: LicenseProfile) -> list[str]:
    """Non-blocking warnings — does not remove provider from catalog."""
    ...
```

---

## Per-provider overrides

| Provider | Override rule |
|----------|---------------|
| **Iconify** | Inherit license from underlying collection (Lucide=ISC, etc.) |
| **DiceBear** | Per-style license from `dicebear.com/licenses` |
| **SVG Repo** | Per-asset filter — skip CC-BY-NC; provider stays in catalog |
| **Poly Pizza** | Per-model CC0 vs CC-BY |
| **Simple Icons** | CC0 file + trademark warning in `notes` |
| **Unsplash API** | Override: attribution required despite permissive image license |
| **Pexels API** | Override: prominent Pexels link in API integration |

---

## Exclusion registry

Hard-coded exclusions in `license/exclusions.py` — **commercial_use=false only**:

```text
humaaans → commercial_use not confirmed
```

Automation bans (unDraw, Storyset) are **not** catalog exclusions — set `api_automation_allowed=false` on the license profile.

---

## Attribution builder

When `attribution_required`:

```text
Unsplash API:
  Photo by {photographer} on Unsplash
  Links with utm_source={app_name}&utm_medium=referral

CC-BY:
  © {author} — {title} — {license_url}

Pexels API:
  Photos provided by Pexels (linked)
```

Returned in `ResourceAssetRef.attribution_text` — agent copies into UI credits.

---

## Agent-facing license summary

Each MCP response includes:

```json
{
  "license_summary": {
    "commercial_ok": true,
    "attribution_required": false,
    "warnings": ["Trademark: brand logos are not endorsement", "automation_prohibited_by_provider"],
    "blocked_providers": []
  }
}
```

---

## Revalidation

- `license/revalidator.py` — checklist runner (manual + future CI)
- Each provider `docs/providers/<id>/LICENSE.md` with last-verified date
- Quarterly review or on provider ToS change notification

---

## Legal disclaimer

Resource Intelligence provides **structured metadata** from official sources. It is not legal advice. Agents should surface `license_warnings` to users for production launches.
