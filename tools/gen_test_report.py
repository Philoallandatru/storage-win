#!/usr/bin/env python
"""gen_test_report.py — generate the data-driven AI SSD test report.

Collects every scenario's run data (suite_summary_*.json written by
``run_ai_ssd_suite.py``) plus per-case key metrics harvested from the
benchmark results directories, and renders ``docs/AI_SSD_TEST_REPORT.md``.

Usage:
    python tools/gen_test_report.py [--results-root E:\\MLPerfStorageTest]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_RESULTS_ROOT = Path("E:/MLPerfStorageTest")
OUT = REPO / "docs" / "AI_SSD_TEST_REPORT.md"

FAMILIES = ("Training", "Checkpoint", "KV Cache", "VectorDB")

# Key-metric harvesters: probe json files under a case's results dir for these
# keys and report the first hit. (family -> (metric_label, json_key, cast))
_METRIC_SPECS = {
    "Training": [
        ("AU", "au", float), ("throughput_MBs", "throughput_MBs", float),
        ("samples/s", "samples_per_second", float),
    ],
    "Checkpoint": [
        ("save_GBps", "save_ckpt1.throughput", float),
        ("load_GBps", "load_ckpt1.throughput", float),
        ("save_s", "save_ckpt1.duration", float),
    ],
    "KV Cache": [
        ("p95_ms", "p95_latency_ms", float), ("p99_ms", "p99_latency_ms", float),
        ("tokens/s", "tokens_per_second", float),
    ],
    "VectorDB": [
        ("recall@k", "recall_at_k", float), ("QPS", "throughput_qps", float),
        ("total_queries", "total_queries", int),
    ],
}

_DIGITS = re.compile(r"\d+")


def _walk_json(path: Path):
    """Yield (json_path, data) for every *.json under path (skip huge ones)."""
    if not path.exists():
        return
    for jp in sorted(path.rglob("*.json")):
        try:
            if jp.stat().st_size > 20 * 1024 * 1024:
                continue
            yield jp, json.loads(jp.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue


def harvest_metrics(case_id: str, results_root: Path, family: str) -> dict[str, str]:
    """Best-effort extraction of the case's key metrics from its results dir.

    ``results_root`` is the directory that holds ``suite_summary_*.json``;
    per-case benchmark output lives under ``results_root/results/<case_id>``.
    """
    case_dir = results_root / "results" / case_id
    metrics: dict[str, str] = {}
    specs = _METRIC_SPECS.get(family, [])
    if not specs:
        return metrics
    # newest timestamp dir first (sorted descending by path parts)
    for jp, data in _walk_json(case_dir):
        if not isinstance(data, dict):
            continue

        def _find(obj, key):
            """Support dotted keys like 'save_ckpt1.throughput' (recursive)."""
            if key in obj:
                return obj[key]
            if "." in key:
                head, rest = key.split(".", 1)
                if head in obj and isinstance(obj[head], dict):
                    return _find(obj[head], rest)
            for v in obj.values():
                if isinstance(v, dict):
                    r = _find(v, key)
                    if r is not None:
                        return r
            return None

        for label, key, cast in specs:
            if label in metrics:
                continue
            val = _find(data, key)
            if val is not None:
                try:
                    metrics[label] = f"{cast(val):.4g}" if isinstance(cast(val), float) else str(cast(val))
                except (ValueError, TypeError):
                    pass
    return metrics


def load_summaries(results_root: Path) -> list[dict]:
    out = []
    for p in sorted(results_root.glob("suite_summary_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        data["_file"] = p.name
        out.append(data)
    return out


def render(scenarios: list[dict], results_root: Path) -> str:
    L: list[str] = []
    add = L.append

    all_rows = []
    for scen in scenarios:
        cap = scen.get("capacity", "?")
        mem = scen.get("memory", "?")
        for r in scen.get("results", []):
            r = dict(r)
            r["capacity"] = cap
            r["memory"] = mem
            all_rows.append(r)

    total = len(all_rows)
    passed = sum(1 for r in all_rows if r.get("result") == "PASS")
    skipped = sum(1 for r in all_rows if r.get("result") == "SKIP")
    failed = total - passed - skipped

    add("# AI SSD 测试报告（数据驱动）")
    add("")
    add(f"> 生成：{datetime.now():%Y-%m-%d %H:%M:%S} · 由 `tools/gen_test_report.py` 从 "
        f"`suite_summary_*.json` 与 results 目录自动生成")
    add(f"> 场景数：{len(scenarios)} · case 运行数：{total} · **PASS {passed} / FAIL {failed} / SKIP {skipped}**")
    add("")

    add("## 一、环境与场景")
    add("")
    add("| 场景文件 | 容量档 | 内存档 | case 数 | PASS | FAIL | SKIP |")
    add("|---|---|---|---|---|---|---|")
    for scen in scenarios:
        rs = scen.get("results", [])
        p = sum(1 for r in rs if r.get("result") == "PASS")
        f = sum(1 for r in rs if r.get("result") == "FAIL")
        s = sum(1 for r in rs if r.get("result") == "SKIP")
        add(f"| {scen.get('_file','')} | {scen.get('capacity','?')} | {scen.get('memory','?')} | "
            f"{len(rs)} | {p} | {f} | {s} |")
    add("")

    add("## 二、逐 case 结果与指标")
    add("")
    add("| Case | 容量 | 内存 | 家族 | 结果 | rc | 耗时 | 关键指标 |")
    add("|---|---|---|---|---|---|---|---|")
    for r in sorted(all_rows, key=lambda x: (x.get("family", ""), x.get("case_id", ""))):
        cid = r.get("case_id", "?")
        metrics = r.get("metrics") or harvest_metrics(cid, results_root, r.get("family", ""))
        mstr = ", ".join(f"{k}={v}" for k, v in metrics.items()) if metrics else "—"
        add(f"| {cid} | {r.get('capacity','?')} | {r.get('memory','?')} | {r.get('family','?')} | "
            f"{r.get('result','?')} | {r.get('rc','')} | {r.get('duration','')} | {mstr} |")
    add("")

    add("## 三、汇总统计")
    add("")
    add(f"- 总运行：**{total}**（PASS {passed} / FAIL {failed} / SKIP {skipped}，通过率 "
        f"**{passed/total*100:.1f}%**）")
    add("")
    add("### 3.1 按家族")
    add("")
    add("| 家族 | 运行 | PASS | FAIL | SKIP | 平均耗时 |")
    add("|---|---|---|---|---|---|")
    for fam in FAMILIES:
        fr = [r for r in all_rows if r.get("family") == fam]
        if not fr:
            continue
        p = sum(1 for r in fr if r.get("result") == "PASS")
        f = sum(1 for r in fr if r.get("result") == "FAIL")
        s = sum(1 for r in fr if r.get("result") == "SKIP")
        secs = [int(re.sub(r"\D", "", r.get("duration", "0"))) for r in fr if r.get("duration")]
        avg = sum(secs) / len(secs) / 60 if secs else 0
        add(f"| {fam} | {len(fr)} | {p} | {f} | {s} | {avg:.1f} min |")
    add("")

    add("### 3.2 时长分布（PASS 的 case）")
    add("")
    dur = sorted(int(re.sub(r"\D", "", r.get("duration", "0"))) for r in all_rows
                 if r.get("result") == "PASS" and r.get("duration"))
    if dur:
        add(f"- 最短 {dur[0]}s · 中位 {dur[len(dur)//2]}s · 最长 {dur[-1]}s · 总和 {sum(dur)//60}min")
        add("- 所有 PASS case 均 ≤ 1.5h 预算" if dur[-1] <= 5400 else "- ⚠️ 存在超过 1.5h 的 case")
    add("")

    if failed:
        add("## 四、失败与跳过")
        add("")
        add("| Case | 场景 | 结果 | 说明 |")
        add("|---|---|---|---|")
        for r in all_rows:
            if r.get("result") in ("FAIL", "SKIP"):
                note = r.get("note", "")
                add(f"| {r.get('case_id','')} | {r.get('capacity','?')}/{r.get('memory','?')} | "
                    f"{r.get('result','')} | {note} |")
        add("")
    return "\n".join(L)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    args = parser.parse_args()

    scenarios = load_summaries(args.results_root)
    if not scenarios:
        print(f"未找到 suite_summary_*.json（results-root: {args.results_root}）——先运行套件脚本。")
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(scenarios, args.results_root), encoding="utf-8")
    print(f"written: {OUT} ({OUT.stat().st_size} bytes, {len(scenarios)} 场景)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
