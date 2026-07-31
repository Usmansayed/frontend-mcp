"""Live layout region probe for observe capture packs (no full snapshot required)."""
from __future__ import annotations

from typing import Any

_REGION_JS = """(() => {
  const tags = ['header','nav','aside','main','footer','form','section'];
  const out = [];
  const seen = new Set();
  for (const tag of tags) {
    const nodes = Array.from(document.querySelectorAll(tag)).slice(0, tag === 'section' ? 6 : 2);
    for (const el of nodes) {
      const r = el.getBoundingClientRect();
      const absTop = r.top + window.scrollY;
      const absLeft = r.left + window.scrollX;
      if (r.width < 40 || r.height < 40) continue;
      const role = tag;
      const key = role === 'section' ? `${role}:${Math.round(absTop)}` : role;
      if (role !== 'section' && seen.has(role)) continue;
      seen.add(key);
      out.push({
        role,
        label: role,
        rect: {
          x: Math.max(0, Math.floor(absLeft)),
          y: Math.max(0, Math.floor(absTop)),
          w: Math.ceil(r.width),
          h: Math.ceil(r.height),
          width: Math.ceil(r.width),
          height: Math.ceil(r.height),
        },
      });
    }
  }
  return out.slice(0, 12);
})()"""


async def probe_layout_regions(session: Any) -> list[dict[str, Any]]:
	"""Best-effort semantic regions from the live DOM for section crops."""
	try:
		from navigation.visual_browser_intelligence.verify.verification import evaluate_js

		raw = await evaluate_js(session, _REGION_JS)
	except Exception:
		return []
	if not isinstance(raw, list):
		return []
	out: list[dict[str, Any]] = []
	for row in raw:
		if not isinstance(row, dict):
			continue
		rect = row.get("rect")
		if not isinstance(rect, dict):
			continue
		out.append(
			{
				"role": str(row.get("role") or "section"),
				"label": str(row.get("label") or row.get("role") or "section"),
				"rect": rect,
			}
		)
	return out
