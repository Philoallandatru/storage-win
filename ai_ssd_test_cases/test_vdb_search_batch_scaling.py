"""AI-VDB-011 · search_batch_scaling

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
    "case_id": "AI-VDB-011",
    "category": "vdb",
    "case_name": "search_batch_scaling",
    "config": "batch 1/8/32/64",
    "purpose": "验证批查询对 QPS 和单查询尾延迟的影响。",
    "steps": [
        "准备 batch 1/8/32/64 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 QPS、per-query P99、Recall，确认结果可复现。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_search_batch_scaling.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：四档 batch 完成；per-query P99 不被 aggregate QPS 掩盖；Recall 达标。",
    "metrics": "QPS、per-query P99、Recall",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
