# Iconify — License & API Notes

**Last verified:** 2026-07-11  
**Status:** P0 adapter planned

## Platform license

- Iconify **API software**: MIT ([GitHub](https://github.com/iconify/api))
- **Icons served**: each collection has its own license — must resolve per prefix

## API

- Public HTTP API: `https://api.iconify.design`
- Self-host: `@iconify/api` npm, Docker
- No API key for public tier; self-host for production scale

## Commercial use

- Yes for most open-source icon sets
- Verify per collection (e.g. Lucide=ISC, MDI=Apache/Pictogrammers)

## Attribution

- Usually not required in UI for MIT/ISC sets
- Some collections may require attribution — check collection metadata

## MCP orchestration

- **Allowed:** Search API, return SVG URL, agent fetches at build time
- **Not allowed:** Bulk mirror entire icon sets into MCP storage
- **Required:** `license_resolver` must map `prefix` → collection license

## AI / dataset

- Platform MIT code: OK
- Icon assets: follow per-collection license (most OSS sets OK; verify)

## References

- https://iconify.design/docs/api/
- https://iconify.design/docs/licenses.html
