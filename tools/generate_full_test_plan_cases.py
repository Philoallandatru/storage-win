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


def _training_file_count(model: str, accelerator: str) -> int | None:
    candidates = (
        SOURCE_ROOT.parent.parent / "configs" / "dlio" / "workload" / f"{model}_{accelerator}.yaml",
        SOURCE_ROOT.parent.parent / "configs" / "dlio" / "workload" / f"{model}_datagen.yaml",
    )
    for path in candidates:
        if not path.is_file():
            continue
        match = re.search(
            r"^\s*num_files_train:\s*(\d+)(?:\s+#.*)?$",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return int(match.group(1))
    return None


def _blocked_native(reason: str) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "commands": [],
    }


def _native_case_definition(case: dict[str, Any]) -> dict[str, Any]:
    """Describe only commands the repository CLI can execute directly.

    This definition is copied into each generated Case script.  It is
    intentionally not a runtime adapter: the generated file owns the command
    list and calls ``mlpstorage`` itself.
    """
    case_id = case["case_id"]
    family = case["family"]
    config = case["model_config"].lower()
    variables = case["primary_variables"].lower()

    if family in {"Base", "Mixed"}:
        return _blocked_native(
            "项目没有 Base/Mixed 对应的统一 mlpstorage 命令；不能用 Python probe 冒充 native benchmark。"
        )

    if family == "Training":
        if case_id in {"AI-TRN-014", "AI-TRN-015", "AI-TRN-016"}:
            return _blocked_native(
                "该 Case 的 scaling/cache 变量没有对应的单一 native mlpstorage 参数，需先拆成真实模型 Case。"
            )
        model_match = re.search(r"(unet3d|retinanet|cosmoflow|resnet50|dlrm|flux)", config)
        accelerator_match = re.search(r"(a100|h100|b200|mi355)", config)
        if not model_match or not accelerator_match:
            return _blocked_native(f"无法从 Case 配置解析 native training model/accelerator: {case['model_config']}")
        model = model_match.group(1)
        accelerator = accelerator_match.group(1)
        if not (model in {"unet3d", "retinanet"} and accelerator in {"b200", "mi355"}):
            return _blocked_native(
                "当前训练 Case 没有可执行的 native open 命令；whatif 只用于估算，不能作为 workload Case。"
            )
        mode = "open"
        file_count = _training_file_count(model, accelerator)
        params = ["--params", f"dataset.num_files_train={file_count}"] if file_count else []
        common = [
            mode, "training", model, "<COMMAND>", "file",
            "--data-dir", "<DATA_DIR>", "--results-dir", "<RESULTS_DIR>",
            "--systemname", "<SYSTEMNAME>", "--exec-type", "mpi", "--mpi-bin", "<MPI_BIN>",
        ]
        datagen = [
            mode, "training", model, "datagen", "file", "--num-processes", "1",
            "--data-dir", "<DATA_DIR>", "--results-dir", "<RESULTS_DIR>",
            "--systemname", "<SYSTEMNAME>", "--exec-type", "mpi", "--mpi-bin", "<MPI_BIN>",
            *params,
        ]
        run = [
            mode, "training", model, "run", "file",
            "--num-accelerators", "<ACCELERATORS>", "--accelerator-type", accelerator,
            "--client-host-memory-in-gb", "<CLIENT_MEMORY_GB>", "--loops", "<LOOPS>",
            "--data-dir", "<DATA_DIR>", "--results-dir", "<RESULTS_DIR>",
            "--systemname", "<SYSTEMNAME>", "--exec-type", "mpi", "--mpi-bin", "<MPI_BIN>",
            *params,
        ]
        return {"status": "SUPPORTED", "reason": f"native {mode} training command", "commands": [
            {"phase": "prepare", "argv": datagen}, {"phase": "run", "argv": run}
        ]}

    if family == "Checkpoint":
        if case_id in {"AI-CKP-008", "AI-CKP-009"}:
            return _blocked_native(
                "cold-cache reset 或 interval/burst 编排不是 checkpointing CLI 的单一 native 参数，不能静默改成普通 run。"
            )
        model_match = re.search(r"(8b|70b|405b|1t)", config)
        rank_match = re.search(r"(\d+)[ -]?rank", config)
        if not model_match or not rank_match:
            return _blocked_native(f"无法从 Case 配置解析 native checkpoint model/ranks: {case['model_config']}")
        model = f"llama3-{model_match.group(1)}"
        ranks = rank_match.group(1)
        command = [
            "open", "checkpointing", "run", "file", "--model", model,
            "--num-processes", ranks, "--client-host-memory-in-gb", "<CLIENT_MEMORY_GB>",
            "--checkpoint-folder", "<CHECKPOINT_DIR>", "--num-checkpoints-read", "10",
            "--num-checkpoints-write", "10", "--results-dir", "<RESULTS_DIR>",
            "--systemname", "<SYSTEMNAME>", "--exec-type", "mpi", "--mpi-bin", "<MPI_BIN>",
        ]
        return {"status": "SUPPORTED", "reason": "native open checkpointing command", "commands": [
            {"phase": "run", "argv": command}
        ]}

    if family == "VectorDB":
        if case_id == "AI-VDB-015":
            return _blocked_native(
                "AI-VDB-015 是仓库已实现的 VectorDB Trace capture/replay；它不是 native mlpstorage Case，入口位于 trace_test_cases/，不能与 native 成绩混报。"
            )
        index = next((item for item in ("DISKANN", "HNSW", "AISAQ", "IVF_FLAT", "IVF_SQ8", "FLAT") if item in config.upper()), "HNSW")
        dim_match = re.search(r"[x×](\d+)", config)
        dimension = dim_match.group(1) if dim_match else "128"
        vectors = "10000000" if "10m" in config else ("1000000" if "1m" in config else "1000")
        collection = f"{case_id.lower().replace('-', '_')}_{index.lower()}"
        datagen = [
            "open", "vectordb", "datagen", "file", "--vdb-engine", "milvus", "--vdb-index", index,
            "--host", "127.0.0.1", "--port", "19530", "--collection", collection,
            "--num-vectors", vectors, "--dimension", dimension, "--num-shards", "1", "--force",
            "--results-dir", "<RESULTS_DIR>", "--systemname", "<SYSTEMNAME>",
        ]
        run = [
            "open", "vectordb", "run", "file", "--vdb-engine", "milvus", "--vdb-index", index,
            "--host", "127.0.0.1", "--port", "19530", "--collection", collection,
            "--benchmark-mode", "timed", "--vector-dim", dimension, "--num-query-processes", "<QUERY_PROCESSES>",
            "--runtime", "<DURATION_SEC>", "--loops", "<LOOPS>", "--storage-root", "<STORAGE_ROOT>",
            "--results-dir", "<RESULTS_DIR>", "--systemname", "<SYSTEMNAME>",
        ]
        return {"status": "SUPPORTED", "reason": "native open vectordb commands; Milvus must already be healthy", "commands": [
            {"phase": "prepare", "argv": datagen}, {"phase": "run", "argv": run}
        ]}

    if family == "KV Cache":
        model_map = (
            ("llama3.1-70b", "llama3.1-70b-instruct"), ("llama3.1-8b", "llama3.1-8b"),
            ("mistral-7b", "mistral-7b"), ("llama2-7b", "llama2-7b"), ("tiny-1b", "tiny-1b"),
        )
        model = next((value for token, value in model_map if token in config), None)
        if case_id in {"AI-KV-009", "AI-KV-010", "AI-KV-011", "AI-KV-012", "AI-KV-014", "AI-KV-015", "AI-KV-016", "AI-KV-017", "AI-KV-021", "AI-KV-022"} or not model:
            return _blocked_native(
                "该 KV Case 的模型或 trace/prefill/decode/persona/TP 参数不在 mlpstorage kvcache CLI 暴露范围内。"
            )
        users_match = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)\s*users", variables)
        user_match = re.search(r"(\d+)\s*users", variables)
        users = users_match.group(1) if users_match else (user_match.group(1) if user_match else "10")
        extra: list[str] = []
        if case_id == "AI-KV-001":
            extra += ["--gpu-mem-gb", "0", "--cpu-mem-gb", "0"]
        elif case_id == "AI-KV-002":
            extra += ["--gpu-mem-gb", "0", "--cpu-mem-gb", "4"]
        elif case_id == "AI-KV-003":
            extra += ["--gpu-mem-gb", "0", "--cpu-mem-gb", "0"]
        elif case_id == "AI-KV-019":
            extra += ["--enable-rag", "--rag-num-docs", "10"]
        elif case_id == "AI-KV-020":
            extra += ["--enable-autoscaling", "--autoscaler-mode", "qos"]
        command = [
            "open", "kvcache", "run", "--model", model, "--num-users", users,
            "--duration", "<DURATION_SEC>", "--generation-mode", "realistic", "--performance-profile", "latency",
            "--trials", "3", "--inter-option-delay", "20", "--loops", "<LOOPS>",
            "--cache-dir", "<CACHE_DIR>", "--results-dir", "<RESULTS_DIR>", "--systemname", "<SYSTEMNAME>",
            "--exec-type", "mpi", "--num-processes", "1", "--hosts", "localhost", "--mpi-bin", "<MPI_BIN>",
            *extra,
        ]
        return {"status": "SUPPORTED", "reason": "native open kvcache command", "commands": [
            {"phase": "run", "argv": command}
        ]}

    return _blocked_native(f"没有 {family} 对应的 native mlpstorage 命令")


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
        workbook_command = matrix[5]
        native = _native_case_definition({
            "case_id": case_id,
            "family": coverage[1],
            "model_config": coverage[5],
            "primary_variables": coverage[7],
        })
        # Keep only cases that invoke a real native workload.  BLOCKED and
        # whatif entries are planning material, not executable test cases.
        if native["status"] != "SUPPORTED" or not native["commands"]:
            continue
        if any(command["argv"][0] != "open" for command in native["commands"]):
            continue
        native_commands = ["mlpstorage " + " ".join(item["argv"]) for item in native["commands"]]
        tool = "mlpstorage" if native["status"] == "SUPPORTED" else "BLOCKED: no native mlpstorage command"
        source_command = (
            "\n".join(native_commands)
            if native_commands
            else "# BLOCKED: no native mlpstorage command: " + native["reason"]
        )
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
            "tool": tool,
            "purpose": matrix[2],
            "steps": _steps(matrix[3]),
            "duration": matrix[4],
            "source_command": source_command,
            "workbook_command": workbook_command,
            "native_status": native["status"],
            "native_block_reason": native.get("reason") if native["status"] == "BLOCKED" else None,
            "native_commands": native["commands"],
            "standard": matrix[6],
        })
    return catalog


def _filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


def _entrypoint(case: dict[str, Any]) -> str:
    commands = case["native_commands"]
    status = case["native_status"]
    reason = case["native_block_reason"] or case["tool"]
    template = r'''"""FULL_TEST_PLAN Case __CASE_NO__: __CASE_ID__.

The command list below is the native mlpstorage command for this case.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


CASE_ID = __CASE_ID_REPR__
NATIVE_STATUS = __NATIVE_STATUS_REPR__
NATIVE_REASON = __NATIVE_REASON_REPR__
COMMANDS = __COMMANDS_REPR__


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{CASE_ID} direct mlpstorage case")
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"), default="plan")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DUT_DATA", "data")))
    parser.add_argument("--results-dir", type=Path, default=Path(os.environ.get("MLPERF_RESULTS_DIR", "results")))
    parser.add_argument("--mlpstorage", type=Path)
    parser.add_argument("--launcher", choices=("single", "mpi"), default="single")
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--systemname", default=None)
    parser.add_argument("--client-memory-gb", type=int, default=64)
    parser.add_argument("--accelerators", type=int, default=1)
    parser.add_argument("--query-processes", type=int, default=1)
    parser.add_argument("--duration-sec", type=int, default=60)
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--dlio-bin-path", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--o-direct", action="store_true")
    parser.add_argument("--confirm-dut", action="store_true")
    parser.add_argument("--init-results", action="store_true")
    parser.add_argument("--cleanup-data", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    args = parser.parse_args()

    if NATIVE_STATUS != "SUPPORTED":
        print(f"{CASE_ID} BLOCKED: no native mlpstorage command: {NATIVE_REASON}")
        return 2
    cli = args.mlpstorage
    if cli is None:
        for candidate in (Path(sys.executable).with_name("mlpstorage.exe"), Path(sys.executable).with_name("mlpstorage")):
            if candidate.is_file():
                cli = candidate
                break
    if cli is None:
        cli = Path(shutil.which("mlpstorage") or "mlpstorage")
    selected = [item for item in COMMANDS if args.prepare or item["phase"] != "prepare"]
    values = {
        "<DATA_DIR>": str(args.data_dir.resolve()),
        "<RESULTS_DIR>": str(args.results_dir.resolve()),
        "<CHECKPOINT_DIR>": str(args.data_dir.resolve() / "checkpoint" / CASE_ID),
        "<CACHE_DIR>": str(args.data_dir.resolve() / "kvcache" / CASE_ID),
        "<STORAGE_ROOT>": str(args.data_dir.resolve() / "milvus" / CASE_ID),
        "<SYSTEMNAME>": args.systemname or f"{CASE_ID.lower()}-native",
        "<CLIENT_MEMORY_GB>": str(args.client_memory_gb),
        "<ACCELERATORS>": str(args.accelerators),
        "<QUERY_PROCESSES>": str(args.query_processes),
        "<DURATION_SEC>": str(args.duration_sec),
        "<LOOPS>": str(args.loops),
        "<MPI_BIN>": args.mpi_bin,
    }
    if args.mode == "execute" and not args.confirm_dut:
        print(f"{CASE_ID} BLOCKED: execute requires --confirm-dut")
        return 2
    if args.cleanup_data and args.cleanup_root is None:
        print(f"{CASE_ID} BLOCKED: --cleanup-data requires --cleanup-root")
        return 2

    def finalize(code: int) -> int:
        if not args.cleanup_data:
            return code
        data_path = args.data_dir.resolve()
        root_path = args.cleanup_root.resolve()
        if data_path == root_path or root_path not in data_path.parents:
            print(f"{CASE_ID} CLEANUP_FAILED: data path is outside cleanup root")
            return 1
        try:
            if data_path.exists():
                shutil.rmtree(data_path)
            print(f"TEST_DATA_ROOT={data_path}")
            print(f"TEST_DATA_CLEANED={not data_path.exists()}")
            return code if not data_path.exists() else 1
        except OSError as error:
            print(f"{CASE_ID} CLEANUP_FAILED: {error}")
            return 1

    if args.init_results and args.mode in {"preflight", "dry-run", "execute"}:
        args.results_dir.parent.mkdir(parents=True, exist_ok=True)
        init_command = [str(cli), "init", args.systemname or f"{CASE_ID.lower()}-native", str(args.results_dir.resolve())]
        print(f"{CASE_ID} init: {subprocess.list2cmdline(['mlpstorage', *init_command[1:]])}")
        if args.mode == "execute":
            initialized = subprocess.run(init_command, check=False)
            if initialized.returncode != 0:
                return finalize(initialized.returncode)
    for item in selected:
        command = [str(cli), *[values.get(arg, arg) for arg in item["argv"] if arg != "<COMMAND>"]]
        if args.o_direct and ("training" in command or "checkpointing" in command) and "--o-direct" not in command:
            command.append("--o-direct")
        if args.dlio_bin_path and ("training" in command or "checkpointing" in command):
            command.extend(["--dlio-bin-path", str(args.dlio_bin_path)])
        if args.launcher == "single" and args.mode in {"preflight", "dry-run", "execute"} and "checkpointing" in command and "--num-processes" in command:
            ranks = int(command[command.index("--num-processes") + 1])
            if ranks > 1:
                print(f"{CASE_ID} BLOCKED: checkpointing rank case requires --launcher mpi (requested {ranks} ranks)")
                return finalize(2)
        print(f"{CASE_ID} {item['phase']}: {subprocess.list2cmdline(['mlpstorage', *command[1:]])}")
        if args.mode in {"plan", "preflight"}:
            continue
        if args.mode == "dry-run":
            command.append("--dry-run")
        try:
            completed = subprocess.run(command, check=False)
        except OSError as error:
            print(f"{CASE_ID} FAIL phase={item['phase']}: {error}")
            return finalize(1)
        if completed.returncode != 0:
            print(f"{CASE_ID} FAIL phase={item['phase']} rc={completed.returncode}")
            return finalize(completed.returncode)
    if args.mode == "preflight" and not cli.is_file() and shutil.which(str(cli)) is None:
        print(f"{CASE_ID} BLOCKED: mlpstorage executable not found: {cli}")
        return 2
    if args.mode == "dry-run":
        print(f"{CASE_ID} DRY_RUN (not a workload PASS)")
        return 3
    if args.mode == "execute":
        print(f"{CASE_ID} PASS")
    return finalize(0)


if __name__ == "__main__":
    raise SystemExit(main())
'''
    return (
        template.replace("__CASE_NO__", f"{case['case_no']:03d}")
        .replace("__CASE_ID__", case["case_id"])
        .replace("__CASE_ID_REPR__", repr(case["case_id"]))
        .replace("__NATIVE_STATUS_REPR__", repr(status))
        .replace("__NATIVE_REASON_REPR__", repr(reason))
        .replace("__COMMANDS_REPR__", repr(commands))
    )


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
    expected_files = {_filename(case["case_id"]) for case in catalog}
    for stale in cases_dir.glob("test_*.py"):
        if stale.name not in expected_files:
            stale.unlink()
    for case in catalog:
        (cases_dir / _filename(case["case_id"])).write_text(_entrypoint(case), encoding="utf-8")
    print(f"generated {len(catalog)} FULL_TEST_PLAN scripts in {cases_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
