"""AI-CKP-006 · 1t_subset

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
    "case_id": "AI-CKP-006",
    "category": "checkpoint",
    "case_name": "1t_subset",
    "config": "1T subset，8 ranks，161 GB/checkpoint",
    "purpose": "验证最大单节点分片的突发写入和恢复。",
    "steps": [
        "准备 1T subset，8 ranks，161 GB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、burst、GC、恢复时间 和恢复时间。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_checkpoint_1t_subset.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：突发写入完成；fsync 和 hash 通过；恢复时间达到目标；无持续 GC 异常。",
    "metrics": "burst、GC、恢复时间",
    "mode": "checkpoint",
    "shards": 8
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
