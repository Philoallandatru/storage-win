"""AI-KV-009 · deepseek_v3_mla

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
    "case_id": "AI-KV-009",
    "category": "kv",
    "case_name": "deepseek_v3_mla",
    "config": "deepseek-v3，context 4K/8K/25K，MLA",
    "purpose": "验证 MLA 压缩 KV 对小对象效率的影响。",
    "steps": [
        "准备 deepseek-v3，context 4K/8K/25K，MLA 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 对象大小、bytes/token、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_deepseek_v3_mla.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：三档 context 完成；对象大小和 bytes/token 可解释；尾延迟满足 SLA。",
    "metrics": "对象大小、bytes/token、P99",
    "mode": "kv",
    "users": 35
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
