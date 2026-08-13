#!/usr/bin/env python
"""gen_case_requirements_doc.py — generate the AI SSD case requirements doc.

Reads case_catalog.json (34 base cases) + capacity_catalog.json (1TB/2TB/4TB
tiers) and, when present, the suite summary JSONs written by
``scripts/run_ai_ssd_suite.py``, and renders ``docs/AI_SSD_CASE_REQUIREMENTS.md``
describing what every case tests, how it runs (shrunk on a 512 GB disk), and
its measured result.

Usage:
    python tools/gen_case_requirements_doc.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CATALOG = REPO / "full_test_plan_cases" / "case_catalog.json"
CAPACITY = REPO / "full_test_plan_cases" / "capacity_catalog.json"
SUITE_DIR = Path("E:/MLPerfStorageTest")  # suite summaries land next to results root
OUT = REPO / "docs" / "AI_SSD_CASE_REQUIREMENTS.md"

SHRINK = {
    "Training": "8 files + `--allow-invalid-params`（真实 datagen + 训练）",
    "Checkpoint": "8 ranks + 1 写 / 1 读 + `--allow-invalid-params`（真实 I/O 冒烟；容量档保留 capacity_catalog 的 I/O 量）",
    "KV Cache": "10 users + 10 s + 1 trial + `--generation-mode fast`",
    "VectorDB": "100 vectors + 10 s + `vdb_smoke.yaml` + Milvus Lite",
}


def load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_suite_results() -> dict[str, str]:
    results: dict[str, str] = {}
    # newest summary wins: later runs overwrite earlier (FAIL -> PASS fixups)
    for summary in sorted(SUITE_DIR.glob("suite_summary_*.json"),
                          key=lambda p: p.stat().st_mtime):
        data = json.loads(summary.read_text(encoding="utf-8"))
        for item in data.get("results", []):
            results[item["case_id"]] = item["result"]
    return results


def family_order(case) -> tuple[int, str]:
    fams = {"Training": 0, "Checkpoint": 1, "KV Cache": 2, "VectorDB": 3}
    return (fams.get(case.get("family", ""), 9), case["case_id"])


def render() -> str:
    catalog = load(CATALOG)
    capacity = load(CAPACITY)
    results = load_suite_results()

    L: list[str] = []
    add = L.append
    add("# AI SSD Case 需求文档")
    add("")
    add("> 生成：由 `tools/gen_case_requirements_doc.py` 从 `case_catalog.json` / "
        "`capacity_catalog.json` 生成，实测结果回填自 `run_ai_ssd_suite.py` 的 summary。")
    add("> 数据源唯一入口：`full_test_plan_cases/case_catalog.json`（34 基础 case）+ "
        "`capacity_catalog.json`（1TB/2TB/4TB 容量档）。")
    add("")
    add("## 一、测试体系概述")
    add("")
    add("- 执行引擎：`mlpstorage`（MLPerf Storage Benchmark Suite v3.0）")
    add("- 统一执行器：`full_test_plan_cases/run_case.py`（`run_case.cmd <CASE_ID>`）")
    add("- 批量套件：`scripts/run_ai_ssd_suite.py --capacity <档位> --data-drive X: --results-drive Y:`")
    add("- 四类 workload：Training / Checkpoint / KV Cache / VectorDB")
    add("- **512 GB 磁盘约束**：所有 case 以缩小参数运行（见各家族表），验证执行链路、门禁与指标产出，"
        "不生成真实容量数据；容量档（1TB/2TB/4TB）的完整数据量需对应容量的磁盘。")
    add("")
    add("## 二、Case 需求总表（34 基础 case）")
    add("")
    add("| Case | 家族 | 优先级 | 需求 ID | 测试目的 | 主要变量 | 主要指标 | 实测 |")
    add("|---|---|---|---|---|---|---|---|")
    for case in sorted(catalog, key=family_order):
        reqs = "、".join(case.get("requirements") or [])
        cid = case["case_id"]
        add(f"| {cid} | {case.get('family','')} | {case.get('priority','')} | {reqs} | "
            f"{case.get('test_purpose','')} | {case.get('primary_variables','')} | "
            f"{case.get('primary_metrics','')} | {results.get(cid, '待跑')} |")
    add("")
    add("## 三、各家族测试内容与缩小验证参数")
    add("")
    for family in ("Training", "Checkpoint", "KV Cache", "VectorDB"):
        add(f"### {family}")
        add("")
        add(f"**缩小验证参数**：{SHRINK[family]}")
        add("")
        add("| Case | 测试内容（test_purpose） | 主要指标 |")
        add("|---|---|---|")
        for case in sorted(catalog, key=lambda c: c["case_id"]):
            if case.get("family") == family:
                add(f"| {case['case_id']} | {case.get('test_purpose','')} | {case.get('primary_metrics','')} |")
        add("")
    add("## 四、容量档（1TB / 2TB / 4TB）")
    add("")
    add("容量档 case 以 `case_id` 后缀 `-1TB/-2TB/-4TB` 表示，基于基础 case 叠加容量参数"
        "（见 `capacity_catalog.json`）。512 GB 盘上以缩小参数验证配置解析与执行链路。")
    add("")
    for tier in ("1TB", "2TB", "4TB"):
        body = capacity[tier]
        entries = body.get("cases", body) if isinstance(body, dict) else body
        if isinstance(entries, dict):
            entries = {k: v for k, v in entries.items() if not k.startswith("_")}
        rows = entries if isinstance(entries, list) else [
            {"case_id": k, "base": v.get("base", ""), "overrides": v.get("overrides", [])} for k, v in entries.items()
        ]
        add(f"### {tier}")
        add("")
        add("| Case | 基础 case | 容量覆盖参数 | 实测 |")
        add("|---|---|---|---|")
        for row in rows:
            ov = " ".join(str(x) for x in row.get("overrides", []))
            cid = row["case_id"]
            add(f"| {cid} | {row.get('base','')} | `{ov}` | {results.get(cid, '待跑')} |")
        add("")
    add("## 五、判定标准（Pass / Fail / Invalid）")
    add("")
    add("- **Pass**：达到门禁（如 Training AU ≥ 90% @ declared load）且结果、代码版本 manifest 完整。")
    add("- **Fail**：未达门禁、运行中断或指标回归。")
    add("- **Invalid**：路径/盘符错误、数据缺失、结果目录不在 DUT 上等无法验证 DUT 的情况。")
    add("- 缩小版（dev smoke）**Pass** 仅代表执行链路、门禁与指标产出正常，不代表真实容量下的性能结论。")
    add("")
    add("## 六、运行与清理")
    add("")
    add("- 单 case：`run_case.cmd <CASE_ID> --data-dir X:\\... --results-dir Y:\\...`（可加缩小参数）")
    add("- 批量：`python scripts/run_ai_ssd_suite.py --capacity 512GB --data-drive D: --results-drive E:`")
    add("- 套件每次运行前后自动检查环境（python/mlpstorage/vdbbench/milvus-lite/磁盘空间），")
    add("  每个 case 结束后自动删除数据目录，汇总写入 `suite_summary_<档位>.json`。")
    add("")
    return "\n".join(L)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"written: {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
