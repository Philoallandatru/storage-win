"""AI-CKP-005 · 405b_full_shared

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
    "case_id": "AI-CKP-005",
    "category": "checkpoint",
    "case_name": "405b_full_shared",
    "config": "405B full，512 ranks，5.29 TB/checkpoint",
    "purpose": "验证 TB 级 shared storage 的并发 checkpoint 扩展。",
    "steps": [
        "准备 405B full，512 ranks，5.29 TB/checkpoint 对应的 checkpoint 分片和容量余量。",
        "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
        "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
        "校验 10 次保存/读取、完整性、scale、最慢 rank、global duration 和恢复时间。"
    ],
    "test_duration": "约 4–8 小时",
    "command": "python ai_ssd_test_cases/test_checkpoint_405b_full_shared.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：512 ranks 均完成；无丢分片；skew、吞吐和容量变化可解释。",
    "metrics": "scale、最慢 rank、global duration",
    "mode": "checkpoint",
    "shards": 512
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
