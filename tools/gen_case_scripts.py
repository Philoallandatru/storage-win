"""Generate one simple .cmd script per native case (+ 1TB/2TB/4TB capacity variants).

Each script is self-contained: run it directly (``AI-TRN-003.cmd``) and it
invokes the unified executor with the family dev-shrink flags baked in
(small datagen / real-I/O checkpoint smoke / short KV / Milvus-Lite VDB),
so it runs on a 512 GB disk inside the 1.5 h per-case budget.  The only
per-machine edits are the DATA_DIR / RESULT_DIR variables at the top.

Regenerate after changing the catalogs:
    python tools/gen_case_scripts.py
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from full_test_plan_cases.shrink import SKIP_REASONS, shrink_args  # noqa: E402

CASES_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"
OUT_DIR = REPO_ROOT / "scripts" / "cases"

# NOTE: keep this template pure ASCII (cmd.exe parses .cmd with the system
# code page; non-ASCII comments break on GBK systems).  Backslashes in the
# template must be doubled because this is a Python triple-quoted string.
TEMPLATE = """@echo off
REM ============================================================
REM  {case_id}  {model}  - run this script directly
REM  DATA_DIR and RESULT_DIR must be on different filesystems (CAP-03)
REM  (capacity variants default both to G: - run_case bypasses CAP-03)
REM ============================================================
setlocal

cd /d "%~dp0..\\.."
set "REPO_ROOT=%CD%"
set "PY=%REPO_ROOT%\\.venv\\Scripts\\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%REPO_ROOT%\\.venv\\Scripts;%PATH%"

REM ---------- data/results location (default: C: drive; edit for other drives) ----------
REM   Data and results are on the SAME drive by default (SINGLE_DRIVE=1 below).
REM   To use two drives, edit both paths AND set SINGLE_DRIVE=0.
set "DATA_DIR=C:\\MLPerfStorageTest\\data\\{case_id}"
set "RESULT_DIR=C:\\MLPerfStorageTest\\results\\{case_id}"

REM ---------- 1 = data and results share one drive (C:-only machine) ----------
set "SINGLE_DRIVE=1"
set "GATE="
if "%SINGLE_DRIVE%"=="1" set "GATE=--skip-fs-separation-gate"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case {case_id} --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname {case_id_lower} {shrink_flags} %GATE%
set "RC=%ERRORLEVEL%"

REM ---------- generic data cleanup (set CLEANUP=0 to keep data) ----------
if "%CLEANUP%"=="0" goto :skip_cleanup
echo "%DATA_DIR%" | findstr /i /c:"%~n0" >nul
if errorlevel 1 (
  echo [%~n0] CLEANUP_SKIPPED: DATA_DIR does not contain case id, refusing to delete: "%DATA_DIR%"
  goto :skip_cleanup
)
if exist "%DATA_DIR%" (
  echo [%~n0] cleaning data: %DATA_DIR%
  rmdir /s /q "%DATA_DIR%" 2>nul
  echo [%~n0] DATA_CLEANED
)
:skip_cleanup
endlocal & exit /b %RC%
"""


def _model_label(case_file: Path) -> str:
    """Best-effort short model label from the case file's COMMANDS."""
    try:
        tree = ast.parse(case_file.read_text(encoding="utf-8"))
    except Exception:
        return ""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "COMMANDS" for t in node.targets):
            try:
                commands = ast.literal_eval(node.value)
            except Exception:
                return ""
            argv = commands[0]["argv"]
            if "training" in argv:
                idx = argv.index("training") + 1
                if idx < len(argv) and not argv[idx].startswith("--"):
                    return argv[idx]
            if "--model" in argv:
                return argv[argv.index("--model") + 1]
            if "--vdb-index" in argv:
                return argv[argv.index("--vdb-index") + 1]
    return ""


def _label_for(base_id: str) -> str:
    try:
        return _model_label(CASES_DIR / f"test_{base_id.lower().replace('-', '_')}.py")
    except Exception:
        return ""


# Template for cases that cannot run on this machine (e.g. AI-VDB-005 AISAQ):
# a .cmd that explains WHY instead of failing with a cryptic benchmark error.
SKIP_TEMPLATE = """@echo off
REM ============================================================
REM  {case_id}  - cannot run on this machine
REM ============================================================
setlocal
echo [%~n0] SKIPPED: {reason}
echo To run this case, satisfy the requirement above and use the suite
echo script or run_case directly (see docs/AI_SSD_CASE_MATRIX.md).
exit /b 1
"""


def _shrink_flags(case_id: str) -> str:
    """Family dev-shrink flags as a cmd-line string.

    VDB's ``--milvus-uri`` points at ``%DATA_DIR%\\milvus_lite.db`` so each
    run uses its own Lite db next to the case data, and ``--vdb-config`` is
    rewritten to ``%REPO_ROOT%\\...`` so it works on any machine/path.
    """
    flags = shrink_args(case_id, Path("<DATA_DIR>"), Path("<RESULTS_DIR>"), "64GB")
    text = " ".join(flags)
    text = text.replace("<DATA_DIR>", "%DATA_DIR%").replace("<RESULTS_DIR>", "%RESULT_DIR%")
    return text.replace("full_test_plan_cases/configs/vdb_smoke.yaml",
                        "%REPO_ROOT%\\full_test_plan_cases\\configs\\vdb_smoke.yaml")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # clear stale scripts so every .cmd is regenerated from the current catalogs
    for stale in OUT_DIR.glob("*.cmd"):
        stale.unlink()
    generated = 0

    # native cases from case_catalog.json (the cases/ entrypoints were merged away)
    catalog = json.loads((REPO_ROOT / "full_test_plan_cases" / "case_catalog.json").read_text(encoding="utf-8"))
    for case in catalog:
        case_id = case["case_id"]
        if case_id in SKIP_REASONS:
            body = SKIP_TEMPLATE.format(case_id=case_id, reason=SKIP_REASONS[case_id])
            (OUT_DIR / f"{case_id}.cmd").write_text(body, encoding="utf-8", newline="\r\n")
            generated += 1
            continue
        content = TEMPLATE.format(
            case_id=case_id,
            case_id_lower=case_id.lower(),
            model=case.get("model_config") or "native",
            shrink_flags=_shrink_flags(case_id),
        )
        (OUT_DIR / f"{case_id}.cmd").write_text(content, encoding="utf-8", newline="\r\n")
        generated += 1

    # capacity variants (1TB / 2TB / 4TB) share the same single-drive C: default
    capacity_path = REPO_ROOT / "full_test_plan_cases" / "capacity_catalog.json"
    capacity = json.loads(capacity_path.read_text(encoding="utf-8"))
    for tier in ("1TB", "2TB", "4TB"):
        for cid, spec in capacity.get(tier, {}).items():
            if str(cid).startswith("_"):
                continue
            body = TEMPLATE.format(
                case_id=cid,
                case_id_lower=cid.lower(),
                model=_label_for(spec["base"]) or "capacity",
                shrink_flags=_shrink_flags(cid),
            )
            (OUT_DIR / f"{cid}.cmd").write_text(body, encoding="utf-8", newline="\r\n")
            generated += 1

    print(f"generated {generated} scripts in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
