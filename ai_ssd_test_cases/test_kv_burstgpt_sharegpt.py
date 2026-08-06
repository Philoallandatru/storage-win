"""AI-KV-022 · burstgpt_sharegpt

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
    "case_id": "AI-KV-022",
    "category": "kv",
    "case_name": "burstgpt_sharegpt",
    "config": "BurstGPT/ShareGPT arrival/context trace",
    "purpose": "验证真实 arrival 和 context 分布下的突发尾延迟。",
    "steps": [
        "准备 BurstGPT/ShareGPT arrival/context trace 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 burst tail、queue、drop、tokens/s，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 2–4 小时",
    "command": "python ai_ssd_test_cases/test_kv_burstgpt_sharegpt.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：外部数据集版本和 trace speed 固定；无异常 drop；突发尾延迟可解释。",
    "metrics": "burst tail、queue、drop、tokens/s",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
