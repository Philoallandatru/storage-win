"""AI-TRN-016 · cache_path_matrix

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
    "case_id": "AI-TRN-016",
    "category": "training",
    "case_name": "cache_path_matrix",
    "config": "warm/cold/--o-direct",
    "purpose": "量化缓存污染对训练结果的影响。",
    "steps": [
        "准备 warm/cold/--o-direct 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、PhysicalDisk 实际读字节、吞吐、AU、P99、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_training_cache_path_matrix.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：三种路径独立可复现；cold/direct 实际读字节与逻辑量一致；AU 差异可解释。",
    "metrics": "PhysicalDisk 实际读字节、吞吐、AU、P99",
    "mode": "cache_matrix"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
