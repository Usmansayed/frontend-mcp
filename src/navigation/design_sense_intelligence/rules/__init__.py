"""Design Lint rule engine (DOM/CSS port) — foundation for Consistency Intelligence."""
from .engine import LintResult, run_lint
from .meta import RULE_META

__all__ = ['RULE_META', 'LintResult', 'run_lint']
