"""AI-KV-007 · llama31_8b_users

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
    "case_id": "AI-KV-007",
    "category": "kv",
    "case_name": "llama31_8b_users",
    "config": "llama3.1-8b，users 25/50/100/200",
    "purpose": "绘制 8B 独立负载的最大合格用户曲线。",
    "steps": [
        "准备 llama3.1-8b，users 25/50/100/200 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 max compliant users、P99.99、tokens/s，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_llama31_8b_users.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：最大合格用户明确；Interactive SLA 全部满足；无 tier I/O 缺失。",
    "metrics": "max compliant users、P99.99、tokens/s",
    "mode": "kv",
    "users": 100
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
