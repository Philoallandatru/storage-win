"""AI-MIX-003 · vdb_search_ingest

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
    "case_id": "AI-MIX-003",
    "category": "mixed",
    "case_name": "vdb_search_ingest",
    "config": "前台 VectorDB search，后台 ingest/index",
    "purpose": "验证 RAG 在线查询对后台建库的容忍度。",
    "steps": [
        "分别完成前台和后台 前台 VectorDB search，后台 ingest/index 的单项基线。",
        "同时启动前台/后台负载，固定到达节奏并记录 UTC 时间线。",
        "重复运行并采集前台尾延迟、后台吞吐、队列和错误。",
        "对照单项基线，判断 Recall、foreground P99、ingest rate 是否满足通过门槛。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_mixed_vdb_search_ingest.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：Recall 不降；前台 P99≤1.5×solo 且满足 SLA；后台 ingest 可完成。",
    "metrics": "Recall、foreground P99、ingest rate",
    "mode": "mixed",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
