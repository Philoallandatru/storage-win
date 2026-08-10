"""Compatibility CLI for the Training commands in AI_SSD_ALL_CASE_PLAN.xlsx."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_ssd_test_cases.runner import run_case


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one AI SSD Training Case")
    parser.add_argument("--case", required=True, choices=[f"AI-TRN-{number:03d}" for number in range(1, 17)])
    args, rest = parser.parse_known_args()
    if "--execute" not in rest:
        rest = ["--execute", *rest]
    return run_case(args.case, rest)


if __name__ == "__main__":
    raise SystemExit(main())
