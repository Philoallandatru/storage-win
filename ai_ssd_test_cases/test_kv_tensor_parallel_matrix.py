"""AI-KV-014 · tensor_parallel_matrix

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
    "case_id": "AI-KV-014",
    "category": "kv",
    "case_name": "tensor_parallel_matrix",
    "config": "TP 1/2/4/8，num_gpus≥TP",
    "purpose": "量化 TP 变化对 per-rank shard 对象和聚合带宽的影响。",
    "steps": [
        "准备 TP 1/2/4/8，num_gpus≥TP 的 KV Cache tier、模型和用户/上下文配置。",
        "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
        "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
        "对照 per-rank bytes、aggregate BW、P99，确认没有 OOM、丢请求或缓存目录落错盘。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_kv_tensor_parallel_matrix.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：各 TP 点 rank 对齐；bytes 和 BW 可解释；尾延迟满足 SLA。",
    "metrics": "per-rank bytes、aggregate BW、P99",
    "mode": "kv",
    "users": 50
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
