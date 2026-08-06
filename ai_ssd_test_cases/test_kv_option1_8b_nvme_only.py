"""AI-KV-001 · option1_8b_nvme_only

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
    "case_id": "AI-KV-001",
    "category": "kv",
    "case_name": "option1_8b_nvme_only",
    "config": "MLPerf option 1，8B，200 users，CPU/GPU=0",
    "purpose": "验证 8B NVMe-only 高并发 KV Cache。",
    "steps": [
        "准备 MLPerf option 1，8B，200 users，CPU/GPU=0 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 worst P95、tokens/s、tier bytes，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_option1_8b_nvme_only.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：storage_entries>0；所有 trial 完成；worst P95 和 tokens/s 达到对应 SLA；NVMe tier 有实际 I/O。",
    "metrics": "worst P95、tokens/s、tier bytes",
    "mode": "kv",
    "users": 200
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
