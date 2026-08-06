"""AI-TRN-011 · dlrm_mi355_parquet_parallel

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
    "case_id": "AI-TRN-011",
    "category": "training",
    "case_name": "dlrm_mi355_parquet_parallel",
    "config": "DLRM/MI355 Parquet，threads 1/4/8/16",
    "purpose": "验证 Parquet 并行读取带宽和主机开销。",
    "steps": [
        "准备 DLRM/MI355 Parquet，threads 1/4/8/16 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、read BW、CPU、P99、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_dlrm_mi355_parquet_parallel.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU 达标；read BW 随线程变化可解释；CPU、队列和 P99 无异常。",
    "metrics": "read BW、CPU、P99、AU",
    "mode": "columnar",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
