"""FULL_TEST_PLAN Case 023: AI-CKP-003."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from full_test_plan_cases.runner import run_case


if __name__ == "__main__":
    raise SystemExit(run_case("AI-CKP-003"))
