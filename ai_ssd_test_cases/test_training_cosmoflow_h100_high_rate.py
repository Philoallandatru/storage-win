"""AI-TRN-007 · cosmoflow_h100_high_rate

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
    "case_id": "AI-TRN-007",
    "category": "training",
    "case_name": "cosmoflow_h100_high_rate",
    "config": "CosmoFlow/H100 TFRecord，accelerator 1/2/4/8",
    "purpose": "验证更高请求速率下的随机读取尾延迟。",
    "steps": [
        "准备 CosmoFlow/H100 TFRecord，accelerator 1/2/4/8 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、P99、IOPS、queue、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_cosmoflow_h100_high_rate.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥70%；P99 达标；请求速率提高后无供数中断。",
    "metrics": "P99、IOPS、queue、AU",
    "mode": "shuffle"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
