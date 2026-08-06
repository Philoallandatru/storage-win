"""AI-KV-006 · llama2_7b_upper_bound

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
    "case_id": "AI-KV-006",
    "category": "kv",
    "case_name": "llama2_7b_upper_bound",
    "config": "llama2-7b，512 KiB/token，alloc 1/2/4/8",
    "purpose": "验证较大 KV/token 下的 P99.9 和 OOM 边界。",
    "steps": [
        "准备 llama2-7b，512 KiB/token，alloc 1/2/4/8 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 P99.9、OOM guard、tier bytes，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_llama2_7b_upper_bound.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：各 alloc 点结果完整；OOM guard 正常；无 silent eviction 或目录误写。",
    "metrics": "P99.9、OOM guard、tier bytes",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
