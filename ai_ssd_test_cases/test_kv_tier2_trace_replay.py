"""AI-KV-021 · tier2_trace_replay

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
    "case_id": "AI-KV-021",
    "category": "kv",
    "case_name": "tier2_trace_replay",
    "config": "Tier-2 trace，1×/2×/4×，Windows Direct I/O",
    "purpose": "在 Windows Direct I/O 下复现过滤后的 Tier-2 访问。",
    "steps": [
        "准备 Tier-2 trace，1×/2×/4×，Windows Direct I/O 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 P50/P95/P99、aligned BW、实际读字节，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_tier2_trace_replay.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：trace 过滤范围可追溯；三种速率完成；aligned BW 和尾延迟可复现。",
    "metrics": "P50/P95/P99、aligned BW、实际读字节",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
