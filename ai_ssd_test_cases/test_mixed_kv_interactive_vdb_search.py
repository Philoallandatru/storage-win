"""AI-MIX-004 · kv_interactive_vdb_search

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
    "case_id": "AI-MIX-004",
    "category": "mixed",
    "case_name": "kv_interactive_vdb_search",
    "config": "前台 KV interactive + VectorDB search",
    "purpose": "验证两类前台随机读共存时的双 SLA。",
    "steps": [
        "分别完成前台和后台 前台 KV interactive + VectorDB search 的单项基线。",
        "同时启动前台/后台负载，固定到达节奏并记录 UTC 时间线。",
        "重复运行并采集前台尾延迟、后台吞吐、队列和错误。",
        "对照单项基线，判断 KV P99、VDB P99、Recall、QPS 是否满足通过门槛。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_mixed_kv_interactive_vdb_search.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：两类前台 workload 的 SLA 均达标；Recall 不降；无持续队列堆积。",
    "metrics": "KV P99、VDB P99、Recall、QPS",
    "mode": "mixed",
    "users": 50,
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
