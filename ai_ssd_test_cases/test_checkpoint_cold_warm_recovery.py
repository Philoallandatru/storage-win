"""AI-CKP-008 · cold_warm_recovery

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
    "case_id": "AI-CKP-008",
    "category": "checkpoint",
    "case_name": "cold_warm_recovery",
    "config": "write-only→purge/reboot→read-only",
    "purpose": "证明恢复读实际命中 SSD，而不是页缓存。",
    "steps": [
        "准备 write-only→purge/reboot→read-only 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、PhysicalDisk bytes、load time、hash 和恢复时间。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_checkpoint_cold_warm_recovery.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：cold 方法明确；实际物理读字节与逻辑量一致；warm/cold 结果分开报告。",
    "metrics": "PhysicalDisk bytes、load time、hash",
    "mode": "checkpoint",
    "shards": 8
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
