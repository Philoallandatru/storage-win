"""AI-TRN-012 · flux_b200_parquet_large_object

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
    "case_id": "AI-TRN-012",
    "category": "training",
    "case_name": "flux_b200_parquet_large_object",
    "config": "Flux/B200 Parquet，threads 4/8/16",
    "purpose": "验证大 Parquet 对象的持续读取带宽。",
    "steps": [
        "准备 Flux/B200 Parquet，threads 4/8/16 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、GiB/s、P99、温度、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_training_flux_b200_parquet_large_object.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；GiB/s 达标；吞吐无持续下降；空间余量安全。",
    "metrics": "GiB/s、P99、温度、AU",
    "mode": "sequential"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
