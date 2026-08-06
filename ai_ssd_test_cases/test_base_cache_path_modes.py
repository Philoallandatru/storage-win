"""AI-BASE-002 · cache_path_modes

Generated from docs/AI_SSD_TEST_PLAN.xlsx.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai_ssd_test_cases.runner_support import execute_case

CASE_SPEC = {
    "case_id": "AI-BASE-002",
    "category": "base",
    "case_name": "cache_path_modes",
    "config": "Q1 / Buffered、cold、Direct",
    "purpose": "区分缓冲、冷缓存和直接访问对结果的影响。",
    "steps": [
        "确认 DUT、数据盘和结果盘映射，记录 Q1 / Buffered、cold、Direct。",
        "采集测试前容量、健康状态和 Windows PhysicalDisk 基线。",
        "按本 Case 的路径或填充率条件运行，重复记录实际读写。",
        "对照 PhysicalDisk 实际读字节、吞吐、P99，确认路径、容量和性能变化可解释。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_base_cache_path_modes.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：三种路径独立完成；cold/direct 的实际读字节可解释；不混报 warm-only 结果。",
    "metrics": "PhysicalDisk 实际读字节、吞吐、P99",
    "mode": "base"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
