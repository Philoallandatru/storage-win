"""AI-VDB-006 · hnsw_10m

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
    "case_id": "AI-VDB-006",
    "category": "vdb",
    "case_name": "hnsw_10m",
    "config": "10M×1536 HNSW，10 shards，query proc 1/4/8",
    "purpose": "验证大数据集 HNSW 的加载、扩展和 P99。",
    "steps": [
        "准备 10M×1536 HNSW，10 shards，query proc 1/4/8 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 scale、load time、P99、QPS，确认结果可复现。"
    ],
    "test_duration": "约 4–8 小时",
    "command": "python ai_ssd_test_cases/test_vdb_hnsw_10m.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：10 shards 可加载；query proc 变化可解释；无容器重启或数据缺失。",
    "metrics": "scale、load time、P99、QPS",
    "mode": "vdb",
    "dimensions": 1536
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
