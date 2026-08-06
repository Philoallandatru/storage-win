"""AI-VDB-012 · ingest_tuning

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
    "case_id": "AI-VDB-012",
    "category": "vdb",
    "case_name": "ingest_tuning",
    "config": "batch 1K/10K，compact on/off",
    "purpose": "验证写入批次和 compact 对建索引效率的影响。",
    "steps": [
        "准备 batch 1K/10K，compact on/off 的向量、索引和固定 planted query。",
        "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
        "记录 Recall、QPS、P99、实际读写、容量和温度。",
        "在相同 Recall 门槛下比较 vectors/s、flush/index time、写放大，确认结果可复现。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_vdb_ingest_tuning.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：四种组合结果完整；无丢向量；flush/index 时间和写放大可解释。",
    "metrics": "vectors/s、flush/index time、写放大",
    "mode": "vdb",
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
