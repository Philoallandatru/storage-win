"""Run plan/preflight mode for a selected FULL_TEST_PLAN set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from full_test_plan_cases.catalog import load_catalog
from full_test_plan_cases.runner import run_case


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all matching FULL_TEST_PLAN case entrypoints")
    parser.add_argument("--mode", choices=("plan", "preflight"), default="plan")
    parser.add_argument("--family")
    parser.add_argument("--priority", choices=("P0", "P1", "P2"))
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--results-dir", default="results/full_test_plan")
    args = parser.parse_args()
    selected = [
        case for case in load_catalog()
        if (not args.family or case["family"].lower() == args.family.lower())
        and (not args.priority or case["priority"] == args.priority)
    ]
    failures = 0
    for case in selected:
        failures += run_case(case["case_id"], [
            "--mode", args.mode,
            "--data-dir", args.data_dir,
            "--results-dir", args.results_dir,
        ]) != 0
    print(f"selected={len(selected)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
