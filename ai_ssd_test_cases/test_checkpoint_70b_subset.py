"""AI-CKP-002 · 70b_subset

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
    "case_id": "AI-CKP-002",
    "category": "checkpoint",
    "case_name": "70b_subset",
    "config": "70B subset，8 ranks，114 GB/checkpoint",
    "purpose": "验证单盘模拟 70B 分片的写入和恢复。",
    "steps": [
        "准备 70B subset，8 ranks，114 GB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、最慢 rank、最小吞吐、hash 和恢复时间。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_checkpoint_70b_subset.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：每个 rank 完成；字节数符合配置；hash 一致；无空间或写入错误。",
    "metrics": "最慢 rank、最小吞吐、hash",
    "mode": "checkpoint",
    "shards": 8
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
