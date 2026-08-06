"""AI-KV-013 · tier_capacity_matrix

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
    "case_id": "AI-KV-013",
    "category": "kv",
    "case_name": "tier_capacity_matrix",
    "config": "GPU/CPU=0/4/16/32 GiB",
    "purpose": "定位 GPU/CPU tier 变化下的 offload 拐点。",
    "steps": [
        "准备 GPU/CPU=0/4/16/32 GiB 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 tier occupancy、spill latency、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_tier_capacity_matrix.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：每个 tier 点完成；spill 拐点可定位；无 OOM 或缓存目录误写。",
    "metrics": "tier occupancy、spill latency、P99",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
