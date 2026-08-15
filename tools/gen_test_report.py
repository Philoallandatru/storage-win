#!/usr/bin/env python
"""gen_test_report.py — generate the data-driven AI SSD test report.

Collects every scenario's run data (suite_summary_*.json written by
``run_ai_ssd_suite.py``) plus per-case key metrics harvested from the
benchmark results directories, and renders a self-contained, styled HTML
report (default) or the legacy Markdown report.

Usage:
    python tools/gen_test_report.py [--results-root E:\\MLPerfStorageTest]
    python tools/gen_test_report.py --format md    # legacy Markdown
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_RESULTS_ROOT = Path("E:/MLPerfStorageTest")
OUT_HTML = REPO / "docs" / "AI_SSD_TEST_REPORT.html"
OUT_MD = REPO / "docs" / "AI_SSD_TEST_REPORT.md"

FAMILIES = ("Training", "Checkpoint", "KV Cache", "VectorDB", "MIX")

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
    "MIX": [
        ("KV p95_ms", "p95_latency_ms", float), ("KV tokens/s", "tokens_per_second", float),
        ("VDB QPS", "throughput_qps", float), ("VDB recall@k", "recall_at_k", float),
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


def _flatten(scenarios: list[dict]) -> list[dict]:
    """Flatten scenario results into per-case rows with capacity/memory."""
    all_rows = []
    for scen in scenarios:
        cap = scen.get("capacity", "?")
        mem = scen.get("memory", "?")
        for r in scen.get("results", []):
            r = dict(r)
            r["capacity"] = cap
            r["memory"] = mem
            all_rows.append(r)
    return all_rows


def _totals(all_rows: list[dict]) -> tuple[int, int, int, int]:
    total = len(all_rows)
    passed = sum(1 for r in all_rows if r.get("result") == "PASS")
    skipped = sum(1 for r in all_rows if r.get("result") == "SKIP")
    failed = total - passed - skipped
    return total, passed, failed, skipped


# ---------------------------------------------------------------------------
# HTML rendering (self-contained, styled, no external assets)
# ---------------------------------------------------------------------------

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 0;
       background: #f4f6f9; color: #1f2937; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 28px 20px 64px; }
header { background: linear-gradient(135deg, #1e3a8a, #2563eb);
         color: #fff; border-radius: 14px; padding: 26px 30px; margin-bottom: 24px;
         box-shadow: 0 4px 18px rgba(30,58,138,.25); }
header h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: .5px; }
header .sub { opacity: .92; font-size: 14px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
         gap: 14px; margin-bottom: 26px; }
.card { background: #fff; border-radius: 12px; padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,.06); border-top: 4px solid #94a3b8; }
.card .num { font-size: 30px; font-weight: 700; line-height: 1.1; }
.card .lbl { font-size: 13px; color: #64748b; margin-top: 4px; }
.card.pass { border-top-color: #22c55e; } .card.pass .num { color: #15803d; }
.card.fail { border-top-color: #ef4444; } .card.fail .num { color: #b91c1c; }
.card.skip { border-top-color: #94a3b8; } .card.skip .num { color: #475569; }
.card.total { border-top-color: #2563eb; } .card.total .num { color: #1d4ed8; }
.card.rate { border-top-color: #a855f7; } .card.rate .num { color: #7e22ce; }
section { background: #fff; border-radius: 12px; padding: 22px 24px; margin-bottom: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,.06); }
section h2 { margin: 0 0 16px; font-size: 18px; color: #111827; border-left: 4px solid #2563eb;
             padding-left: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th, td { padding: 9px 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }
th { background: #f8fafc; color: #475569; font-weight: 600; white-space: nowrap; }
tbody tr:hover { background: #f8fafc; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px;
         font-weight: 600; color: #fff; }
.badge.PASS { background: #22c55e; } .badge.FAIL { background: #ef4444; }
.badge.SKIP { background: #94a3b8; } .badge.TIMEOUT { background: #f59e0b; }
.fam-tag { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px;
           background: #eef2ff; color: #4338ca; font-weight: 600; }
.bar { height: 10px; border-radius: 5px; background: #e5e7eb; overflow: hidden; margin-top: 6px; }
.bar > span { display: block; height: 100%; border-radius: 5px; }
footer { text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px; }
.mono { font-family: Consolas, monospace; font-size: 12.5px; }
.muted { color: #64748b; }
"""


def _esc(s) -> str:
    return html.escape(str(s))


def _family_rows(all_rows: list[dict], results_root: Path) -> list[tuple[dict, dict]]:
    """Return (row, metrics) pairs sorted by family then case id."""
    out = []
    for r in sorted(all_rows, key=lambda x: (x.get("family", ""), x.get("case_id", ""))):
        cid = r.get("case_id", "?")
        metrics = r.get("metrics") or harvest_metrics(cid, results_root, r.get("family", ""))
        out.append((r, metrics))
    return out


def render_html(scenarios: list[dict], results_root: Path) -> str:
    all_rows = _flatten(scenarios)
    total, passed, failed, skipped = _totals(all_rows)
    rate = passed / total * 100 if total else 0.0
    fam_rows = _family_rows(all_rows, results_root)

    L: list[str] = []
    add = L.append
    add("<!DOCTYPE html>")
    add('<html lang="zh-CN"><head><meta charset="utf-8">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add(f"<title>AI SSD 测试报告</title><style>{_CSS}</style></head><body>")
    add('<div class="wrap">')

    # ---- header ----
    add("<header>")
    add("<h1>AI SSD 测试报告</h1>")
    add(f'<div class="sub">生成：{datetime.now():%Y-%m-%d %H:%M:%S} · '
        f'场景数 {len(scenarios)} · case 运行数 {total} · 由 tools/gen_test_report.py 自动生成</div>')
    add("</header>")

    # ---- summary cards ----
    add('<div class="cards">')
    add(f'<div class="card total"><div class="num">{total}</div><div class="lbl">总 case 数</div></div>')
    add(f'<div class="card pass"><div class="num">{passed}</div><div class="lbl">PASS</div></div>')
    add(f'<div class="card fail"><div class="num">{failed}</div><div class="lbl">FAIL</div></div>')
    add(f'<div class="card skip"><div class="num">{skipped}</div><div class="lbl">SKIP</div></div>')
    add(f'<div class="card rate"><div class="num">{rate:.1f}%</div><div class="lbl">通过率</div></div>')
    add("</div>")

    # ---- scenarios ----
    add("<section><h2>一、环境与场景</h2><table>")
    add("<thead><tr><th>场景文件</th><th>容量档</th><th>内存档</th>"
        "<th>case 数</th><th>PASS</th><th>FAIL</th><th>SKIP</th></tr></thead><tbody>")
    for scen in scenarios:
        rs = scen.get("results", [])
        p = sum(1 for r in rs if r.get("result") == "PASS")
        f = sum(1 for r in rs if r.get("result") == "FAIL")
        s = sum(1 for r in rs if r.get("result") == "SKIP")
        add(f"<tr><td class='mono'>{_esc(scen.get('_file', ''))}</td>"
            f"<td>{_esc(scen.get('capacity', '?'))}</td><td>{_esc(scen.get('memory', '?'))}</td>"
            f"<td>{len(rs)}</td><td>{p}</td><td>{f}</td><td>{s}</td></tr>")
    add("</tbody></table></section>")

    # ---- per-case table ----
    add("<section><h2>二、逐 case 结果与指标</h2>")
    add("<div style='overflow-x:auto'><table>")
    add("<thead><tr><th>Case</th><th>家族</th><th>容量</th><th>内存</th><th>结果</th>"
        "<th>rc</th><th>耗时</th><th>关键指标</th></tr></thead><tbody>")
    for r, metrics in fam_rows:
        res = r.get("result", "?")
        mstr = ", ".join(f"{k}={v}" for k, v in metrics.items()) if metrics else "—"
        add(f"<tr><td class='mono'>{_esc(r.get('case_id', '?'))}</td>"
            f"<td><span class='fam-tag'>{_esc(r.get('family', '?'))}</span></td>"
            f"<td>{_esc(r.get('capacity', '?'))}</td><td>{_esc(r.get('memory', '?'))}</td>"
            f"<td><span class='badge {_esc(res)}'>{_esc(res)}</span></td>"
            f"<td class='mono'>{_esc(r.get('rc', ''))}</td>"
            f"<td>{_esc(r.get('duration', ''))}</td>"
            f"<td class='mono'>{_esc(mstr)}</td></tr>")
    add("</tbody></table></div></section>")

    # ---- per-family summary ----
    add("<section><h2>三、按家族汇总</h2><table>")
    add("<thead><tr><th>家族</th><th>运行</th><th>PASS</th><th>FAIL</th><th>SKIP</th>"
        "<th>平均耗时</th><th>通过率</th></tr></thead><tbody>")
    for fam in FAMILIES:
        fr = [r for r in all_rows if r.get("family") == fam]
        if not fr:
            continue
        p = sum(1 for r in fr if r.get("result") == "PASS")
        f = sum(1 for r in fr if r.get("result") == "FAIL")
        s = sum(1 for r in fr if r.get("result") == "SKIP")
        secs = [int(re.sub(r"\D", "", r.get("duration", "0"))) for r in fr if r.get("duration")]
        avg = sum(secs) / len(secs) / 60 if secs else 0
        fam_rate = p / len(fr) * 100 if fr else 0
        add(f"<tr><td><span class='fam-tag'>{_esc(fam)}</span></td><td>{len(fr)}</td>"
            f"<td>{p}</td><td>{f}</td><td>{s}</td><td>{avg:.1f} min</td>"
            f"<td><div style='min-width:80px'>{fam_rate:.0f}%"
            f"<div class='bar'><span style='width:{fam_rate:.0f}%;background:#22c55e'></span></div></div></td></tr>")
    add("</tbody></table></section>")

    # ---- duration distribution ----
    add("<section><h2>四、时长分布（PASS 的 case）</h2>")
    dur = sorted(int(re.sub(r"\D", "", r.get("duration", "0"))) for r in all_rows
                 if r.get("result") == "PASS" and r.get("duration"))
    if dur:
        add(f"<p>最短 <b>{dur[0]}s</b> · 中位 <b>{dur[len(dur)//2]}s</b> · 最长 <b>{dur[-1]}s</b> · "
            f"总和 <b>{sum(dur)//60}min</b></p>")
        warn = "存在超过 1.5h 的 case" if dur[-1] > 5400 else "所有 PASS case 均在 1.5h 预算内"
        color = "#dc2626" if dur[-1] > 5400 else "#15803d"
        add(f"<p style='color:{color}'>{warn}</p>")
    else:
        add("<p class='muted'>无 PASS case。</p>")
    add("</section>")

    # ---- failures & skips ----
    if failed:
        add("<section><h2>五、失败与跳过</h2><table>")
        add("<thead><tr><th>Case</th><th>场景</th><th>结果</th><th>说明</th></tr></thead><tbody>")
        for r in all_rows:
            if r.get("result") in ("FAIL", "SKIP", "TIMEOUT"):
                note = r.get("note", "")
                add(f"<tr><td class='mono'>{_esc(r.get('case_id', ''))}</td>"
                    f"<td>{_esc(r.get('capacity', '?'))}/{_esc(r.get('memory', '?'))}</td>"
                    f"<td><span class='badge {_esc(r.get('result'))}'>{_esc(r.get('result'))}</span></td>"
                    f"<td>{_esc(note)}</td></tr>")
        add("</tbody></table></section>")

    add(f"<footer>AI SSD 测试报告 · 生成于 {datetime.now():%Y-%m-%d %H:%M:%S}</footer>")
    add("</div></body></html>")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Legacy Markdown rendering
# ---------------------------------------------------------------------------

def render_md(scenarios: list[dict], results_root: Path) -> str:
    all_rows = _flatten(scenarios)
    total, passed, failed, skipped = _totals(all_rows)

    L: list[str] = []
    add = L.append
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
    for r, metrics in _family_rows(all_rows, results_root):
        cid = r.get("case_id", "?")
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
    parser.add_argument("--format", choices=("html", "md"), default="html",
                        help="output format (default html; md = legacy Markdown)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output file path (default docs/AI_SSD_TEST_REPORT.{html,md})")
    args = parser.parse_args()

    scenarios = load_summaries(args.results_root)
    if not scenarios:
        print(f"未找到 suite_summary_*.json（results-root: {args.results_root}）——先运行套件脚本。")
        return 2
    if args.format == "html":
        out = args.out or OUT_HTML
        body = render_html(scenarios, args.results_root)
    else:
        out = args.out or OUT_MD
        body = render_md(scenarios, args.results_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"written: {out} ({out.stat().st_size} bytes, {len(scenarios)} 场景, format={args.format})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
