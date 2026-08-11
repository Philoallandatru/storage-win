"""Generate one simple .cmd script per native case.

Each script is self-contained: run it directly (``AI-TRN-003.cmd``) and it
invokes the corresponding case entrypoint with sane defaults.  The only
per-machine edits are the DATA_DIR / RESULT_DIR variables at the top
(they must live on different filesystems - CAP-03).

Regenerate after changing ``case_catalog.json`` or the case set:
    python tools/gen_case_scripts.py
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"
OUT_DIR = REPO_ROOT / "scripts" / "cases"

# NOTE: keep this template pure ASCII (cmd.exe parses .cmd with the system
# code page; non-ASCII comments break on GBK systems).  Backslashes in the
# template must be doubled because this is a Python triple-quoted string.
TEMPLATE = """@echo off
REM ============================================================
REM  {case_id}  {model}  - run this script directly
REM  DATA_DIR and RESULT_DIR must be on different filesystems (CAP-03)
REM ============================================================
setlocal

cd /d "%~dp0..\\.."
set "REPO_ROOT=%CD%"
set "PY=%REPO_ROOT%\\.venv\\Scripts\\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%REPO_ROOT%\\.venv\\Scripts;%PATH%"

REM ---------- edit these two per machine (must be different drives) ----------
set "DATA_DIR=G:\\MLPerfStorageTest\\data\\{case_id}"
set "RESULT_DIR=D:\\MLPerfStorageTest\\results\\{case_id}"

REM ---------- dev: uncomment the two lines below to shrink the dataset ----------
REM set "NUM_FILES_TRAIN=8"
REM set "ALLOW_INVALID=1"

set "EXTRA="
if defined NUM_FILES_TRAIN set "EXTRA=%EXTRA% --num-files-train %NUM_FILES_TRAIN%"
if "%ALLOW_INVALID%"=="1" set "EXTRA=%EXTRA% --allow-invalid-params"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case {case_id} --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname {case_id_lower} %EXTRA%
set "RC=%ERRORLEVEL%"
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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for py in sorted(CASES_DIR.glob("test_ai_*.py")):
        case_id = py.stem.replace("test_", "").replace("_", "-").upper()
        label = _model_label(py)
        content = TEMPLATE.format(
            case_id=case_id,
            case_id_lower=case_id.lower(),
            case_file=py.name,
            model=label or "native",
        )
        out = OUT_DIR / f"{case_id}.cmd"
        out.write_text(content, encoding="utf-8", newline="\r\n")
        generated += 1
    print(f"generated {generated} scripts in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
