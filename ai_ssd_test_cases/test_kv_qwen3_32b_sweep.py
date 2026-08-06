"""AI-KV-010 · qwen3_32b_sweep

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
    "case_id": "AI-KV-010",
    "category": "kv",
    "case_name": "qwen3_32b_sweep",
    "config": "qwen3-32b，256 KiB/token",
    "purpose": "验证 32B KV 对象在用户和上下文变化下的供给。",
    "steps": [
        "准备 qwen3-32b，256 KiB/token 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 P99、BW、tokens/s，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_qwen3_32b_sweep.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：context/users sweep 完整；P99 和 BW 达到目标；无丢请求。",
    "metrics": "P99、BW、tokens/s",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
