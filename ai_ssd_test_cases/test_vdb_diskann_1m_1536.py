"""AI-VDB-003 · diskann_1m_1536

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
    "case_id": "AI-VDB-003",
    "category": "vdb",
    "case_name": "diskann_1m_1536",
    "config": "1M×1536 DISKANN，degree64",
    "purpose": "建立磁盘 ANN 的搜索和实际读基线。",
    "steps": [
        "准备 1M×1536 DISKANN，degree64 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、QPS、physical read、P99，确认结果可复现。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_vdb_diskann_1m_1536.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：Recall 达标；physical read 命中 DUT；QPS/P99 可重跑。",
    "metrics": "Recall、QPS、physical read、P99",
    "mode": "vdb",
    "dimensions": 1536
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
