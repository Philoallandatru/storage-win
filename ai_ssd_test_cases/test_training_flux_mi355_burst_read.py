"""AI-TRN-013 · flux_mi355_burst_read

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
    "case_id": "AI-TRN-013",
    "category": "training",
    "case_name": "flux_mi355_burst_read",
    "config": "Flux/MI355 Parquet，batch 72，threads sweep",
    "purpose": "验证长 compute gap 后突发读取的恢复能力。",
    "steps": [
        "准备 Flux/MI355 Parquet，batch 72，threads sweep 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、burst latency、恢复时间、AU、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_training_flux_mi355_burst_read.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；突发读取在目标窗口内恢复；无供数中断。",
    "metrics": "burst latency、恢复时间、AU",
    "mode": "burst"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
