"""Formal Runbook Verification prototype."""

from .checker import Checker, CheckResult, Violation
from .parser import load_runbook

__all__ = ["Checker", "CheckResult", "Violation", "load_runbook"]
__version__ = "0.1.0"
