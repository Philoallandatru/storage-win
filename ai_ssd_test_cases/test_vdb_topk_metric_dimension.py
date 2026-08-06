"""AI-VDB-013 · topk_metric_dimension

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
    "case_id": "AI-VDB-013",
    "category": "vdb",
    "case_name": "topk_metric_dimension",
    "config": "K10/100；COSINE/L2/IP；多维度",
    "purpose": "验证查询形状对 Recall、结果字节和延迟的影响。",
    "steps": [
        "准备 K10/100；COSINE/L2/IP；多维度 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 Recall、result bytes、latency、QPS，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_topk_metric_dimension.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：K、metric、dimension 组合完整；Recall 计算口径一致；结果字节可解释。",
    "metrics": "Recall、result bytes、latency、QPS",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
