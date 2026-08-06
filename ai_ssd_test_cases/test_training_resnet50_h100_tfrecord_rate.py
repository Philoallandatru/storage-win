"""AI-TRN-009 · resnet50_h100_tfrecord_rate

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
    "case_id": "AI-TRN-009",
    "category": "training",
    "case_name": "resnet50_h100_tfrecord_rate",
    "config": "ResNet50/H100 TFRecord，accelerator 1/2/4/8",
    "purpose": "验证更高 TFRecord 供给速率下的持续吞吐。",
    "steps": [
        "准备 ResNet50/H100 TFRecord，accelerator 1/2/4/8 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、throughput、P99、queue、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_resnet50_h100_tfrecord_rate.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；throughput 无持续下降；无供数中断。",
    "metrics": "throughput、P99、queue、AU",
    "mode": "record"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
