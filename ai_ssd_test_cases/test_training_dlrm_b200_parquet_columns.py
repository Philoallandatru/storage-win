"""AI-TRN-010 · dlrm_b200_parquet_columns

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
    "case_id": "AI-TRN-010",
    "category": "training",
    "case_name": "dlrm_b200_parquet_columns",
    "config": "DLRM/B200 Parquet，prefetch 0/2/4",
    "purpose": "验证 Parquet 行组和列裁剪读取表现。",
    "steps": [
        "准备 DLRM/B200 Parquet，prefetch 0/2/4 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、row-groups/s、带宽、P99、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_dlrm_b200_parquet_columns.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥70%；row-groups/s 达标；无异常读放大；CPU 不成为主瓶颈。",
    "metrics": "row-groups/s、带宽、P99、AU",
    "mode": "columnar",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
