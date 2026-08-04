"""Live post-fix smoke for .dev39 hardcore fixes (no full browser suite)."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.component_intelligence.models import ParsedQuery
from navigation.component_intelligence.selection.library_lock import resolve_foundation_library
from navigation.component_intelligence.selection.selector import select_foundation
from navigation.component_intelligence.models import ComponentCandidate
from navigation.execution_runtime.policies.timeout import TimeoutPolicy
from navigation.resolver_intelligence.context import build_resolver_context
from navigation.resolver_intelligence.validators.route_claim import validate_route_claim
from navigation.resolver_intelligence.registry import ResolverRegistry
from navigation.resolver_intelligence.contracts import ResolverKind, ResolverQuery
from navigation.resource_intelligence.models import ResourceCategory
from navigation.resource_intelligence.providers.fontsource.provider import FontsourceProvider
import navigation.resource_intelligence.providers.fontsource.provider as font_mod


def section(title: str) -> None:
	print(f"\n=== {title} ===")


async def main() -> int:
	fails = 0
	portfolio = Path(r"C:\Users\usman\Desktop\artful-portfolio-main\newUi")

	section("1. TimeoutPolicy honors timeout_s")
	p = TimeoutPolicy()
	a90 = p.timeout_for("perception_audit_accessibility", {"timeout_s": 90})
	a180 = p.timeout_for("perception_audit_accessibility", {"timeout_s": 180})
	mode60 = p.timeout_for("perception_audit_mode", {"timeout_s": 60})
	print(f"a11y timeout_s=90 -> wall={a90}")
	print(f"a11y timeout_s=180 -> wall={a180}")
	print(f"mode timeout_s=60 -> wall={mode60}")
	if a180 <= 120:
		print("FAIL: timeout_s=180 still capped at 120")
		fails += 1
	else:
		print("PASS: timeout_s=180 raises executor wall above 120")
	if mode60 <= 120:
		print("FAIL: audit_mode wall not scaled")
		fails += 1
	else:
		print("PASS: audit_mode wall scaled for multi-category")

	section("2. Once-UI foundation detection")
	if portfolio.is_dir():
		res = resolve_foundation_library(
			portfolio, ParsedQuery(raw="select component foundation for about")
		)
		print(f"library={res.library_id} evidence={res.evidence} refused={res.refused}")
		if res.library_id != "@once-ui-system":
			print("FAIL: expected @once-ui-system")
			fails += 1
		else:
			print("PASS: package.json → @once-ui-system")
		sel = await select_foundation(
			[
				ComponentCandidate(
					id="aceternity:hero-navbar",
					provider="shadcn_ecosystem",
					provider_group="registry",
					name="hero-section-with-images-grid-and-navbar",
					title="Hero+Navbar",
					category="block",
					description="x",
					registry="@aceternity",
					item_type="registry:block",
					relevance_score=1.0,
					metadata={"matched_query": "navbar"},
				)
			],
			repo_root=portfolio,
			parsed_query=ParsedQuery(
				raw="select component foundation for portfolio about",
				page_context=["portfolio", "about"],
			),
		)
		print(
			f"select usable={sel.usable} library_id={sel.library_id} "
			f"chosen.cat={sel.chosen.category if sel.chosen else None} "
			f"chosen.reg={sel.chosen.registry if sel.chosen else None}"
		)
		if not sel.usable or sel.library_id != "@once-ui-system":
			print("FAIL: select did not lock @once-ui-system")
			fails += 1
		elif sel.chosen and "aceternity" in (sel.chosen.registry or ""):
			print("FAIL: still chose aceternity block")
			fails += 1
		else:
			print("PASS: select locks @once-ui-system, not aceternity")
	else:
		print(f"SKIP: portfolio not found at {portfolio}")

	section("3. Fontsource geist (live HTTP)")
	font_mod._CACHE = None
	assets, degraded = await FontsourceProvider().search(
		"geist", category=ResourceCategory.FONT, max_results=5
	)
	print(f"assets={len(assets)} degraded={degraded}")
	for a in assets[:3]:
		print(f"  - {a.resource_id} {a.title}")
	if any("400" in d or "fontsource_search_failed" in d for d in degraded):
		print("FAIL: fontsource still failing")
		fails += 1
	elif not assets:
		print("FAIL: no geist fonts returned")
		fails += 1
	else:
		print("PASS: geist search works without HTTP 400")

	section("4. resolve_route vs validate_route_claim (Next App Router)")
	if portfolio.is_dir():
		ctx = build_resolver_context(portfolio)
		resolved = ResolverRegistry().resolve(
			ResolverQuery(kind=ResolverKind.ROUTE, params={"path": "/about"}),
			ctx,
		)
		print(f"resolve_route resolver_id={resolved.resolver_id} status={resolved.status} matches={len(resolved.matches)}")
		claim = validate_route_claim(
			{
				"route": "/about",
				"file": "src/app/about/page.tsx",
				"component": {"name": "About"},
			},
			ctx,
		)
		print(f"validate valid={claim.valid} checks={[ (c.name, c.passed, c.detail) for c in claim.checks ]}")
		rid = str(resolved.resolver_id or "")
		if "react-router" in rid and "next" not in rid.lower():
			print("FAIL: resolve still on react-router for Next app")
			fails += 1
		elif claim.mcp_resolve and "react-router" in str(claim.mcp_resolve.resolver_id or "") and "next" not in str(claim.mcp_resolve.resolver_id or "").lower():
			print("FAIL: validate still hard-coded to react-router")
			fails += 1
		else:
			print("PASS: resolve+validate share Next-capable dispatch")
	else:
		print("SKIP: no portfolio")

	section("5. Consistency project_id default alignment")
	# Pure logic: handler default is 'default' — assert source contains the fix.
	handlers = (ROOT / "src/navigation/mcp/design_intelligence_handlers.py").read_text(encoding="utf-8")
	if "project_id = raw_project or 'default'" in handlers or "raw_project or 'default'" in handlers:
		print("PASS: consistency_audit defaults project_id=default")
	else:
		print("FAIL: consistency_audit project_id default not found")
		fails += 1

	section("SUMMARY")
	print(f"fails={fails}")
	return 1 if fails else 0


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
