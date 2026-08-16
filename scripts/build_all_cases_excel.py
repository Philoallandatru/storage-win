"""Build an Excel of resolved mlpstorage commands for all native FULL_TEST_PLAN cases.

Walks the case catalog's ``native_commands`` (the legacy per-case
entrypoints under ``full_test_plan_cases/cases/`` were merged into the
catalog — see run_case.py), applies the same placeholder substitution
the unified executor uses, and writes the resolved commands to a single
Excel workbook with one sheet per family plus a summary sheet.

Output: docs/AI_SSD_NATIVE_CASES_MLPSTORAGE_COMMANDS.xlsx

The script is read-only with respect to source — it doesn't modify any
case files, the catalog, or the existing all-case-plan Excel. It just
renders a fresh workbook that the user can drop into a docs/ folder
or share with operators.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "full_test_plan_cases" / "case_catalog.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "AI_SSD_NATIVE_CASES_MLPSTORAGE_COMMANDS.xlsx"

from full_test_plan_cases.shrink import MIX_VDB_DRIVE  # noqa: E402

# Default runtime knobs — same defaults as the unified executor (run_case.py).
DEFAULTS = {
    "data_dir": "C:\\MLPerfStorageTest\\data\\<case_id>",
    "results_dir": "D:\\MLPerfStorageTest\\results\\<case_id>",
    "loops": 1,
    "mpi_bin": "mpiexec",
    "num_accelerators": 1,
    "client_memory_gb": 64,
    "duration_sec": 60,
    "query_processes": 1,
    "num_users": 200,
    "gpu_mem_gb": 0,
    "cpu_mem_gb": 0,
    "accelerator_type": "h100",
    "systemname_suffix": "native",
}

# Column layout: keeps the workbook readable when printed or pasted
# into Confluence / Feishu / Markdown.
COLUMNS = [
    ("Case No", 8),
    ("Case ID", 12),
    ("Family", 12),
    ("Model", 18),
    ("Profile", 10),
    ("Priority", 10),
    ("Phase", 12),
    ("Accelerator", 12),
    ("Data Dir", 50),
    ("Results Dir", 50),
    ("System Name", 28),
    ("Native Status", 14),
    ("Native Reason", 22),
    ("Resolved Command", 110),
]

HEADER_FILL = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
PHASE_FILL = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
WRAP = Alignment(wrap_text=True, vertical="top")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--data-drive", default="C")
    p.add_argument("--results-drive", default="D")
    p.add_argument("--vdb-drive", default=MIX_VDB_DRIVE.rstrip(":"),
                   help="drive for the MIX VectorDB stream data (default E)")
    p.add_argument("--test-root", default="MLPerfStorageTest")
    p.add_argument("--include-status", action="append", default=["SUPPORTED"],
                   help="Native status values to include (default: SUPPORTED). "
                        "Use multiple --include-status to add more, e.g. --include-status SUPPORTED --include-status PREVIEW")
    p.add_argument("--dry-run", action="store_true", help="Print summary, do not write Excel")
    return p


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def resolve_command(entry: dict, cmd_entry: dict, model: str,
                    args: argparse.Namespace,
                    vdb_data_dir: Path | None = None) -> dict:
    """Resolve one native command's placeholders into a concrete row dict.

    The catalog is the single source of truth (the legacy ``test_ai_*.py``
    case entrypoints were merged away — see run_case.py), so substitution
    uses the same placeholders the catalog's ``native_commands`` reference.

    ``vdb_data_dir`` is the secondary drive for MIX cases (same default E:
    as run_ai_ssd_suite --vdb-drive); non-MIX cases ignore it.
    """
    case_id = entry["case_id"]
    case_id_lower = case_id.lower()
    data_dir = (Path(f"{args.data_drive}:\\{args.test_root}\\data") / case_id_lower).resolve()
    results_dir = (Path(f"{args.results_drive}:\\{args.test_root}\\results") / case_id_lower).resolve()
    vdb_dir = vdb_data_dir or data_dir
    values = {
        "<DATA_DIR>": str(data_dir),
        "<RESULTS_DIR>": str(results_dir),
        "<CHECKPOINT_DIR>": str(data_dir / "checkpoint" / case_id),
        "<CACHE_DIR>": str(data_dir / "kvcache" / case_id),
        "<STORAGE_ROOT>": str(data_dir / "milvus" / case_id),
        # MIX dual-drive placeholders (same keys run_case.py resolves).
        "<MIX_KV_CACHE_DIR>": str(data_dir / "kvcache" / case_id),
        "<MIX_VDB_STORAGE_ROOT>": str(vdb_dir / "milvus" / case_id),
        "<SYSTEMNAME>": f"{case_id_lower}-{DEFAULTS['systemname_suffix']}",
        "<LOOPS>": str(DEFAULTS["loops"]),
        "<MPI_BIN>": DEFAULTS["mpi_bin"],
        "<ACCELERATORS>": str(DEFAULTS["num_accelerators"]),
        "<CLIENT_MEMORY_GB>": str(DEFAULTS["client_memory_gb"]),
        "<DURATION_SEC>": str(DEFAULTS["duration_sec"]),
        "<QUERY_PROCESSES>": str(DEFAULTS["query_processes"]),
    }
    argv = []
    for tok in cmd_entry["argv"]:
        if isinstance(tok, str) and tok in values:
            argv.append(values[tok])
        else:
            argv.append(tok)
    # Inject --accelerator-type on TRN/CKP run phases if missing.
    if cmd_entry["phase"] == "run" and any(
        k in argv for k in ("training", "checkpointing")
    ) and "--accelerator-type" not in argv:
        argv += ["--accelerator-type", DEFAULTS["accelerator_type"]]

    return {
        "case_id": case_id,
        "phase": cmd_entry["phase"],
        "argv": argv,
        "data_dir": str(data_dir),
        "results_dir": str(results_dir),
        "systemname": values["<SYSTEMNAME>"],
        "native_status": entry.get("native_status", "UNKNOWN"),
        "native_reason": entry.get("native_block_reason") or entry.get("native_reason"),
    }


def detect_model(commands: list[dict], case_id: str) -> str:
    """Best-effort model extraction from the case's COMMANDS list."""
    text = " ".join(tok for c in commands for tok in c["argv"])
    candidates = [
        "llama3.1-8b", "llama3-8b", "llama3-70b", "llama3-405b",
        "retinanet", "resnet50", "unet3d", "cosmoflow",
        "vit", "bert", "gpt3", "yolo", "efficientnet",
    ]
    for c in candidates:
        if c in text:
            return c
    return ""


def render_command(argv: list[str]) -> str:
    """Render an argv as a single command string for the Excel cell."""
    out = []
    for tok in argv:
        if " " in str(tok) or "=" in str(tok) or "\\" in str(tok):
            out.append(f'"{tok}"')
        else:
            out.append(str(tok))
    return " ".join(out)


def build_rows(catalog: list[dict], args: argparse.Namespace) -> list[dict]:
    """Build one row per (case, phase) for every case in the catalog."""
    rows = []
    for entry in catalog:
        case_id = entry["case_id"]
        status = entry.get("native_status", "UNKNOWN")
        if status not in args.include_status:
            continue
        commands = entry.get("native_commands") or []
        if not commands:
            rows.append({
                "case_no": entry.get("case_no"),
                "case_id": case_id,
                "family": entry.get("family", ""),
                "model": "",
                "profile": entry.get("profile", ""),
                "priority": entry.get("priority", ""),
                "phase": "—",
                "accelerator": "",
                "data_dir": "",
                "results_dir": "",
                "systemname": "",
                "native_status": status,
                "native_reason": entry.get("native_block_reason") or "no native_commands in catalog",
                "command": "",
                "error": "",
            })
            continue
        model = detect_model(commands, case_id)
        # MIX cases run VectorDB on the secondary drive (E: by default).
        vdb_data_dir = None
        if entry.get("family") == "MIX":
            vdb_data_dir = (Path(f"{args.vdb_drive}:\\{args.test_root}\\data") / case_id.lower()).resolve()
        for cmd in commands:
            resolved = resolve_command(entry, cmd, model, args, vdb_data_dir=vdb_data_dir)
            accelerator = ""
            argv = resolved["argv"]
            for i, tok in enumerate(argv):
                if tok == "--accelerator-type" and i + 1 < len(argv):
                    accelerator = argv[i + 1]
                    break
            rows.append({
                "case_no": entry.get("case_no"),
                "case_id": resolved["case_id"],
                "family": entry.get("family", ""),
                "model": model,
                "profile": entry.get("profile", ""),
                "priority": entry.get("priority", ""),
                "phase": resolved["phase"],
                "accelerator": accelerator,
                "data_dir": resolved["data_dir"],
                "results_dir": resolved["results_dir"],
                "systemname": resolved["systemname"],
                "native_status": resolved["native_status"],
                "native_reason": resolved["native_reason"] or "",
                "command": render_command(argv),
                "error": "",
            })
    return rows


def write_workbook(rows: list[dict], output: Path, args: argparse.Namespace) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    by_family: dict[str, list[dict]] = {}
    for r in rows:
        by_family.setdefault(r["family"] or "Other", []).append(r)

    family_sheet_order = ["Training", "Checkpoint", "KV Cache", "VectorDB", "Mixed", "Other"]
    for fam in family_sheet_order:
        fam_rows = by_family.get(fam, [])
        if not fam_rows:
            continue
        ws = wb.create_sheet(title=fam)
        for col_idx, (name, width) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=name)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = WRAP
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        ws.row_dimensions[1].height = 22
        ws.freeze_panes = "A2"
        for r_idx, r in enumerate(fam_rows, start=2):
            for c_idx, (name, _) in enumerate(COLUMNS, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=r.get(_key(name), ""))
                cell.alignment = WRAP
            if r.get("error"):
                ws.cell(row=r_idx, column=COLUMNS[-1][0] and len(COLUMNS), value=r["error"]).font = Font(italic=True, color="C00000")
        # Auto-row-height for the long command cell
        for r_idx in range(2, len(fam_rows) + 2):
            ws.row_dimensions[r_idx].height = 60

    # Summary sheet.
    summary = wb.create_sheet(title="Summary", index=0)
    summary_rows = [
        ("Workbook", output.name),
        ("Generated at (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")),
        ("Source catalog", str(CATALOG_PATH.relative_to(REPO_ROOT))),
        ("Total cases in catalog", str(len(load_catalog()))),
        ("Cases included", str(len({r["case_id"] for r in rows}))),
        ("Rows (case × phase)", str(len(rows))),
        ("Filter — native status", ", ".join(args.include_status)),
        ("Default data dir", f"{args.data_drive}:\\{args.test_root}\\data\\<case-id>"),
        ("Default results dir", f"{args.results_drive}:\\{args.test_root}\\results\\<case-id>"),
        ("Default accelerator", DEFAULTS["accelerator_type"]),
        ("Default loops", str(DEFAULTS["loops"])),
        ("CAP-03", "data and results intentionally on different drives (C: vs D:)"),
        ("To re-run a case", ".\\run_case.cmd <AI-XXX-NNN> --data-dir <…> --results-dir <…>"),
    ]
    for r_idx, (k, v) in enumerate(summary_rows, start=1):
        summary.cell(row=r_idx, column=1, value=k).font = Font(bold=True)
        summary.cell(row=r_idx, column=2, value=v).alignment = WRAP
    summary.column_dimensions["A"].width = 26
    summary.column_dimensions["B"].width = 80
    summary.row_dimensions[1].height = 18

    # Per-family count breakdown.
    start = len(summary_rows) + 3
    summary.cell(row=start, column=1, value="Per-family row breakdown").font = Font(bold=True)
    for r_idx, fam in enumerate(family_sheet_order, start=start + 1):
        count = len(by_family.get(fam, []))
        summary.cell(row=r_idx, column=1, value=fam)
        summary.cell(row=r_idx, column=2, value=f"{count} row(s) / {len({r['case_id'] for r in by_family.get(fam, [])})} case(s)")

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)


def _key(display_name: str) -> str:
    """Map column display name to row-dict key."""
    return {
        "Case No": "case_no",
        "Case ID": "case_id",
        "Family": "family",
        "Model": "model",
        "Profile": "profile",
        "Priority": "priority",
        "Phase": "phase",
        "Accelerator": "accelerator",
        "Data Dir": "data_dir",
        "Results Dir": "results_dir",
        "System Name": "systemname",
        "Native Status": "native_status",
        "Native Reason": "native_reason",
        "Resolved Command": "command",
    }[display_name]


def main() -> int:
    args = build_argparser().parse_args()
    catalog = load_catalog()
    rows = build_rows(catalog, args)

    # Print a short summary to stdout regardless of --dry-run.
    by_family: dict[str, int] = {}
    for r in rows:
        by_family[r["family"]] = by_family.get(r["family"], 0) + 1
    print(f"=== Build summary ===")
    print(f"Total rows: {len(rows)}")
    for fam, n in sorted(by_family.items()):
        print(f"  {fam}: {n} row(s)")
    if args.dry_run:
        print("(dry-run, Excel not written)")
        return 0

    write_workbook(rows, args.output, args)
    print(f"Written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
