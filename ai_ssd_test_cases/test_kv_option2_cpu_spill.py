"""AI-KV-002 · option2_cpu_spill

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
    "case_id": "AI-KV-002",
    "category": "kv",
    "case_name": "option2_cpu_spill",
    "config": "MLPerf option 2，4 GB CPU spill，100 users",
    "purpose": "验证 CPU spill 边界和 NVMe tier 仍有实际负载。",
    "steps": [
        "准备 MLPerf option 2，4 GB CPU spill，100 users 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 spill 时刻、P95、evictions、tier bytes，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_option2_cpu_spill.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：spill 行为可观察；NVMe tier entries>0；无 OOM；P95 达到 SLA。",
    "metrics": "spill 时刻、P95、evictions、tier bytes",
    "mode": "kv",
    "users": 100
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
