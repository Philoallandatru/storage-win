"""AI-VDB-014 · cold_warm_search

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
    "case_id": "AI-VDB-014",
    "category": "vdb",
    "case_name": "cold_warm_search",
    "config": "restart/load、重复 round、search-only",
    "purpose": "区分索引加载、缓存和 steady-state 搜索影响。",
    "steps": [
        "准备 restart/load、重复 round、search-only 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 load time、first P99、steady P99、physical read，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_cold_warm_search.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：cold/warm/search-only 分开；first/steady 结果可重跑；physical read 证据完整。",
    "metrics": "load time、first P99、steady P99、physical read",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
