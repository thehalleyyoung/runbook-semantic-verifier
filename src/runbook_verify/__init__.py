"""Formal Runbook Verification prototype."""

from .checker import Checker, CheckResult, Violation
from .parser import load_runbook
from .semantic_diff import diff_runbooks

__all__ = ["Checker", "CheckResult", "Violation", "diff_runbooks", "load_runbook"]
__version__ = "0.1.0"
