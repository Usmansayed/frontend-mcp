"""Repo-rooted paths for ForOpenCode corpus."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FOROPEN = REPO_ROOT / "ForOpenCode"
RAW = FOROPEN / "06_corpus" / "raw"
EXTRACTS = FOROPEN / "06_corpus" / "extracts"
NORMALIZED = FOROPEN / "06_corpus" / "normalized"
COMPARISONS = FOROPEN / "06_corpus" / "comparisons"
GUIDES = FOROPEN / "07_guides"
GRAPHS = FOROPEN / "08_graphs"
SCHEMAS = FOROPEN / "03_schemas"
RESOURCES = FOROPEN / "05_resources"
CONTROL = FOROPEN / "00_control"
DRAFTS = FOROPEN / "10_quality" / "drafts"
PASS1_SOURCES = Path(__file__).resolve().parent / "pass1_sources.yaml"
PASS2_SOURCES = Path(__file__).resolve().parent / "pass2_sources.yaml"


def pass_sources_path(pass_num: int) -> Path:
	if pass_num == 1:
		return PASS1_SOURCES
	if pass_num == 2:
		return PASS2_SOURCES
	raise ValueError(f"Unknown pass: {pass_num}")

