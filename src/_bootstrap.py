"""Bootstrap: prefer local browser-use submodule when present."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX_ROOT = ROOT / "sandbox"
BROWSER_USE_ROOT = ROOT / "browser-use"

if BROWSER_USE_ROOT.is_dir():
    sys.path.insert(0, str(BROWSER_USE_ROOT))
