"""AI-KV-016 · decode_read

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
    "case_id": "AI-KV-016",
    "category": "kv",
    "case_name": "decode_read",
    "config": "Decode-only，预置 cache，model/users",
    "purpose": "验证 disaggregated decode 的读密集 KV 行为。",
    "steps": [
        "准备 Decode-only，预置 cache，model/users 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 read BW、P99.99、tokens/s，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_decode_read.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：预置 cache 可复用；实际读字节可证；P99.99 和 tokens/s 达标。",
    "metrics": "read BW、P99.99、tokens/s",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
