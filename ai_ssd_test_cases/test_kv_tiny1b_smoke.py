"""AI-KV-004 · tiny1b_smoke

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
    "case_id": "AI-KV-004",
    "category": "kv",
    "case_name": "tiny1b_smoke",
    "config": "tiny-1b，users 10→500",
    "purpose": "用小模型快速验证 KV Cache 的小对象 IOPS。",
    "steps": [
        "准备 tiny-1b，users 10→500 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 IOPS、P99、entries，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 30–45 分钟",
    "command": "python ai_ssd_test_cases/test_kv_tiny1b_smoke.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：用户阶梯可重跑；entries>0；P99 无异常尖峰；无丢请求。",
    "metrics": "IOPS、P99、entries",
    "mode": "kv",
    "users": 100
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
