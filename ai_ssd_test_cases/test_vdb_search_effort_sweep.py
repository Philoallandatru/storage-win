"""AI-VDB-009 · search_effort_sweep

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
    "case_id": "AI-VDB-009",
    "category": "vdb",
    "case_name": "search_effort_sweep",
    "config": "ef/search-list 32→512",
    "purpose": "绘制搜索努力度与精度、性能的关系。",
    "steps": [
        "准备 ef/search-list 32→512 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、QPS、P99、search effort，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_search_effort_sweep.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：参数阶梯完整；Recall 单调性和 QPS/P99 变化可解释。",
    "metrics": "Recall、QPS、P99、search effort",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
