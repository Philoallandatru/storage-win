"""AI-KV-015 · prefill_write

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
    "case_id": "AI-KV-015",
    "category": "kv",
    "case_name": "prefill_write",
    "config": "Prefill-only，model/users/context sweep",
    "purpose": "验证 disaggregated prefill 的写密集 KV 行为。",
    "steps": [
        "准备 Prefill-only，model/users/context sweep 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 write BW、fsync、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_prefill_write.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：写入字节完整；fsync 成功；write BW 和 P99 达到目标。",
    "metrics": "write BW、fsync、P99",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
