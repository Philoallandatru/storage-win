"""AI-CKP-003 · 70b_full_distributed

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
    "case_id": "AI-CKP-003",
    "category": "checkpoint",
    "case_name": "70b_full_distributed",
    "config": "70B full，64 ranks，912 GB/checkpoint",
    "purpose": "验证多节点并发写入和恢复的 rank skew。",
    "steps": [
        "准备 70B full，64 ranks，912 GB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、rank skew、global duration、吞吐 和恢复时间。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_checkpoint_70b_full_distributed.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：所有 rank 完成；global duration 和 skew 可解释；无丢分片或损坏。",
    "metrics": "rank skew、global duration、吞吐",
    "mode": "checkpoint",
    "shards": 64
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
