#!/usr/bin/env python
"""Entry: python scripts/decision_lab.py run|list|repl"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
