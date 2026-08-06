"""AI-KV-019 · rag_prefix_multiturn

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
    "case_id": "AI-KV-019",
    "category": "kv",
    "case_name": "rag_prefix_multiturn",
    "config": "RAG/prefix/multi-turn，docs 10/100",
    "purpose": "验证 KV 复用和额外文档 I/O 的收益与代价。",
    "steps": [
        "准备 RAG/prefix/multi-turn，docs 10/100 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 hit rate、bytes saved、P99、docs I/O，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_rag_prefix_multiturn.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：开关和 docs 阶梯完整；hit rate 与 bytes saved 可解释；P99 达标。",
    "metrics": "hit rate、bytes saved、P99、docs I/O",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
