"""AI-KV-011 · gpt_oss_20b_moe

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
    "case_id": "AI-KV-011",
    "category": "kv",
    "case_name": "gpt_oss_20b_moe",
    "config": "gpt-oss-20b，MoE 小 KV，高 users",
    "purpose": "验证 MoE 小 KV 在高并发下的 IOPS 和 CPU 开销。",
    "steps": [
        "准备 gpt-oss-20b，MoE 小 KV，高 users 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 IOPS、CPU overhead、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_gpt_oss_20b_moe.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：高用户点可完成；CPU 开销可归因；IOPS 和 P99 达标。",
    "metrics": "IOPS、CPU overhead、P99",
    "mode": "kv",
    "users": 100
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
