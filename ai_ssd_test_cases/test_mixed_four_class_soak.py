"""AI-MIX-005 · four_class_soak

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
    "case_id": "AI-MIX-005",
    "category": "mixed",
    "case_name": "four_class_soak",
    "config": "4 类循环，fill/GC background，8 小时",
    "purpose": "验证长时间混合 AI SSD 稳定性和持续退化。",
    "steps": [
        "分别完成前台和后台 4 类循环，fill/GC background，8 小时 的单项基线。",
        "同时启动前台/后台负载，固定到达节奏并记录 UTC 时间线。",
        "重复运行并采集前台尾延迟、后台吞吐、队列和错误。",
        "对照单项基线，判断 错误数、前台尾延迟、吞吐退化、温度 是否满足通过门槛。"
    ],
    "test_duration": "约 8 小时",
    "command": "python ai_ssd_test_cases/test_mixed_four_class_soak.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：0 错误；无持续超过 10% 的退化；温度、空间和队列在安全范围。",
    "metrics": "错误数、前台尾延迟、吞吐退化、温度",
    "mode": "mixed",
    "users": 50,
    "dimensions": 128
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
