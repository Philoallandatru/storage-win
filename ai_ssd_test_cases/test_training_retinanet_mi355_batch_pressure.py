"""AI-TRN-005 · retinanet_mi355_batch_pressure

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
    "case_id": "AI-TRN-005",
    "category": "training",
    "case_name": "retinanet_mi355_batch_pressure",
    "config": "RetinaNet/MI355 JPEG，batch/compute sweep",
    "purpose": "验证 batch 和处理节奏变化下的小文件供给稳定性。",
    "steps": [
        "准备 RetinaNet/MI355 JPEG，batch/compute sweep 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、files/s、P99、等待时间、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_training_retinanet_mi355_batch_pressure.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥85%；不同 batch 结果可重复；files/s 无持续下降。",
    "metrics": "files/s、P99、等待时间、AU",
    "mode": "small_file"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
