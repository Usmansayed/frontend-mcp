"""Shared pytest fixtures (SEO Intelligence parked — see parked/MVP_EXCLUDE_SEO.md)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _skip_companion_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Avoid docker/git side effects during unit tests."""
	monkeypatch.setenv("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
