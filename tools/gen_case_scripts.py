"""Generate one simple .cmd script per native case (+ 1TB/2TB capacity variants).

Each script is self-contained: run it directly (``AI-TRN-003.cmd``) and it
invokes the unified executor with sane defaults.  The only per-machine edits
are the DATA_DIR / RESULT_DIR variables at the top.

Regenerate after changing the catalogs:
    python tools/gen_case_scripts.py
"""

from __future__ import annotations

import ast
import json
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
REM  (capacity variants default both to G: - run_case bypasses CAP-03)
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


def _label_for(base_id: str) -> str:
    try:
        return _model_label(CASES_DIR / f"test_{base_id.lower().replace('-', '_')}.py")
    except Exception:
        return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0

    # capacity variants (1TB / 2TB) default to a single drive (G: for both)
    capacity_path = REPO_ROOT / "full_test_plan_cases" / "capacity_catalog.json"
    capacity = json.loads(capacity_path.read_text(encoding="utf-8"))
    for tier in ("1TB", "2TB", "4TB"):
        for cid, spec in capacity.get(tier, {}).items():
            if str(cid).startswith("_"):
                continue
            # capacity variants: single drive (data + results on G:); swap the
            # RESULT_DIR default BEFORE format so {case_id} is still literal
            tpl = TEMPLATE.replace(
                'set "RESULT_DIR=D:\\MLPerfStorageTest',
                'set "RESULT_DIR=G:\\MLPerfStorageTest',
            )
            body = tpl.format(
                case_id=cid,
                case_id_lower=cid.lower(),
                model=_label_for(spec["base"]) or "capacity",
            )
            (OUT_DIR / f"{cid}.cmd").write_text(body, encoding="utf-8", newline="\r\n")
            generated += 1

    # native cases
    for py in sorted(CASES_DIR.glob("test_ai_*.py")):
        case_id = py.stem.replace("test_", "").replace("_", "-").upper()
        label = _model_label(py)
        content = TEMPLATE.format(
            case_id=case_id,
            case_id_lower=case_id.lower(),
            model=label or "native",
        )
        (OUT_DIR / f"{case_id}.cmd").write_text(content, encoding="utf-8", newline="\r\n")
        generated += 1
    print(f"generated {generated} scripts in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
