"""AI-VDB-008 · index_family_sweep

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
    "case_id": "AI-VDB-008",
    "category": "vdb",
    "case_name": "index_family_sweep",
    "config": "DISKANN/HNSW/AISAQ/IVF/FLAT 六类 index",
    "purpose": "在相同 Recall 门槛下比较索引家族。",
    "steps": [
        "准备 DISKANN/HNSW/AISAQ/IVF/FLAT 六类 index 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、QPS、容量、P99，确认结果可复现。"
    ],
    "test_duration": "约 4–8 小时",
    "command": "python ai_ssd_test_cases/test_vdb_index_family_sweep.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：所有支持的 index 均记录版本；同 Recall 下比较；不支持项明确标注。",
    "metrics": "Recall、QPS、容量、P99",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
