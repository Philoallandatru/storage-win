"""AI-KV-003 · option3_70b

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
    "case_id": "AI-KV-003",
    "category": "kv",
    "case_name": "option3_70b",
    "config": "MLPerf option 3，70B，70 users，allocs=4",
    "purpose": "验证大模型 KV 对象下的带宽、尾延迟和 RAM 峰值。",
    "steps": [
        "准备 MLPerf option 3，70B，70 users，allocs=4 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 P95、BW、RAM 峰值、tier bytes，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_option3_70b.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：所有 trial 完成；tier I/O 可证；RAM 无越界；P95 和 BW 达到 SLA。",
    "metrics": "P95、BW、RAM 峰值、tier bytes",
    "mode": "kv",
    "users": 70
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
