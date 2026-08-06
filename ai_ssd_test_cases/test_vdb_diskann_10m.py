"""AI-VDB-007 · diskann_10m

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
    "case_id": "AI-VDB-007",
    "category": "vdb",
    "case_name": "diskann_10m",
    "config": "10M×1536 DISKANN，10 shards",
    "purpose": "验证大磁盘型索引的 QPS、物理 I/O 和温度。",
    "steps": [
        "准备 10M×1536 DISKANN，10 shards 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 QPS、physical IO、temperature、Recall，确认结果可复现。"
    ],
    "test_duration": "约 4–8 小时",
    "command": "python ai_ssd_test_cases/test_vdb_diskann_10m.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：Recall 达标；physical IO 命中 DUT；温度和空间余量安全。",
    "metrics": "QPS、physical IO、temperature、Recall",
    "mode": "vdb",
    "dimensions": 1536
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
