"""Alternate URLs when primary scrape fails (403/404/SPA shell)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .paths import KB_ROOT

FALLBACKS_PATH = KB_ROOT / "scrape_fallbacks.yaml"

# Curated same-content alternates (primary id → ordered URL list)
EXPLICIT_ALTERNATES: dict[str, list[dict[str, str]]] = {
	# ── W3C WCAG (live 403) — wayback also auto-generated ──
	"url_a11y_wcag22_target": [{"url": "https://webaim.org/standards/wcag/checklist", "note": "WebAIM checklist target size"}],
	"url_pilot_wcag_target": [{"url": "https://webaim.org/standards/wcag/checklist", "note": "WebAIM checklist"}],
	# ── NNG moved URLs ──
	"url_nng_login": [
		{"url": "https://www.nngroup.com/articles/checklist-registration-login/", "note": "NNG login/register mobile checklist"},
		{"url": "https://www.nngroup.com/articles/login-walls/", "note": "NNG login walls"},
	],
	"url_nng_autocomplete": [
		{"url": "https://www.nngroup.com/articles/search/", "note": "NNG search UX"},
		{"url": "https://www.nngroup.com/articles/site-search/", "note": "NNG site search"},
	],
	"url_nng_empty": [
		{"url": "https://www.nngroup.com/articles/empty-state-interface/", "note": "NNG empty states"},
	],
	"url_nng_cta": [
		{"url": "https://www.nngroup.com/articles/call-to-action-buttons/", "note": "NNG CTA buttons"},
	],
	"url_nng_onboarding_desktop": [
		{"url": "https://www.nngroup.com/articles/mobile-app-onboarding/", "note": "NNG onboarding"},
		{"url": "https://www.nngroup.com/articles/first-time-experience/", "note": "NNG first-time UX"},
	],
	"url_onb_nng_onboarding": [
		{"url": "https://www.nngroup.com/articles/mobile-app-onboarding/", "note": "NNG mobile onboarding"},
	],
	"url_onb_goal_gradient": [
		{"url": "https://www.nngroup.com/articles/progress-indicators/", "note": "NNG progress / goal gradient adjacent"},
	],
	"url_nng_colorblind": [
		{"url": "https://www.nngroup.com/articles/color-blindness/", "note": "NNG color blindness"},
	],
	"url_ai_nng_ai_ux": [
		{"url": "https://www.nngroup.com/articles/ai-assistant/", "note": "NNG AI assistant UX"},
	],
	"url_ai_nng_genai": [
		{"url": "https://www.nngroup.com/articles/generative-ui/", "note": "NNG generative UI"},
	],
	"url_smashing_inline_validation": [
		{"url": "https://www.smashingmagazine.com/2022/09/inline-validation-web-forms-ux/", "note": "Smashing inline validation (2022)"},
	],
	"url_smashing_typography": [
		{"url": "https://www.smashingmagazine.com/2011/03/technical-web-typography-guidelines-and-techniques/", "note": "Smashing typography guidelines"},
		{"url": "https://developer.mozilla.org/en-US/docs/Learn/CSS/Styling_text/Fundamentals", "note": "MDN typography fundamentals"},
	],
	"url_baymard_search": [
		{"url": "https://baymard.com/blog/ecommerce-search-query-types", "note": "Baymard search query types"},
		{"url": "https://www.nngroup.com/articles/search/", "note": "NNG search fallback"},
	],
	"url_webaim_captcha": [
		{"url": "https://webaim.org/techniques/forms/", "note": "WebAIM forms incl CAPTCHA guidance"},
	],
	"url_govuk_sign_in": [
		{"url": "https://design-system.service.gov.uk/components/button/", "note": "Gov.uk button patterns for sign-in CTAs"},
		{"url": "https://www.nngroup.com/articles/checklist-registration-login/", "note": "NNG login checklist"},
	],
	# ── SPA design systems (need browser) ──
	"url_material_type": [
		{"url": "https://m2.material.io/design/typography/understanding-typography.html", "note": "Material 2 typography"},
		{"url": "https://developer.mozilla.org/en-US/docs/Learn/CSS/Styling_text/Fundamentals", "note": "MDN typography"},
	],
	"url_material_motion": [
		{"url": "https://m2.material.io/design/motion/understanding-motion.html", "note": "Material 2 motion"},
	],
	"url_material_a11y": [
		{"url": "https://m2.material.io/design/usability/accessibility.html", "note": "Material 2 accessibility"},
		{"url": "https://webaim.org/standards/wcag/checklist", "note": "WebAIM WCAG checklist"},
	],
	"url_carbon_motion": [
		{"url": "https://carbondesignsystem.com/guidelines/motion/overview", "note": "Carbon motion (no trailing slash)"},
		{"url": "https://carbondesignsystem.com/components/loading/usage/", "note": "Carbon loading patterns"},
	],
	"url_apple_accessibility": [
		{"url": "https://developer.apple.com/design/human-interface-guidelines/accessibility#Overview", "note": "Apple HIG accessibility overview"},
	],
	"url_ai_apple_hil": [
		{"url": "https://developer.apple.com/design/human-interface-guidelines/generative-ai", "note": "Apple HIG generative AI"},
	],
	"url_ai_google_pair": [
		{"url": "https://pair.withgoogle.com/guidebook/chapters/", "note": "PAIR guidebook chapters"},
	],
	"url_pair_mental_models": [
		{"url": "https://pair.withgoogle.com/guidebook/chapters/mental-models/", "note": "PAIR mental models chapter"},
	],
	"url_cxl_forms_general": [
		{"url": "https://www.nngroup.com/articles/web-form-design/", "note": "NNG web form design"},
		{"url": "https://webaim.org/techniques/forms/", "note": "WebAIM forms"},
	],
	"url_cog_aesthetic_pixelmojo": [
		{"url": "https://www.nngroup.com/articles/aesthetic-usability-effect/", "note": "NNG aesthetic-usability"},
	],
}


def wayback_url(url: str, *, year: str = "2024") -> str:
	"""Internet Archive snapshot wrapper."""
	clean = url.rstrip("/")
	return f"https://web.archive.org/web/{year}/{clean}"


def _host(url: str) -> str:
	return urlparse(url).netloc.lower()


def build_candidate_urls(source_id: str, primary_url: str) -> list[dict[str, str]]:
	"""Ordered scrape attempts: primary → explicit alternates → auto wayback."""
	out: list[dict[str, str]] = [{"url": primary_url, "via": "primary"}]

	for alt in EXPLICIT_ALTERNATES.get(source_id, []):
		out.append({"url": alt["url"], "via": alt.get("note") or "alternate"})

	host = _host(primary_url)
	if "w3.org" in host and "/WAI/" in primary_url:
		wb = wayback_url(primary_url)
		if not any(c["url"] == wb for c in out):
			out.append({"url": wb, "via": "wayback_w3c"})

	if "nngroup.com" in host and source_id not in EXPLICIT_ALTERNATES:
		# Generic NNG 404 recovery: try wayback
		wb = wayback_url(primary_url, year="2023")
		out.append({"url": wb, "via": "wayback_nng"})

	if "baymard.com" in host:
		wb = wayback_url(primary_url, year="2023")
		out.append({"url": wb, "via": "wayback_baymard"})

	# De-dupe preserving order
	seen: set[str] = set()
	deduped: list[dict[str, str]] = []
	for c in out:
		if c["url"] in seen:
			continue
		seen.add(c["url"])
		deduped.append(c)
	return deduped


def write_fallbacks_yaml() -> Path:
	"""Persist explicit alternates for operator review."""
	doc = {
		"version": 1,
		"description": "Alternate URLs when primary scrape fails. Auto wayback applied for w3.org/WAI.",
		"auto_rules": [
			{"match": "w3.org/WAI/", "strategy": "wayback", "year": "2024"},
			{"match": "m3.material.io", "strategy": "browser_headed"},
			{"match": "developer.apple.com", "strategy": "browser_headed"},
		],
		"alternates": EXPLICIT_ALTERNATES,
	}
	KB_ROOT.mkdir(parents=True, exist_ok=True)
	FALLBACKS_PATH.write_text(yaml.dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
	return FALLBACKS_PATH
