"""AI-KV-018 · generation_modes

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
    "case_id": "AI-KV-018",
    "category": "kv",
    "case_name": "generation_modes",
    "config": "none/fast/realistic generation",
    "purpose": "区分峰值生成节奏与真实生成节奏下的资源占用。",
    "steps": [
        "准备 none/fast/realistic generation 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 wall/active BW、SLA、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_kv_generation_modes.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：三种节奏可区分；wall/active BW 均有记录；SLA 判定不混淆。",
    "metrics": "wall/active BW、SLA、P99",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
