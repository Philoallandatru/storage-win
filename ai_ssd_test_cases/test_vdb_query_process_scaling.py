"""AI-VDB-010 · query_process_scaling

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
    "case_id": "AI-VDB-010",
    "category": "vdb",
    "case_name": "query_process_scaling",
    "config": "query process 1/2/4/8/16",
    "purpose": "定位查询并发的饱和点和队列拐点。",
    "steps": [
        "准备 query process 1/2/4/8/16 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 aggregate QPS、queue、P99、CPU，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_query_process_scaling.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：最大合格进程数明确；队列拐点可定位；Recall 不下降。",
    "metrics": "aggregate QPS、queue、P99、CPU",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
