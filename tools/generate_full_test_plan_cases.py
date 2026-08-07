"""Generate one Python entrypoint per case from the inspected FULL workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "full_test_plan_cases"
SOURCE_ROOT = OUTPUT_ROOT / "source"
DEFAULT_WORKBOOK = SOURCE_ROOT / "FULL_TEST_PLAN.xlsx"
DEFAULT_INSPECT = SOURCE_ROOT / "FULL_TEST_PLAN.xlsx.inspect.ndjson"
EXPECTED_SHA256 = "fada60afe5124244551ce248d3e8e3149a57a5b1b25bed2bc212d860d1d27656"


def _tables(path: Path) -> dict[str, list[list[Any]]]:
    found: dict[str, list[list[Any]]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        item = json.loads(line)
        if item.get("kind") == "table" and item.get("sheet") in {"Case执行矩阵", "完整覆盖索引"}:
            found[item["sheet"]] = item["values"]
    if set(found) != {"Case执行矩阵", "完整覆盖索引"}:
        raise ValueError(f"Missing FULL workbook tables in {path}: {sorted(found)}")
    return found


def _case_rows(values: list[list[Any]]) -> list[list[Any]]:
    return [row for row in values if row and isinstance(row[0], str) and re.fullmatch(r"AI-[A-Z]+-\d{3}", row[0])]


def _steps(value: str) -> list[str]:
    return [re.sub(r"^\d+\)\s*", "", line).strip() for line in value.splitlines() if line.strip()]


def build_catalog(inspect_path: Path) -> list[dict[str, Any]]:
    tables = _tables(inspect_path)
    execution = {row[0]: row for row in _case_rows(tables["Case执行矩阵"])}
    coverage_rows = _case_rows(tables["完整覆盖索引"])
    if len(execution) != 72 or len(coverage_rows) != 72:
        raise ValueError(f"Expected 72 FULL cases, got execution={len(execution)} coverage={len(coverage_rows)}")
    catalog: list[dict[str, Any]] = []
    for number, coverage in enumerate(coverage_rows, start=1):
        case_id = coverage[0]
        matrix = execution[case_id]
        catalog.append({
            "case_no": number,
            "case_id": case_id,
            "family": coverage[1],
            "profile": coverage[2],
            "priority": coverage[3],
            "requirements": [item for item in coverage[4].split(";") if item],
            "model_config": coverage[5],
            "test_purpose": coverage[6],
            "primary_variables": coverage[7],
            "primary_metrics": coverage[8],
            "windows_status": coverage[9],
            "tool": matrix[1],
            "purpose": matrix[2],
            "steps": _steps(matrix[3]),
            "duration": matrix[4],
            "source_command": matrix[5],
            "standard": matrix[6],
        })
    return catalog


def _filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


def _entrypoint(case: dict[str, Any]) -> str:
    return f'''"""FULL_TEST_PLAN Case {case["case_no"]:03d}: {case["case_id"]}."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from full_test_plan_cases.runner import run_case


if __name__ == "__main__":
    raise SystemExit(run_case("{case["case_id"]}"))
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--inspect", type=Path, default=DEFAULT_INSPECT)
    args = parser.parse_args()
    digest = hashlib.sha256(args.workbook.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"FULL workbook SHA-256 changed: {digest}")
    catalog = build_catalog(args.inspect)
    cases_dir = OUTPUT_ROOT / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "case_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in catalog:
        (cases_dir / _filename(case["case_id"])).write_text(_entrypoint(case), encoding="utf-8")
    print(f"generated {len(catalog)} FULL_TEST_PLAN scripts in {cases_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
