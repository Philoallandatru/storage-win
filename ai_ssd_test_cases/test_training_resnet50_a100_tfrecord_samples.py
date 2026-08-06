"""AI-TRN-008 · resnet50_a100_tfrecord_samples

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
    "case_id": "AI-TRN-008",
    "category": "training",
    "case_name": "resnet50_a100_tfrecord_samples",
    "config": "ResNet50/A100 TFRecord，固定 batch/threads",
    "purpose": "验证 TFRecord 文件内多 sample 读取效率。",
    "steps": [
        "准备 ResNet50/A100 TFRecord，固定 batch/threads 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、samples/s、吞吐、P99、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_training_resnet50_a100_tfrecord_samples.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；samples/s 达标；batch 结果稳定；无读取错误。",
    "metrics": "samples/s、吞吐、P99、AU",
    "mode": "record"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
