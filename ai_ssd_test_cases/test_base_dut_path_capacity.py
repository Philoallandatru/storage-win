"""AI-BASE-001 · dut_path_capacity

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
    "case_id": "AI-BASE-001",
    "category": "base",
    "case_name": "dut_path_capacity",
    "config": "S0 / 4 块盘 / 卷映射",
    "purpose": "建立 DUT、数据盘和结果盘的可追踪基线。",
    "steps": [
        "确认 DUT、数据盘和结果盘映射，记录 S0 / 4 块盘 / 卷映射。",
        "采集测试前容量、健康状态和 Windows PhysicalDisk 基线。",
        "按本 Case 的路径或填充率条件运行，重复记录实际读写。",
        "对照 路径映射、容量、健康状态，确认路径、容量和性能变化可解释。"
    ],
    "test_duration": "约 20–30 分钟",
    "command": "python ai_ssd_test_cases/test_base_dut_path_capacity.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：DUT、data、result 路径映射正确；结果目录不在 DUT；容量和序列号可追溯。",
    "metrics": "路径映射、容量、健康状态",
    "mode": "base"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
