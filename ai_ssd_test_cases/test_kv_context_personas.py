"""AI-KV-017 · context_personas

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
    "case_id": "AI-KV-017",
    "category": "kv",
    "case_name": "context_personas",
    "config": "chatbot/coding/document 短/长上下文",
    "purpose": "比较不同上下文 persona 的对象分布和尾延迟。",
    "steps": [
        "准备 chatbot/coding/document 短/长上下文 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 object CDF、P99、tier bytes，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_context_personas.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：三类 persona 结果完整；object CDF 和尾延迟可解释；无丢请求。",
    "metrics": "object CDF、P99、tier bytes",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
