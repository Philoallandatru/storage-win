"""AI-TRN-006 · cosmoflow_a100_shuffle

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
    "case_id": "AI-TRN-006",
    "category": "training",
    "case_name": "cosmoflow_a100_shuffle",
    "config": "CosmoFlow/A100 TFRecord，accelerator 1/2/4",
    "purpose": "验证中小对象随机访问和 shuffle 供数。",
    "steps": [
        "准备 CosmoFlow/A100 TFRecord，accelerator 1/2/4 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、IOPS、P99、queue、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_cosmoflow_a100_shuffle.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥70%；shuffle 无供数空洞；IOPS/P99 达标；数据完整。",
    "metrics": "IOPS、P99、queue、AU",
    "mode": "shuffle"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
