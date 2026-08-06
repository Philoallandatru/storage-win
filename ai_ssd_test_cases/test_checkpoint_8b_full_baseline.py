"""AI-CKP-001 · 8b_full_baseline

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
    "case_id": "AI-CKP-001",
    "category": "checkpoint",
    "case_name": "8b_full_baseline",
    "config": "8B full，8 ranks，105 GB/checkpoint",
    "purpose": "建立单节点 8B checkpoint 写入和恢复基线。",
    "steps": [
        "准备 8B full，8 ranks，105 GB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、10 save/load、fsync、cold read 和恢复时间。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_checkpoint_8b_full_baseline.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：10 次保存和读取完成；所有分片完整；fsync 成功；最慢 rank 可追溯。",
    "metrics": "10 save/load、fsync、cold read",
    "mode": "checkpoint",
    "shards": 8
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
