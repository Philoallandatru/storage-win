"""AI-KV-020 · saturation_autoscale

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
    "case_id": "AI-KV-020",
    "category": "kv",
    "case_name": "saturation_autoscale",
    "config": "users/request-rate 逐步增加 20/25%",
    "purpose": "定位最大合格负载、队列拐点和恢复时间。",
    "steps": [
        "准备 users/request-rate 逐步增加 20/25% 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 knee、queue、recovery、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_saturation_autoscale.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：最大合格点明确；超过拐点能恢复；无持续丢请求或队列失控。",
    "metrics": "knee、queue、recovery、P99",
    "mode": "kv",
    "users": 100
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
