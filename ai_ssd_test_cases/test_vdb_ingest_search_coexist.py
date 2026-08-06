"""AI-VDB-016 · ingest_search_coexist

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
    "case_id": "AI-VDB-016",
    "category": "vdb",
    "case_name": "ingest_search_coexist",
    "config": "独立 ingest/query clients",
    "purpose": "评价后台写入和建索引对前台搜索的影响。",
    "steps": [
        "准备 独立 ingest/query clients 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、foreground P99、ingest rate，确认结果可复现。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_vdb_ingest_search_coexist.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：前台 Recall 不降；P99 满足 SLA；后台 ingest rate 和影响可量化。",
    "metrics": "Recall、foreground P99、ingest rate",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
