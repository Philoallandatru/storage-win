"""AI-VDB-015 · logical_trace_replay

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
    "case_id": "AI-VDB-015",
    "category": "vdb",
    "case_name": "logical_trace_replay",
    "config": "both/search-only，1×/2×/4×",
    "purpose": "复现 VectorDB 逻辑 SSD 负载并验证对齐带宽。",
    "steps": [
        "准备 both/search-only，1×/2×/4× 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 aligned BW、P99、trace 覆盖，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_logical_trace_replay.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：trace 版本和过滤范围固定；三种速率完成；aligned BW/P99 可比较。",
    "metrics": "aligned BW、P99、trace 覆盖",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
