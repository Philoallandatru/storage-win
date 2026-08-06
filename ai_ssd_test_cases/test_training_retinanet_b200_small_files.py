"""AI-TRN-004 · retinanet_b200_small_files

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
    "case_id": "AI-TRN-004",
    "category": "training",
    "case_name": "retinanet_b200_small_files",
    "config": "RetinaNet/B200 JPEG，accelerator 1/4/8/16",
    "purpose": "验证百万级 JPEG 小文件的元数据和 IOPS 能力。",
    "steps": [
        "准备 RetinaNet/B200 JPEG，accelerator 1/4/8/16 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、files/s、IOPS、P99、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_training_retinanet_b200_small_files.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥85%；files/s 达标；P99 无异常尖峰；无缺文件。",
    "metrics": "files/s、IOPS、P99、AU",
    "mode": "small_file"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
