"""AI-BASE-003 · repeatability_monitor_overhead

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
    "case_id": "AI-BASE-003",
    "category": "base",
    "case_name": "repeatability_monitor_overhead",
    "config": "Q1 / 3 runs / monitor off-on",
    "purpose": "验证重复性并量化监控开销。",
    "steps": [
        "确认 DUT、数据盘和结果盘映射，记录 Q1 / 3 runs / monitor off-on。",
        "采集测试前容量、健康状态和 Windows PhysicalDisk 基线。",
        "按本 Case 的路径或填充率条件运行，重复记录实际读写。",
        "对照 吞吐 CV、监控前后差异，确认路径、容量和性能变化可解释。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_base_repeatability_monitor_overhead.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：3 次吞吐 CV≤5%；监控开销≤2%；日志和时间覆盖完整。",
    "metrics": "吞吐 CV、监控前后差异",
    "mode": "base"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
