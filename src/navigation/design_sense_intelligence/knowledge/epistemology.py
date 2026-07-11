"""Epistemology & evaluative engine — structured from Gemini Architecture doc."""
from __future__ import annotations

from .types import EvaluationChecklist, HeuristicEntry, PsychologyLaw, SeverityLevel

# Sourced from: knowledge/Architecture and Epistemology of an AI-Driven Design Evaluative Engine.md

NIELSEN_HEURISTICS: tuple[HeuristicEntry, ...] = (
	HeuristicEntry('nielsen_h1', 'Visibility of system status', 'System provides immediate, understandable feedback.', 'Is feedback provided within 100ms? Are loading states appropriate?'),
	HeuristicEntry('nielsen_h2', 'Match between system and real world', 'System speaks the user\'s language, not engineering jargon.', 'Is copy free of internal jargon?'),
	HeuristicEntry('nielsen_h3', 'User control and freedom', 'Emergency exits: undo, redo, cancel without data loss.', 'Can users undo destructive or lengthy operations?'),
	HeuristicEntry('nielsen_h4', 'Consistency and standards', 'Same words/actions mean the same thing; follow platform conventions.', 'Does UI follow platform HIG/Material conventions?'),
	HeuristicEntry('nielsen_h5', 'Error prevention', 'Prevent invalid states structurally, not just error messages.', 'Are invalid inputs prevented (e.g. past dates disabled)?'),
	HeuristicEntry('nielsen_h6', 'Recognition rather than recall', 'Objects, actions, options visible — minimize memory load.', 'Must users remember info from a prior screen?'),
	HeuristicEntry('nielsen_h7', 'Flexibility and efficiency of use', 'Accelerators for expert users alongside novice-friendly defaults.', 'Are keyboard shortcuts or macros available?'),
	HeuristicEntry('nielsen_h8', 'Aesthetic and minimalist design', 'Dialogues contain no irrelevant information.', 'Is every element earning its place?'),
	HeuristicEntry('nielsen_h9', 'Help users recognize, diagnose, recover from errors', 'Plain language errors with constructive solutions.', 'Do errors explain problem and fix in plain language?'),
	HeuristicEntry('nielsen_h10', 'Help and documentation', 'Searchable, task-focused, concrete steps.', 'Is help available and task-oriented?'),
)

GESTALT_PRINCIPLES: tuple[HeuristicEntry, ...] = (
	HeuristicEntry('gestalt_proximity', 'Law of Proximity', 'Close elements perceived as related.', 'Are related controls grouped with smaller internal margins?'),
	HeuristicEntry('gestalt_similarity', 'Law of Similarity', 'Similar visual traits imply similar function.', 'Do same-looking elements behave the same?'),
	HeuristicEntry('gestalt_continuity', 'Law of Continuity', 'Eye follows continuous paths (F-pattern, Z-pattern).', 'Does layout support natural scanning flow?'),
	HeuristicEntry('gestalt_closure', 'Law of Closure', 'Brain completes incomplete shapes.', 'Is minimalist iconography still recognizable?'),
	HeuristicEntry('gestalt_figure_ground', 'Figure-Ground', 'Interactive elements separate from background via contrast/elevation.', 'Are CTAs distinct from background containers?'),
)

PSYCHOLOGY_LAWS: tuple[PsychologyLaw, ...] = (
	PsychologyLaw('fitts_law', "Fitts's Law", 'T = a + b·log₂(1 + D/W)', 'Place primary CTAs in low-distance, high-width zones; edge targets are optimal.'),
	PsychologyLaw('hicks_law', "Hick's Law", 'RT = a + b·log₂(n)', 'Reduce choices per step to prevent analysis paralysis.'),
	PsychologyLaw('millers_law', "Miller's Law", '7±2 items in working memory', 'Chunk dense information; limit menu items to ~7.'),
	PsychologyLaw('jakobs_law', "Jakob's Law", 'Users prefer familiar patterns from other products', 'Penalize novel patterns unless efficiency gain justifies relearning.'),
	PsychologyLaw('aesthetic_usability', 'Aesthetic-Usability Effect', 'Pleasant designs perceived as easier to use', 'Polish can forgive minor usability flaws — but do not rely on it.'),
	PsychologyLaw('cognitive_load', 'Cognitive Load Theory', 'Intrinsic + extraneous + germane load', 'Eliminate extraneous load; optimize germane load.'),
)

HEART_VECTORS: tuple[str, ...] = (
	'Happiness — subjective satisfaction (NPS, surveys)',
	'Engagement — frequency and depth of interaction',
	'Adoption — new users or feature uptake',
	'Retention — returning users over time',
	'Task Success — efficiency, effectiveness, error rate',
)

NPCIS_VECTORS: tuple[str, ...] = (
	'Navigation — pathways and wayfinding',
	'Presentation — display, hierarchy, aesthetics',
	'Content — clarity, readability, relevance of copy',
	'Interaction — response to inputs and gestures',
	'Strategy — alignment with business goals and jobs-to-be-done',
)

SEVERITY_LEVELS: tuple[SeverityLevel, ...] = (
	SeverityLevel(0, 'No Violation', 'Intentional behavior; no usability problem.'),
	SeverityLevel(1, 'Cosmetic Issue', 'Minor visual inconsistency; fix if time permits.'),
	SeverityLevel(2, 'Minor Usability Problem', 'Slight friction; user recovers easily.'),
	SeverityLevel(3, 'Major Usability Problem', 'Flow significantly disrupted; high priority.'),
	SeverityLevel(4, 'Usability Catastrophe', 'Blocks core task or causes data loss — fix before release.'),
)

RULE_HIERARCHY: tuple[tuple[int, str, str], ...] = (
	(1, 'Absolute Constraints', 'WCAG math, touch targets, HTML validity — non-negotiable.'),
	(2, 'Platform Conventions', 'Apple HIG, Material Design — strongly recommended.'),
	(3, 'Brand & Design System', 'Corporate identity tokens and component rules.'),
	(4, 'Heuristic Best Practices', 'Nielsen, cognitive load, visual density preferences.'),
)

DOMAIN_CHECKLISTS: tuple[EvaluationChecklist, ...] = (
	EvaluationChecklist(
		'typography', 'typography_reviewer', 'objective',
		(
			'Semantic hierarchy (H1–H6) structurally sound and visually distinct',
			'Body text minimum 16px for cross-device readability',
			'Line height ~1.5× font size for body text',
			'Line length 40–60 characters',
			'WCAG 2.1 AA contrast ratio on all text nodes',
			'Maximum 2–3 typeface families',
		),
	),
	EvaluationChecklist(
		'layout', 'layout_reviewer', 'objective',
		(
			'Elements snapped to unified 4pt/8pt grid',
			'Visual balance via composition check',
			'Gestalt proximity: unrelated groups have larger margins than within groups',
			'Adequate whitespace between cognitive zones',
			'Primary CTAs in high-visibility zones (Fitts\'s Law)',
		),
	),
	EvaluationChecklist(
		'color', 'color_reviewer', 'objective',
		(
			'Contrast ratio compliant on text and interactive elements',
			'Semantic colors restricted to recognized states',
			'Accent color reserved for clickable targets',
			'Information not conveyed by hue alone',
			'Distinct hues minimized to reduce visual congestion',
		),
	),
	EvaluationChecklist(
		'navigation', 'navigation_reviewer', 'subjective',
		(
			'Active nav state visibly differentiated',
			'Nav lists grouped if count exceeds seven (Miller\'s Law)',
			'Breadcrumbs in multi-level hierarchies',
			'Labels concise; no truncation on small viewports',
			'Consistent escape route (Home or Back)',
		),
	),
	EvaluationChecklist(
		'interaction', 'ux_reviewer', 'objective',
		(
			'Interactive elements have default, hover, active, focus, disabled states',
			'Feedback within 100ms threshold',
			'Destructive actions protected by confirmation',
			'Inline form validation, not post-submit only',
			'Touch targets adequately sized and spaced',
		),
	),
)
