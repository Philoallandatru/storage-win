"""Fast structural tests for the executable consumer AI-PC SSD cases."""

from __future__ import annotations

import json
from pathlib import Path

from tools.ai_ssd_cases.catalog import CASES
from tools.ai_ssd_cases.runner import run_case


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "tools" / "ai_ssd_cases" / "cases"


def _filename(case_id: str) -> str:
    return case_id.lower().replace("-", "_") + ".py"


def test_consumer_matrix_has_native_cases_and_entrypoints() -> None:
    assert len(CASES) == 20
    for case_id in CASES:
        assert (CASE_DIR / _filename(case_id)).is_file(), case_id


def test_case_entrypoints_are_one_file_per_case() -> None:
    files = {
        path.name
        for path in CASE_DIR.glob("*.py")
        if path.name not in {"__init__.py", "_template.py"}
    }
    assert files == {_filename(case_id) for case_id in CASES}


def test_case_dry_run_writes_a_verdict(tmp_path: Path) -> None:
    dut = tmp_path / "dut"
    results = tmp_path / "results"
    rc = run_case(
        "S2-CKPT-01",
        [
            "--dut-root", str(dut),
            "--results-root", str(results),
            "--mode", "dry-run",
        ],
    )
    assert rc == 0
    verdicts = list((results / "S2-CKPT-01").glob("*/verdict.json"))
    assert len(verdicts) == 1
    payload = json.loads(verdicts[0].read_text(encoding="utf-8"))
    assert payload["status"] == "DRY_RUN"
    assert payload["results"][0]["command"]
