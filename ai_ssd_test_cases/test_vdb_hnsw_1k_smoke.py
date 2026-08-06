"""AI-VDB-001 · hnsw_1k_smoke

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
    "case_id": "AI-VDB-001",
    "category": "vdb",
    "case_name": "hnsw_1k_smoke",
    "config": "1K×128 HNSW，planted query，L2",
    "purpose": "完成 Windows smoke 并验证 trace 完整性。",
    "steps": [
        "准备 1K×128 HNSW，planted query，L2 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、QPS、trace 完整性，确认结果可复现。"
    ],
    "test_duration": "约 20–30 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_hnsw_1k_smoke.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：Recall 达标；QPS 可记录；trace、索引和结果文件完整。",
    "metrics": "Recall、QPS、trace 完整性",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
