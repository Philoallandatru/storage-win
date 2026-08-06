"""AI-CKP-009 · interval_burst_gc

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
    "case_id": "AI-CKP-009",
    "category": "checkpoint",
    "case_name": "interval_burst_gc",
    "config": "interval 5/30/300 s，1/2/10 cycles",
    "purpose": "评价连续 checkpoint 和后台 GC 对后续保存的影响。",
    "steps": [
        "准备 interval 5/30/300 s，1/2/10 cycles 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、后续 checkpoint 退化、P99、GC 和恢复时间。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_checkpoint_interval_burst_gc.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：所有 cycle 完成；后续 checkpoint 退化可量化；无持续超过目标的尾延迟。",
    "metrics": "后续 checkpoint 退化、P99、GC",
    "mode": "checkpoint",
    "shards": 8
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
