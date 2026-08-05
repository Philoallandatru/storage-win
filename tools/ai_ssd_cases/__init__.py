"""Executable consumer AI-PC SSD test cases.

Every module under :mod:`tools.ai_ssd_cases.cases` is a thin, independently
launchable entry point.  The common runner owns preflight checks, command
construction, monitoring, evidence collection and verdict generation.
"""

from .catalog import CASES, CaseSpec, get_case

__all__ = ["CASES", "CaseSpec", "get_case"]
