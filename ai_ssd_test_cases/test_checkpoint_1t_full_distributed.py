"""AI-CKP-007 · 1t_full_distributed

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
    "case_id": "AI-CKP-007",
    "category": "checkpoint",
    "case_name": "1t_full_distributed",
    "config": "1T full，1024 ranks，18 TB/checkpoint",
    "purpose": "验证极大模型 checkpoint 的全局保存和恢复。",
    "steps": [
        "准备 1T full，1024 ranks，18 TB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、global save/load、rank skew 和恢复时间。"
    ],
    "test_duration": "约 8–12 小时",
    "command": "python ai_ssd_test_cases/test_checkpoint_1t_full_distributed.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：1024 ranks 全部完成；global save/load 可重跑；无损坏、缺 rank 或容量越界。",
    "metrics": "global save/load、rank skew",
    "mode": "checkpoint",
    "shards": 1024
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
