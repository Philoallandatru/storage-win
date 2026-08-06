"""AI-VDB-004 · diskann_1m_512

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
    "case_id": "AI-VDB-004",
    "category": "vdb",
    "case_name": "diskann_1m_512",
    "config": "1M×512 DISKANN，和 1536 维对照",
    "purpose": "量化向量维度变化对查询字节和 QPS 的影响。",
    "steps": [
        "准备 1M×512 DISKANN，和 1536 维对照 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 bytes/query、QPS、Recall，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_diskann_1m_512.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：两种维度同 Recall 门槛；bytes/query 变化可解释；无索引错配。",
    "metrics": "bytes/query、QPS、Recall",
    "mode": "vdb",
    "dimensions": 512
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
