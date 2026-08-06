"""AI-BASE-004 · fill_level_degradation

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
    "case_id": "AI-BASE-004",
    "category": "base",
    "case_name": "fill_level_degradation",
    "config": "Q1/X / 20、50、80、90% fill",
    "purpose": "观察 SSD 填充率升高后的性能退化曲线。",
    "steps": [
        "确认 DUT、数据盘和结果盘映射，记录 Q1/X / 20、50、80、90% fill。",
        "采集测试前容量、健康状态和 Windows PhysicalDisk 基线。",
        "按本 Case 的路径或填充率条件运行，重复记录实际读写。",
        "对照 吞吐、IOPS、P99、队列，确认路径、容量和性能变化可解释。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_base_fill_level_degradation.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：输出各填充率结果；不得覆盖未授权目录；退化趋势和瓶颈可解释。",
    "metrics": "吞吐、IOPS、P99、队列",
    "mode": "base"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
