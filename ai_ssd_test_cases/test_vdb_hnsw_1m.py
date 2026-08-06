"""AI-VDB-002 · hnsw_1m

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
    "case_id": "AI-VDB-002",
    "category": "vdb",
    "case_name": "hnsw_1m",
    "config": "1M×1536 HNSW，M64，ef 32/128/256",
    "purpose": "建立内存图索引的 Recall-QPS-P99 基线。",
    "steps": [
        "准备 1M×1536 HNSW，M64，ef 32/128/256 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、QPS、P99、容量，确认结果可复现。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_vdb_hnsw_1m.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：同一 Recall 门槛下比较；ef 阶梯完整；P99 和容量可追溯。",
    "metrics": "Recall、QPS、P99、容量",
    "mode": "vdb",
    "dimensions": 1536
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
