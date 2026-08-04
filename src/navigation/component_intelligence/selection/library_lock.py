"""Library-first foundation resolution — durable lock, not registry beauty contest.

Invariant (Tests 10–12):
  The unit of foundation is a LIBRARY id (@shadcn, …), never a random registry block.
  Specialty packs (aceternity hero+navbar), auth blocks, and generic-token hits
  cannot advance component_select unless the host explicitly asks for specialty.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import ComponentCandidate, ParsedQuery
from .filter import (
	DECORATIVE_REGISTRIES,
	FOUNDATION_REGISTRIES,
	query_allows_specialty_foundation,
)

# Explicit library names the host may request in the query.
_EXPLICIT_LIBRARY_MARKERS: tuple[tuple[str, str], ...] = (
	("shadcn", "@shadcn"),
	("@shadcn", "@shadcn"),
	("radix", "@shadcn"),
	("once-ui", "@once-ui-system"),
	("once ui", "@once-ui-system"),
	("@once-ui-system", "@once-ui-system"),
	("aceternity", "@aceternity"),
	("magicui", "@magicui"),
	("magic ui", "@magicui"),
	("mui", "@mui"),
	("material ui", "@mui"),
	("@mui", "@mui"),
	("chakra", "@chakra"),
	("mantine", "@mantine"),
)

_COMPETING_DS_DEPS: dict[str, str] = {
	"@once-ui-system/core": "@once-ui-system",
	"@once-ui-system/core.css": "@once-ui-system",
	"once-ui": "@once-ui-system",
	"@mui/material": "@mui",
	"@chakra-ui/react": "@chakra",
	"@mantine/core": "@mantine",
	"antd": "@antd",
}


@dataclass(slots=True)
class LibraryResolution:
	library_id: str | None
	evidence: list[str] = field(default_factory=list)
	confidence: float = 0.0
	refused: bool = False
	refuse_reason: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			"library_id": self.library_id,
			"evidence": list(self.evidence),
			"confidence": self.confidence,
			"refused": self.refused,
			"refuse_reason": self.refuse_reason,
		}


def normalize_library_id(raw: str | None) -> str | None:
	if not raw:
		return None
	text = str(raw).strip().lower()
	if not text:
		return None
	if text in {"shadcn", "ui", "radix-ui", "radix"}:
		return "@shadcn"
	if not text.startswith("@"):
		text = f"@{text}"
	# Map bare decorative names
	aliases = {
		"@ui": "@shadcn",
		"@radix-ui": "@shadcn",
	}
	return aliases.get(text, text)


def is_valid_foundation_library(library_id: str | None, *, allow_specialty: bool = False) -> bool:
	norm = normalize_library_id(library_id)
	if not norm:
		return False
	if norm in {r.lower() if r.startswith("@") else f"@{r.lower()}" for r in FOUNDATION_REGISTRIES}:
		return True
	if norm in {"@shadcn", "@ui", "@radix-ui"}:
		return True
	if allow_specialty and norm in {r.lower() for r in DECORATIVE_REGISTRIES}:
		return True
	# Known alternate design systems when explicitly detected/requested
	if norm in {"@mui", "@chakra", "@mantine", "@antd", "@once-ui-system"}:
		return True
	return False


def resolve_foundation_library(
	repo_root: Path | None,
	parsed_query: ParsedQuery | None = None,
) -> LibraryResolution:
	"""Resolve which library is the project foundation — never a page block."""
	allow_specialty = query_allows_specialty_foundation(parsed_query)
	raw = (parsed_query.raw or "").lower() if parsed_query else ""

	# 1) Explicit host request wins when valid.
	for marker, library_id in _EXPLICIT_LIBRARY_MARKERS:
		if marker in raw:
			norm = normalize_library_id(library_id)
			if is_valid_foundation_library(norm, allow_specialty=allow_specialty or norm in {
				"@aceternity", "@magicui"
			}):
				return LibraryResolution(
					library_id=norm,
					evidence=[f"explicit_query:{marker}"],
					confidence=0.98,
				)

	# 2) Codebase detection.
	detected = _detect_from_repo(repo_root)
	if detected.refused:
		return detected
	if detected.library_id:
		if is_valid_foundation_library(
			detected.library_id,
			allow_specialty=allow_specialty,
		):
			return detected
		return LibraryResolution(
			library_id=None,
			evidence=detected.evidence,
			refused=True,
			refuse_reason="detected_library_not_foundation",
		)

	# 3) Specialty-only query without a library still refuses decorative default.
	if allow_specialty:
		# Host asked for specialty effects but not a named lib — still default core DS;
		# specialty blocks are starters via search_components, not foundations.
		pass

	# 4) Durable default for React/Next / unknown greenfield: @shadcn.
	return LibraryResolution(
		library_id="@shadcn",
		evidence=["default_react_foundation"],
		confidence=0.9,
	)


def make_library_candidate(
	library_id: str,
	*,
	confidence: float = 0.9,
	evidence: list[str] | None = None,
) -> ComponentCandidate:
	"""Synthetic candidate representing a library lock (not a registry block)."""
	norm = normalize_library_id(library_id) or library_id
	slug = norm.lstrip("@")
	return ComponentCandidate(
		id=f"foundation-library:{slug}",
		provider="foundation_lock",
		provider_group="foundation",
		name=slug,
		title=f"{norm} foundation library",
		category="library",
		description=f"Project component foundation locked to {norm}.",
		registry=norm,
		item_type="foundation:library",
		relevance_score=float(confidence),
		framework="react",
		tags=["foundation", "library", slug],
		metadata={
			"matched_query": "foundation_library",
			"library_id": norm,
			"lock_evidence": list(evidence or []),
			"is_library_lock": True,
		},
	)


def registry_matches_library(candidate: ComponentCandidate, library_id: str) -> bool:
	cand = normalize_library_id(candidate.registry) or normalize_library_id(
		str(candidate.metadata.get("library_id") or "")
		if isinstance(candidate.metadata, dict)
		else None
	)
	want = normalize_library_id(library_id)
	return bool(cand and want and cand == want)


def _detect_from_repo(repo_root: Path | None) -> LibraryResolution:
	if repo_root is None:
		return LibraryResolution(library_id=None, evidence=["no_repo_root"])
	root = Path(repo_root)
	evidence: list[str] = []

	pkg = root / "package.json"
	deps: dict[str, str] = {}
	if pkg.is_file():
		try:
			data = json.loads(pkg.read_text(encoding="utf-8"))
			deps = {
				**(data.get("dependencies") or {}),
				**(data.get("devDependencies") or {}),
			}
		except (json.JSONDecodeError, OSError):
			evidence.append("package_json_unreadable")

	# Declared UI systems beat generic React→shadcn (hardcore: @once-ui-system/core).
	found_ds = [lib for dep, lib in _COMPETING_DS_DEPS.items() if dep in deps]
	found_ds = list(dict.fromkeys(found_ds))
	if len(found_ds) == 1:
		evidence.append(f"package_dep:{found_ds[0]}")
		return LibraryResolution(
			library_id=found_ds[0],
			evidence=evidence,
			confidence=0.95,
		)
	if len(found_ds) > 1:
		priority = ("@once-ui-system", "@mui", "@chakra", "@mantine", "@antd")
		for pref in priority:
			if pref in found_ds:
				evidence.append(f"package_dep_preferred:{pref}")
				return LibraryResolution(
					library_id=pref,
					evidence=evidence + [f"ambiguous_ds:{','.join(found_ds)}"],
					confidence=0.9,
				)
		return LibraryResolution(
			library_id=None,
			evidence=evidence + [f"ambiguous_ds:{','.join(found_ds)}"],
			refused=True,
			refuse_reason="ambiguous_library",
		)

	# components.json ⇒ shadcn (only when no competing DS package declared)
	components_json = root / "components.json"
	if components_json.is_file():
		evidence.append("components.json")
		return LibraryResolution(
			library_id="@shadcn",
			evidence=evidence,
			confidence=0.97,
		)
	for alt in (root / "apps", root / "packages"):
		if alt.is_dir():
			for path in alt.rglob("components.json"):
				evidence.append(f"components.json:{path.relative_to(root)}")
				return LibraryResolution(
					library_id="@shadcn",
					evidence=evidence,
					confidence=0.96,
				)

	# shadcn-like stack without components.json yet
	shadcn_signals = 0
	if "tailwindcss" in deps:
		shadcn_signals += 1
		evidence.append("dep:tailwindcss")
	if any(k.startswith("@radix-ui/") for k in deps):
		shadcn_signals += 1
		evidence.append("dep:@radix-ui")
	if "class-variance-authority" in deps:
		shadcn_signals += 1
		evidence.append("dep:cva")
	ui_dir = root / "components" / "ui"
	src_ui = root / "src" / "components" / "ui"
	if ui_dir.is_dir() or src_ui.is_dir():
		shadcn_signals += 2
		evidence.append("components/ui")
	if shadcn_signals >= 2:
		return LibraryResolution(
			library_id="@shadcn",
			evidence=evidence,
			confidence=0.92,
		)

	if "react" in deps or "next" in deps:
		evidence.append("dep:react_or_next")
		return LibraryResolution(
			library_id="@shadcn",
			evidence=evidence + ["default_with_react"],
			confidence=0.88,
		)

	return LibraryResolution(library_id=None, evidence=evidence or ["no_detection"])
