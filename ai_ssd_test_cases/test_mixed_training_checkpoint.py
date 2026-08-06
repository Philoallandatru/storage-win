"""AI-MIX-001 · training_checkpoint

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
    "case_id": "AI-MIX-001",
    "category": "mixed",
    "case_name": "training_checkpoint",
    "config": "前台 Training，后台 Checkpoint save",
    "purpose": "验证持续读与突发写同盘时的训练和保存窗口。",
    "steps": [
        "分别完成前台和后台 前台 Training，后台 Checkpoint save 的单项基线。",
        "同时启动前台/后台负载，固定到达节奏并记录 UTC 时间线。",
        "重复运行并采集前台尾延迟、后台吞吐、队列和错误。",
        "对照单项基线，判断 AU、checkpoint throughput、foreground P99 是否满足通过门槛。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_mixed_training_checkpoint.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU 达标；checkpoint throughput≥solo 的 0.8×；无数据或分片错误。",
    "metrics": "AU、checkpoint throughput、foreground P99",
    "mode": "mixed"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
