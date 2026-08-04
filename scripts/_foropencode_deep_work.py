"""Deep-work upgrade for ForOpenCode corpus — run once from repo root."""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path("ForOpenCode")
TODAY = "2026-07-19"
NORM = ROOT / "06_corpus" / "normalized"
COMP = ROOT / "06_corpus" / "comparisons"
GRAPHS = ROOT / "08_graphs"
GUIDES = ROOT / "07_guides"
RAW_CARBON = ROOT / "06_corpus" / "raw" / "src_ibm_carbon"


def fix_carbon() -> None:
	snap = RAW_CARBON / "snapshot.md"
	data = snap.read_bytes()
	digest = hashlib.sha256(data).hexdigest()
	manifest = f"""source_id: src_ibm_carbon
acquired_at: {TODAY}
acquired_by: cursor_agent
url: https://www.carbondesignsystem.com/guidelines/accessibility/overview/
access: public
license_notes: "IBM Carbon docs — Apache-2.0 components; documentation fair-use snapshot for research corpus"
artifacts:
  - path: snapshot.md
    content_type: text/markdown
    checksum_sha256: "{digest}"
    bytes: {len(data)}
pointers:
  - kind: canonical_url
    value: https://www.carbondesignsystem.com/guidelines/accessibility/overview/
  - kind: hub
    value: https://carbondesignsystem.com/
notes: "Accessibility overview snapshot. Manifest repaired after empty-checksum stub."
"""
	(RAW_CARBON / "manifest.yaml").write_text(manifest, encoding="utf-8")
	print("fixed carbon", digest[:16], len(data))


def card(**kw: object) -> dict:
	required = [
		"id",
		"name",
		"category",
		"subcategory",
		"definition",
		"engineering_meaning",
		"why_humans_behave_this_way",
		"how_to_detect_violations",
		"when_to_apply",
		"when_not_to_apply",
		"tradeoffs",
		"common_mistakes",
		"examples",
		"evidence_class",
		"confidence",
		"supporting_source_ids",
		"extract_ids",
		"consensus_status",
		"version",
		"last_reviewed",
	]
	for key in required:
		if key not in kw:
			raise KeyError(key)
	out = dict(kw)
	out.setdefault("references", [])
	out.setdefault("source_urls", [])
	out.setdefault("conflict_notes", "")
	out.setdefault("conflict_claim_ids", [])
	out.setdefault(
		"revision_notes",
		"Deep-work pass by Cursor agent: filled operational fields from extracts.",
	)
	return out  # type: ignore[return-value]


def build_cards() -> list[dict]:
	cards: list[dict] = []
	cards.append(
		card(
			id="UX_A11Y_TARG_004",
			name="WCAG 2.2 Target Size (Minimum)",
			category="Compliance and Limits",
			subcategory="Accessibility Motor",
			definition=(
				"Pointer targets must be at least 24×24 CSS pixels, or satisfy the spacing "
				"exception with a 24 CSS-pixel diameter circle that does not intersect other targets."
			),
			engineering_meaning=(
				"Interactive hit areas must meet ≥24×24 CSS px, or ensure undersized targets have "
				"enough clearance that 24px-diameter circles centered on their boxes do not intersect "
				"other targets."
			),
			why_humans_behave_this_way=(
				"Users with motor impairments, tremors, or imprecise pointing miss small, densely "
				"packed targets and activate neighbors by accident."
			),
			how_to_detect_violations=(
				"Measure CSS bounding boxes. If width or height < 24px, test whether a 24px-diameter "
				"circle centered on the box intersects any other target."
			),
			when_to_apply="All pointer-activated controls (mouse, touch, pen), including icon-only buttons.",
			when_not_to_apply=(
				"Inline text links constrained by line-height; unmodified user-agent controls; "
				"equivalent larger control available; essential/legal presentation exceptions per WCAG."
			),
			tradeoffs="Larger targets reduce density; spacing exception can cost more whitespace than upsizing.",
			common_mistakes="Sizing the visible icon but not the hit area; adjacent 20×20 icons with no gap.",
			examples=[
				"24×24 CSS px button always passes size criterion",
				"20×20 icon with ≥4px isolating gap may pass via spacing exception",
				"Row of 20×20 icons with 0 gap fails circle-intersection test",
			],
			evidence_class="standard",
			confidence=1.0,
			supporting_source_ids=["src_w3c_wcag22_target_size"],
			extract_ids=[
				"src_w3c_wcag22_target_size.json#c01",
				"src_w3c_wcag22_target_size.json#c02",
			],
			consensus_status="single_source",
			version=2,
			last_reviewed=TODAY,
			references=["WCAG 2.2 SC 2.5.8"],
			source_urls=["https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum"],
			conflict_notes=(
				"COMPLEMENTS Fitts (UX_HCI_FITTS_001). CONFLICTS with Hick when enlarging many peers "
				"forces scrolling or fewer visible choices."
			),
			conflict_claim_ids=["UX_COG_HICK_002"],
		)
	)
	cards.append(
		card(
			id="UX_A11Y_CONT_005",
			name="WCAG Contrast (Minimum)",
			category="Compliance and Limits",
			subcategory="Accessibility Visual",
			definition=(
				"Text and images of text must maintain at least 4.5:1 contrast against the background; "
				"large text at least 3:1."
			),
			engineering_meaning=(
				"Compute relative luminance of foreground/background pairs. Fail if normal text < 4.5:1 "
				"or large text (≈18pt+/14pt bold) < 3:1. Prefer semantic tokens that encode compliant pairs."
			),
			why_humans_behave_this_way=(
				"Low vision and age-related contrast sensitivity loss make low-contrast text unreadably "
				"fatiguing or invisible."
			),
			how_to_detect_violations=(
				"Automated contrast checkers (axe, WAVE, WebAIM) plus sampling computed styles on text "
				"over images/gradients."
			),
			when_to_apply="All meaningful text and images of text, including form labels and error copy.",
			when_not_to_apply="Decorative text, inactive/disabled components, incidental logotypes as allowed by WCAG.",
			tradeoffs="Strict contrast can constrain brand palettes; never sacrifice Absolute AA for aesthetics.",
			common_mistakes="Checking brand hex on white but shipping text on photography; color-only error states.",
			examples=["#595959 on #FFFFFF ≈ 7:1 passes", "Light gray placeholder-as-label often fails 4.5:1"],
			evidence_class="standard",
			confidence=1.0,
			supporting_source_ids=["src_webaim_wcag_checklist", "src_ibm_carbon"],
			extract_ids=["src_webaim_wcag_checklist.json#c01", "src_ibm_carbon.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			references=["WCAG SC 1.4.3", "IBM Carbon a11y overview"],
			source_urls=[
				"https://webaim.org/standards/wcag/checklist",
				"https://www.carbondesignsystem.com/guidelines/accessibility/overview/",
			],
		)
	)
	cards.append(
		card(
			id="UX_A11Y_FOCUS_011",
			name="Focus Not Obscured (Minimum)",
			category="Compliance and Limits",
			subcategory="Accessibility Visual",
			definition="When a component receives keyboard focus, it must not be entirely hidden by author-created content.",
			engineering_meaning=(
				"Sticky headers/footers, cookie bars, and overlays must not fully cover the focused control. "
				"Use scroll-margin / focus management so focused nodes stay at least partially visible."
			),
			why_humans_behave_this_way=(
				"Keyboard and AT users navigate by focus; a fully hidden focus target breaks orientation."
			),
			how_to_detect_violations="Tab through the page with sticky chrome present; fail if focused element is completely covered.",
			when_to_apply="All interactive components, especially with sticky UI chrome.",
			when_not_to_apply="User-opened content (e.g., modal) dismissible without advancing focus, per WCAG nuance.",
			tradeoffs="May require larger scroll padding or thinner sticky bars.",
			common_mistakes="Sticky header covering focused links; focus trapped under cookie banners.",
			examples=["scroll-margin-top on inputs under sticky nav"],
			evidence_class="standard",
			confidence=1.0,
			supporting_source_ids=["src_w3c_wcag22_overview"],
			extract_ids=["src_w3c_wcag22_overview.json#c01"],
			consensus_status="single_source",
			version=1,
			last_reviewed=TODAY,
			source_urls=["https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/"],
		)
	)
	cards.append(
		card(
			id="UX_HCI_FITTS_001",
			name="Fitts's Law (Shannon Formulation)",
			category="Interaction Dynamics",
			subcategory="Motor Ergonomics",
			definition=(
				"Movement time to a target increases with Index of Difficulty ID = log2(A/W + 1), "
				"where A is amplitude (distance) and W is target width; MT = a + b·ID."
			),
			engineering_meaning=(
				"Reduce pointing latency by increasing effective target width and decreasing travel "
				"distance for frequent actions. Treat screen edges as larger effective targets."
			),
			why_humans_behave_this_way=(
				"Motor control uses a fast ballistic phase then a slower corrective phase; "
				"smaller/farther targets demand more corrective time."
			),
			how_to_detect_violations=(
				"Estimate A from resting cursor/thumb zones and W of primary CTAs; flag frequent "
				"actions with high ID or targets below WCAG floor."
			),
			when_to_apply="CTA placement, toolbars, menus, drag targets on pointer UIs.",
			when_not_to_apply="Pure keyboard flows; voice; intentionally high-friction destructive controls.",
			tradeoffs="Larger/closer targets consume space and can increase accidental activation; conflicts with many simultaneous options (Hick).",
			common_mistakes="Ignoring hit padding; clustering tiny icons; non-Shannon Fitts formulations.",
			examples=["Full-width mobile primary button", "Dock/edge targets with infinite boundary"],
			evidence_class="law",
			confidence=0.95,
			supporting_source_ids=["src_fitts_law_yorku", "src_w3c_wcag22_target_size"],
			extract_ids=["src_fitts_law_yorku.json#c01", "src_w3c_wcag22_target_size.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			conflict_notes="COMPLEMENTS UX_A11Y_TARG_004. CONFLICTS_WITH UX_COG_HICK_002 on dense mobile viewports.",
			conflict_claim_ids=["UX_COG_HICK_002"],
			source_urls=["https://www.yorku.ca/mack/hhci2018.html"],
		)
	)
	cards.append(
		card(
			id="UX_COG_HICK_002",
			name="Hick-Hyman Law",
			category="Human Behavior",
			subcategory="Cognitive Load",
			definition=(
				"Decision/reaction time increases roughly with the information entropy of the choice set "
				"(classically RT ≈ a + b·log2(n) for n equiprobable options)."
			),
			engineering_meaning=(
				"Reduce simultaneous actionable choices; chunk into hierarchies/search; highlight a "
				"primary action so effective n is small for novices."
			),
			why_humans_behave_this_way=(
				"Working memory and response selection cost grow as alternatives increase."
			),
			how_to_detect_violations=(
				"Count peer primary actions in a decision region; many equally weighted CTAs/menu items "
				"without grouping (often ≫7 visible peers) → overload risk."
			),
			when_to_apply="Nav menus, pricing tiers, settings panels, checkout decisions, onboarding choices.",
			when_not_to_apply="Expert analytic dashboards needing simultaneous density; highly learned expert UIs.",
			tradeoffs="Fewer choices per screen may add steps (interaction cost vs cognitive cost).",
			common_mistakes="Mega-menus of undifferentiated links; equal-weight button rows.",
			examples=["Progressive disclosure of advanced settings", "One primary CTA + secondary text link"],
			evidence_class="law",
			confidence=0.95,
			supporting_source_ids=["src_hick_law_pmc", "src_iso_9241_110"],
			extract_ids=["src_hick_law_pmc.json#c01", "src_iso_9241_110.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			conflict_notes="CONFLICTS_WITH UX_HCI_FITTS_001 when making each option large enough reduces how many fit on screen.",
			conflict_claim_ids=["UX_HCI_FITTS_001"],
			source_urls=["https://pmc.ncbi.nlm.nih.gov/articles/PMC5998988/"],
		)
	)
	cards.append(
		card(
			id="UX_COG_FOGG_013",
			name="Fogg Behavior Model (B=MAP)",
			category="Human Behavior",
			subcategory="Motivation and Action",
			definition="A target behavior occurs when Motivation, Ability, and a Prompt converge at the same moment (B=MAP).",
			engineering_meaning=(
				"Diagnose failed CTAs/onboarding by testing Prompt visibility/timing, Ability (friction), "
				"and Motivation (value clarity). Prefer raising Ability before spamming prompts."
			),
			why_humans_behave_this_way=(
				"Without sufficient motivation, ability, or a timely cue, the activation threshold is not crossed."
			),
			how_to_detect_violations=(
				"High exposure + low conversion: check if prompt is hidden, task is hard, or value is unclear."
			),
			when_to_apply="Conversion CTAs, onboarding, notifications, habit loops.",
			when_not_to_apply="Passive reading surfaces; automated backend processes; manipulative dark patterns.",
			tradeoffs="Motivation hacks erode trust; Ability work costs engineering; Prompts can become noise.",
			common_mistakes="Adding more banners when friction is the Ability problem.",
			examples=["1-click purchase raises Ability at peak Motivation"],
			evidence_class="heuristic",
			confidence=0.85,
			supporting_source_ids=["src_fogg_behaviormodel", "src_baymard_checkout"],
			extract_ids=["src_fogg_behaviormodel.json#c01", "src_baymard_checkout.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			source_urls=["https://www.behaviormodel.org/"],
		)
	)
	cards.append(
		card(
			id="UX_ARC_ISO_001",
			name="ISO 9241-110 Suitability for the Task",
			category="Interaction Dynamics",
			subcategory="Structural Architecture",
			definition="The dialog supports user goals without unnecessary effort or irrelevant complexity.",
			engineering_meaning=(
				"Show only controls/info needed for the current task; minimize steps for common paths; "
				"hide advanced options until needed."
			),
			why_humans_behave_this_way="Irrelevant options inflate Hick cost and dilute attention from the goal.",
			how_to_detect_violations=(
				"For a screen, mark elements not supporting the primary task; if a large share is irrelevant, fail."
			),
			when_to_apply="Task-focused flows: forms, checkout, setup wizards.",
			when_not_to_apply="Command centers / multi-goal dashboards where breadth is the task.",
			tradeoffs="Can reduce discoverability of secondary features.",
			common_mistakes="Crowding checkout with marketing modules; burying primary action.",
			examples=["Checkout shows shipping/payment/contact only"],
			evidence_class="standard",
			confidence=0.95,
			supporting_source_ids=["src_iso_9241_110", "src_hick_law_pmc"],
			extract_ids=["src_iso_9241_110.json#c01", "src_hick_law_pmc.json#c01"],
			consensus_status="consensus",
			version=1,
			last_reviewed=TODAY,
		)
	)
	cards.append(
		card(
			id="UX_INX_SELF_001",
			name="ISO 9241-110 Self-Descriptiveness",
			category="Interaction Dynamics",
			subcategory="Feedback Systems",
			definition="The dialog is self-explanatory: status and options are clearly described without external docs.",
			engineering_meaning=(
				"Visible labels, explained states, and actionable errors. Prefer persistent labels over "
				"placeholder-only fields; icon-only controls need accessible names."
			),
			why_humans_behave_this_way="Users build mental models from visible cues; unexplained states force trial-and-error.",
			how_to_detect_violations="Audit controls for missing accessible names; placeholder-only fields; opaque errors.",
			when_to_apply="Forms, navigation, status chrome, errors.",
			when_not_to_apply="Universally conventional icons may use short names if the accessibility tree is complete.",
			tradeoffs="More labels increase density.",
			common_mistakes="Icon-only unlabeled buttons; errors that only change color.",
			examples=["Error: 'Email needs an @' instead of 'Invalid'"],
			evidence_class="standard",
			confidence=0.95,
			supporting_source_ids=["src_iso_9241_110"],
			extract_ids=["src_iso_9241_110.json#c02"],
			consensus_status="single_source",
			version=1,
			last_reviewed=TODAY,
		)
	)
	cards.append(
		card(
			id="UX_INX_CTRL_001",
			name="ISO 9241-110 Controllability",
			category="Interaction Dynamics",
			subcategory="Feedback Systems",
			definition="Users can initiate, pace, and reverse dialog actions; they retain control.",
			engineering_meaning="Provide cancel/undo/back that preserves work; avoid forced auto-submit; confirm destructive actions.",
			why_humans_behave_this_way="Fear of irreversible mistakes causes hesitation; undo enables safe exploration.",
			how_to_detect_violations="Find irreversible deletes without confirm; modals without dismiss; auto-advancing steps.",
			when_to_apply="Destructive actions, multi-step flows, settings changes.",
			when_not_to_apply="Security operations where undo would break integrity (document the exception).",
			tradeoffs="Confirmations add friction; undo needs state management.",
			common_mistakes="Delete without undo/confirm; checkout that loses data on Back.",
			examples=["Undo toast after archive", "Confirm before permanent delete"],
			evidence_class="standard",
			confidence=0.95,
			supporting_source_ids=["src_iso_9241_110"],
			extract_ids=["src_iso_9241_110.json#c03"],
			consensus_status="single_source",
			version=1,
			last_reviewed=TODAY,
		)
	)
	cards.append(
		card(
			id="UX_INX_ERR_009",
			name="Error Prevention and Fault Tolerance",
			category="Interaction Dynamics",
			subcategory="Feedback Systems",
			definition="Errors should be prevented or easily corrected without serious consequences; preserve user input.",
			engineering_meaning=(
				"Prefer constraints/masks and field-level validation after completion. Never wipe the form "
				"on failure. Messages must be specific and programmatically associated."
			),
			why_humans_behave_this_way=(
				"Mode-switching between filling and post-submit repair is costly; local feedback restores the path."
			),
			how_to_detect_violations="Submit-only validation with page reload; cleared fields; color-only errors.",
			when_to_apply="Account, checkout, payment, and high-stakes forms.",
			when_not_to_apply="Validate-on-each-keystroke before the user finishes typing.",
			tradeoffs="Richer client validation increases complexity.",
			common_mistakes="Clear-on-error; 'Invalid input'; color-only indicators.",
			examples=["Luhn check before submit", "Preserve values after server 400"],
			evidence_class="standard",
			confidence=0.95,
			supporting_source_ids=["src_iso_9241_110", "src_baymard_form_design"],
			extract_ids=["src_iso_9241_110.json#c04", "src_baymard_form_design.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			conflict_notes="MITIGATES high interaction cost of full-page resubmit cycles.",
		)
	)
	cards.append(
		card(
			id="UX_ARC_FORM_010",
			name="Single-Column Form Layout",
			category="Product Surfaces",
			subcategory="Forms",
			definition="Present sequential form fields in a single primary vertical column rather than multi-column grids.",
			engineering_meaning=(
				"Use one vertical stack for fields. Allow narrow exceptions only for tightly coupled "
				"micro-fields (e.g., city/state/ZIP)."
			),
			why_humans_behave_this_way="Multi-column forms break linear reading gravity and increase order ambiguity.",
			how_to_detect_violations=(
				"Layout audit: consecutive unrelated inputs share similar vertical positions outside allowed micro-groups."
			),
			when_to_apply="Checkout, signup, lead forms, most consumer forms.",
			when_not_to_apply="Expert dense enterprise forms with trained users; tightly coupled date/name parts.",
			tradeoffs="Increases vertical length; submit may fall below fold.",
			common_mistakes="Mimicking paper forms with two-column name/address blocks.",
			examples=["Full-width address line; city/state/ZIP as one allowed row"],
			evidence_class="empirical",
			confidence=0.95,
			supporting_source_ids=["src_baymard_form_design", "src_iso_9241_110"],
			extract_ids=["src_baymard_form_design.json#c01", "src_iso_9241_110.json#c01"],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
			conflict_notes="Manage Gestalt proximity with tighter intra-group spacing if vertical gaps grow.",
		)
	)
	cards.append(
		card(
			id="UX_PRD_GUEST_001",
			name="Guest Checkout Prominence",
			category="Product Surfaces",
			subcategory="Conversion",
			definition="Guest checkout must be a primary, highly visible path; do not force account creation to purchase.",
			engineering_meaning=(
				"On account gate step, present Guest Checkout as equal/greater visual weight than Sign in / Create account."
			),
			why_humans_behave_this_way="Forced registration is major abandonment friction and reduces trust.",
			how_to_detect_violations="Checkout entry audit: guest path missing, below fold, or weaker than login.",
			when_to_apply="Consumer ecommerce checkout entry.",
			when_not_to_apply="B2B portals requiring authenticated purchasing by policy.",
			tradeoffs="May reduce account graph for personalization; offer soft post-purchase account creation.",
			common_mistakes="Guest as tiny link under login wall.",
			examples=['Primary "Continue as guest" button above or beside login'],
			evidence_class="empirical",
			confidence=0.95,
			supporting_source_ids=["src_baymard_checkout", "src_fogg_behaviormodel"],
			extract_ids=["src_baymard_checkout.json#c01", "src_fogg_behaviormodel.json#c01"],
			consensus_status="consensus",
			version=1,
			last_reviewed=TODAY,
		)
	)
	cards.append(
		card(
			id="UX_DS_TOKEN_001",
			name="Semantic Color Tokens Bound to Roles",
			category="Design Systems and Tokens",
			subcategory="Semantic Tokens",
			definition="Colors should be expressed as semantic roles rather than raw palette literals in product UI.",
			engineering_meaning=(
				"Components consume tokens (e.g., color-critical) mapped to theme values that already "
				"satisfy contrast. Avoid hard-coded hex in feature CSS."
			),
			why_humans_behave_this_way="Consistent role→meaning mapping reduces interpretation cost; tokens make a11y fixes systemic.",
			how_to_detect_violations="Search UI code for raw hex/rgb in components that should use tokens.",
			when_to_apply="Product UI, design systems, theming, status/feedback colors.",
			when_not_to_apply="One-off marketing illustrations outside the system (still check contrast if text).",
			tradeoffs="Requires token governance; migration cost from legacy hex.",
			common_mistakes="Using brand green for both success and primary CTA with different meanings.",
			examples=["Polaris-style critical/success tokens", "Carbon themes complying with WCAG AA contrast"],
			evidence_class="heuristic",
			confidence=0.85,
			supporting_source_ids=["src_shopify_polaris", "src_ibm_carbon", "src_webaim_wcag_checklist"],
			extract_ids=[
				"src_shopify_polaris.json#c01",
				"src_ibm_carbon.json#c01",
				"src_webaim_wcag_checklist.json#c01",
			],
			consensus_status="consensus",
			version=2,
			last_reviewed=TODAY,
		)
	)
	return cards


def write_cards(cards: list[dict]) -> None:
	obsolete = [
		"UX_HCI_POINT_001.json",
		"UX_COG_EFFORT_002.json",
		"UX_A11Y_BASE_001.json",
		"UX_PRD_FORM_001.json",
		"UX_DS_ENTERPRISE_001.json",
	]
	for name in obsolete:
		path = NORM / name
		if path.exists():
			path.unlink()
			print("removed", name)
	for item in cards:
		path = NORM / f"{item['id']}.json"
		path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	print("wrote", len(cards), "claim cards")


def write_comparisons() -> None:
	data = {
		"cl_pointing_efficiency.json": {
			"cluster_id": "cl_pointing_efficiency",
			"taxonomy_path": ["Interaction Dynamics", "Motor Ergonomics"],
			"compared_at": TODAY,
			"extract_ids": ["src_w3c_wcag22_target_size.json", "src_fitts_law_yorku.json"],
			"consensus": [
				{
					"summary": "Larger targets improve Absolute accessibility (WCAG) and pointing performance (Fitts).",
					"supporting_local_claim_refs": [
						"src_w3c_wcag22_target_size.json#c01",
						"src_fitts_law_yorku.json#c01",
					],
					"proposed_claim_id": "UX_HCI_FITTS_001",
				}
			],
			"conflicts": [
				{
					"summary": "Enlarging many peer targets reduces how many options fit without scrolling, raising Hick cost.",
					"side_a_refs": [
						"src_fitts_law_yorku.json#c01",
						"src_w3c_wcag22_target_size.json#c01",
					],
					"side_b_refs": ["src_hick_law_pmc.json#c01"],
					"decision_hint": "Few primary actions large; secondary behind disclosure. Never drop below WCAG floor.",
				}
			],
			"duplicates": [],
			"notes": "Deep-work revision: COMPLEMENTS WCAG↔Fitts; cross-link Hick conflict.",
		},
		"cl_hick_vs_fitts.json": {
			"cluster_id": "cl_hick_vs_fitts",
			"taxonomy_path": ["Human Behavior", "Cognitive Load"],
			"compared_at": TODAY,
			"extract_ids": [
				"src_hick_law_pmc.json",
				"src_fitts_law_yorku.json",
				"src_iso_9241_110.json",
			],
			"consensus": [
				{
					"summary": "Fewer clearer primary actions (Hick + ISO) that are easy to hit (Fitts).",
					"supporting_local_claim_refs": [
						"src_hick_law_pmc.json#c01",
						"src_iso_9241_110.json#c01",
						"src_fitts_law_yorku.json#c01",
					],
					"proposed_claim_id": "UX_ARC_ISO_001",
				}
			],
			"conflicts": [
				{
					"summary": "Hick favors fewer choices; Fitts favors larger targets — space competition on small viewports.",
					"side_a_refs": ["src_hick_law_pmc.json#c01"],
					"side_b_refs": ["src_fitts_law_yorku.json#c01"],
					"decision_hint": "Priority: WCAG mins → one primary CTA → chunk remaining choices.",
				}
			],
			"duplicates": [],
			"notes": "New conflict cluster from deep-work mandate.",
		},
		"cl_forms_checkout.json": {
			"cluster_id": "cl_forms_checkout",
			"taxonomy_path": ["Product Surfaces", "Forms"],
			"compared_at": TODAY,
			"extract_ids": [
				"src_baymard_checkout.json",
				"src_baymard_form_design.json",
				"src_iso_9241_110.json",
				"src_fogg_behaviormodel.json",
			],
			"consensus": [
				{
					"summary": "Single-column layouts reduce form ambiguity (Baymard) and support ISO task suitability.",
					"supporting_local_claim_refs": [
						"src_baymard_form_design.json#c01",
						"src_iso_9241_110.json#c01",
					],
					"proposed_claim_id": "UX_ARC_FORM_010",
				},
				{
					"summary": "Guest checkout prominence reduces forced-registration friction and raises Fogg Ability.",
					"supporting_local_claim_refs": [
						"src_baymard_checkout.json#c01",
						"src_fogg_behaviormodel.json#c01",
					],
					"proposed_claim_id": "UX_PRD_GUEST_001",
				},
				{
					"summary": "Fault-tolerant validation is required alongside layout empirics.",
					"supporting_local_claim_refs": ["src_iso_9241_110.json#c04"],
					"proposed_claim_id": "UX_INX_ERR_009",
				},
			],
			"conflicts": [],
			"duplicates": [
				{
					"survivor_ref": "UX_ARC_FORM_010",
					"merged_refs": ["UX_PRD_FORM_001"],
					"fingerprint": "split_form_mega_card",
				}
			],
			"notes": "Split former mega-claim UX_PRD_FORM_001 into FORM_010, GUEST_001, ERR_009.",
		},
		"cl_accessibility.json": {
			"cluster_id": "cl_accessibility",
			"taxonomy_path": ["Compliance and Limits"],
			"compared_at": TODAY,
			"extract_ids": [
				"src_w3c_wcag22_target_size.json",
				"src_w3c_wcag22_overview.json",
				"src_webaim_wcag_checklist.json",
				"src_ibm_carbon.json",
			],
			"consensus": [
				{
					"summary": "Absolute baseline: contrast, target size/spacing, focus not obscured; DS themes encode these.",
					"supporting_local_claim_refs": [
						"src_webaim_wcag_checklist.json#c01",
						"src_w3c_wcag22_target_size.json#c01",
						"src_w3c_wcag22_overview.json#c01",
						"src_ibm_carbon.json#c01",
					],
					"proposed_claim_id": "UX_A11Y_CONT_005",
				}
			],
			"conflicts": [],
			"duplicates": [
				{
					"survivor_ref": "UX_A11Y_CONT_005",
					"merged_refs": ["UX_A11Y_BASE_001"],
					"fingerprint": "split_a11y_mega_card",
				}
			],
			"notes": "Replaced vague UX_A11Y_BASE_001 with discrete Absolute cards. Empty conflicts justified: standards align.",
		},
		"cl_cognition_behavior.json": {
			"cluster_id": "cl_cognition_behavior",
			"taxonomy_path": ["Human Behavior"],
			"compared_at": TODAY,
			"extract_ids": [
				"src_hick_law_pmc.json",
				"src_fogg_behaviormodel.json",
				"src_iso_9241_110.json",
			],
			"consensus": [
				{
					"summary": "Reduce choice entropy and keep dialogs task-appropriate to raise Ability before prompting.",
					"supporting_local_claim_refs": [
						"src_hick_law_pmc.json#c01",
						"src_fogg_behaviormodel.json#c01",
						"src_iso_9241_110.json#c01",
					],
					"proposed_claim_id": "UX_COG_FOGG_013",
				}
			],
			"conflicts": [
				{
					"summary": "Adding more prompts when Ability is low increases noise without conversion.",
					"side_a_refs": ["src_fogg_behaviormodel.json#c01"],
					"side_b_refs": ["src_iso_9241_110.json#c01"],
					"decision_hint": "Fix Ability/friction first; then prompt.",
				}
			],
			"duplicates": [
				{
					"survivor_ref": "UX_COG_HICK_002",
					"merged_refs": ["UX_COG_EFFORT_002"],
					"fingerprint": "split_mega_cognition_card",
				}
			],
			"notes": "Retired UX_COG_EFFORT_002; Hick and Fogg kept separate.",
		},
		"cl_design_systems.json": {
			"cluster_id": "cl_design_systems",
			"taxonomy_path": ["Design Systems and Tokens"],
			"compared_at": TODAY,
			"extract_ids": [
				"src_shopify_polaris.json",
				"src_ibm_carbon.json",
				"src_webaim_wcag_checklist.json",
			],
			"consensus": [
				{
					"summary": "Semantic tokens + a11y-compliant themes beat ad-hoc hex.",
					"supporting_local_claim_refs": [
						"src_shopify_polaris.json#c01",
						"src_ibm_carbon.json#c01",
						"src_webaim_wcag_checklist.json#c01",
					],
					"proposed_claim_id": "UX_DS_TOKEN_001",
				}
			],
			"conflicts": [],
			"duplicates": [],
			"notes": "Heuristic consensus across DS + Absolute contrast checklist.",
		},
	}
	for name, obj in data.items():
		(COMP / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	print("wrote", len(data), "comparisons")


def write_graph(cards: list[dict]) -> None:
	nodes: list[dict] = []
	edges: list[dict] = []
	for item in cards:
		nodes.append(
			{
				"id": item["id"],
				"type": "claim",
				"label": item["name"],
				"ref": f"06_corpus/normalized/{item['id']}.json",
				"metadata": {
					"evidence_class": item["evidence_class"],
					"confidence": item["confidence"],
				},
			}
		)

	def add_edge(eid: str, src: str, tgt: str, rel: str, ctx: str, conf: float = 0.9) -> None:
		edges.append(
			{
				"id": eid,
				"source": src,
				"target": tgt,
				"relation": rel,
				"context": ctx,
				"confidence": conf,
			}
		)

	add_edge("e_fitts_targ", "UX_HCI_FITTS_001", "UX_A11Y_TARG_004", "COMPLEMENTS", "Optimize above Absolute floor")
	add_edge("e_hick_fitts", "UX_COG_HICK_002", "UX_HCI_FITTS_001", "CONFLICTS_WITH", "Choice count vs target size")
	add_edge("e_hick_iso", "UX_COG_HICK_002", "UX_ARC_ISO_001", "COMPLEMENTS", "Fewer irrelevant options")
	add_edge("e_err_ctrl", "UX_INX_ERR_009", "UX_INX_CTRL_001", "COMPLEMENTS", "Fault tolerance + undo")
	add_edge("e_form_iso", "UX_ARC_FORM_010", "UX_ARC_ISO_001", "COMPLEMENTS", "Single column supports task focus")
	add_edge("e_guest_fogg", "UX_PRD_GUEST_001", "UX_COG_FOGG_013", "COMPLEMENTS", "Guest path raises Ability")
	add_edge("e_token_contrast", "UX_DS_TOKEN_001", "UX_A11Y_CONT_005", "SPECIALIZES", "Tokens encode contrast-safe roles")
	add_edge("e_focus_cont", "UX_A11Y_FOCUS_011", "UX_A11Y_CONT_005", "COMPLEMENTS", "Operable + perceivable baseline")

	for item in cards:
		for sid in item["supporting_source_ids"][:2]:
			edges.append(
				{
					"id": f"cite_{item['id']}_{sid}",
					"source": item["id"],
					"target": sid,
					"relation": "CITES",
					"context": "supporting source",
					"confidence": 1.0,
				}
			)
			nodes.append(
				{
					"id": sid,
					"type": "source",
					"label": sid,
					"ref": f"05_resources/RESOURCE_INDEX.yaml#{sid}",
					"metadata": {},
				}
			)

	seen: set[str] = set()
	uniq: list[dict] = []
	for node in nodes:
		if node["id"] in seen:
			continue
		seen.add(node["id"])
		uniq.append(node)

	guide_id = "guide_form_opt"
	uniq.append(
		{
			"id": guide_id,
			"type": "guide",
			"label": "Form & Checkout Engineering Playbook",
			"ref": "07_guides/guide_form_opt.md",
			"metadata": {"status": "accepted"},
		}
	)
	for cid in [
		"UX_ARC_FORM_010",
		"UX_PRD_GUEST_001",
		"UX_INX_ERR_009",
		"UX_COG_FOGG_013",
		"UX_ARC_ISO_001",
	]:
		edges.append(
			{
				"id": f"composed_{cid}",
				"source": cid,
				"target": guide_id,
				"relation": "COMPOSED_IN",
				"context": "form/checkout playbook",
				"confidence": 0.95,
			}
		)

	(GRAPHS / "nodes.json").write_text(json.dumps(uniq, indent=2) + "\n", encoding="utf-8")
	(GRAPHS / "edges.json").write_text(json.dumps(edges, indent=2) + "\n", encoding="utf-8")
	for stub in ("node_form_guide.json", "edge_guide_claim.json"):
		path = GRAPHS / stub
		if path.exists():
			path.unlink()
	print("graph", len(uniq), "nodes", len(edges), "edges")


def write_guide() -> None:
	md = """---
guide_id: guide_form_opt
title: "Form & Checkout Engineering Playbook"
slug: "form-checkout"
claim_ids:
  - UX_ARC_FORM_010
  - UX_PRD_GUEST_001
  - UX_INX_ERR_009
  - UX_INX_SELF_001
  - UX_COG_FOGG_013
  - UX_ARC_ISO_001
  - UX_A11Y_CONT_005
status: accepted
created_at: 2026-07-19
checklist_passed: true
---

# Form & Checkout Engineering Playbook

## Core philosophy

Forms convert when they minimize cognitive and motor friction while remaining Absolute-accessible. Absorb complexity in the system (ISO task suitability + Fogg Ability); never invent fields or account walls that do not serve the purchase goal. Cite: `UX_ARC_ISO_001`, `UX_COG_FOGG_013`.

## Rules

1. Use a **single primary column** for sequential fields (`UX_ARC_FORM_010`).
2. Make **Guest checkout** a primary path — equal or greater weight than sign-in (`UX_PRD_GUEST_001`).
3. Prefer **prevention + local repair**: validate after field completion, preserve input, specific errors (`UX_INX_ERR_009`).
4. Every control needs a **visible/accessible name**; no placeholder-only labels (`UX_INX_SELF_001`).
5. Keep simultaneous choices small on decision steps; one primary CTA (`UX_ARC_ISO_001` / Hick).
6. Text contrast ≥ **4.5:1** (large text 3:1) including errors (`UX_A11Y_CONT_005`).
7. Diagnose failed CTAs with **B=MAP** before adding more prompts (`UX_COG_FOGG_013`).

## Patterns

- Vertical field stack with tight label→input proximity; larger gaps between groups.
- Guest Continue as guest button above or beside account options.
- Inline validation on blur; associate `aria-describedby` error text.
- Soft post-purchase create-account instead of a login wall.

## Anti-patterns

- Multi-column name/address grids for consumer checkout.
- Forced account creation before pay.
- Clearing the form on server validation failure.
- Color-only error states.
- Equal-weight rows of competing CTAs on the account gate.

## Decision framework

1. Is the field required for this transaction? If no → remove/hide (`UX_ARC_ISO_001`).
2. Is Ability low (too many fields/steps)? Fix Ability before adding Prompts (`UX_COG_FOGG_013`).
3. Layout vs density: default single column; allow micro-groups only for coupled fields (`UX_ARC_FORM_010`).
4. If Hick and Fitts compete on mobile: keep one large primary CTA; disclose secondary options (`UX_COG_HICK_002` / `UX_HCI_FITTS_001`).
5. Absolute a11y never yields to brand preference (`UX_A11Y_CONT_005`, `UX_A11Y_TARG_004`).

## Exceptions

- City / State / ZIP (or equivalent) may share one row.
- B2B portals may require authentication by policy (`UX_PRD_GUEST_001` when_not).
- Expert enterprise data-entry density may justify multi-column — document training assumption.

## Real-world examples

- Guest-first checkout entry with account creation after purchase.
- Address autofill from postal code (system absorbs complexity).
- Payment field masks preventing alpha input.

## References

- `src_baymard_form_design` — single-column empirics
- `src_baymard_checkout` — guest checkout
- `src_iso_9241_110` — dialog principles / fault tolerance
- `src_fogg_behaviormodel` — B=MAP
- `src_webaim_wcag_checklist` — contrast minimum
"""
	(GUIDES / "guide_form_opt.md").write_text(md, encoding="utf-8")
	meta = {
		"guide_id": "guide_form_opt",
		"title": "Form & Checkout Engineering Playbook",
		"slug": "form-checkout",
		"situation_keys": ["feature", "greenfield", "conversion"],
		"taxonomy_paths": [["Product Surfaces", "Forms"], ["Product Surfaces", "Conversion"]],
		"claim_ids": [
			"UX_ARC_FORM_010",
			"UX_PRD_GUEST_001",
			"UX_INX_ERR_009",
			"UX_INX_SELF_001",
			"UX_COG_FOGG_013",
			"UX_ARC_ISO_001",
			"UX_A11Y_CONT_005",
		],
		"source_ids": [
			"src_baymard_form_design",
			"src_baymard_checkout",
			"src_iso_9241_110",
			"src_fogg_behaviormodel",
			"src_webaim_wcag_checklist",
		],
		"status": "accepted",
		"created_at": TODAY,
		"checklist_passed": True,
	}
	(GUIDES / "guide_form_opt.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
	print("guide updated")


def patch_extracts() -> None:
	fogg_path = ROOT / "06_corpus" / "extracts" / "src_fogg_behaviormodel.json"
	fogg = json.loads(fogg_path.read_text(encoding="utf-8"))
	for claim in fogg["claims"]:
		claim.setdefault(
			"tradeoffs",
			"Motivation hacks without Ability work erode trust; prompt spam creates banner blindness.",
		)
		claim.setdefault(
			"common_mistakes",
			"Adding more CTAs when the form is too hard; prompting at low-motivation moments.",
		)
		claim.setdefault(
			"examples",
			[
				"Simplify checkout steps before adding urgency banners",
				"Show prompt when cart value motivation is high",
			],
		)
	fogg_path.write_text(json.dumps(fogg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

	polaris_path = ROOT / "06_corpus" / "extracts" / "src_shopify_polaris.json"
	polaris = json.loads(polaris_path.read_text(encoding="utf-8"))
	for claim in polaris["claims"]:
		claim.setdefault(
			"when_not_to_apply",
			"One-off marketing art outside the product shell; still verify text contrast if text is present.",
		)
		claim.setdefault(
			"tradeoffs",
			"Token migration cost; requires governance so teams do not bypass tokens.",
		)
		claim.setdefault(
			"common_mistakes",
			"Hard-coding hex in feature CSS; using the same green for brand and success with different meanings.",
		)
		claim.setdefault(
			"examples",
			["color-critical for destructive actions", "color-success for confirmations"],
		)
	polaris_path.write_text(json.dumps(polaris, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	print("patched extracts")


def main() -> None:
	fix_carbon()
	cards = build_cards()
	write_cards(cards)
	write_comparisons()
	write_graph(cards)
	write_guide()
	patch_extracts()
	print("DONE", len(cards), "cards")


if __name__ == "__main__":
	main()
