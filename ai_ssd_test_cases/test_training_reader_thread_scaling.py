"""AI-TRN-015 · reader_thread_scaling

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
    "case_id": "AI-TRN-015",
    "category": "training",
    "case_name": "reader_thread_scaling",
    "config": "固定训练数据，read_threads 1/2/4/8/16/32",
    "purpose": "定位读取线程增加后的 SSD/CPU 饱和拐点。",
    "steps": [
        "准备 固定训练数据，read_threads 1/2/4/8/16/32 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、throughput、CPU、queue、P99、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_reader_thread_scaling.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：饱和拐点可复现；吞吐 CV≤5%；瓶颈可归因；无持续错误。",
    "metrics": "throughput、CPU、queue、P99",
    "mode": "saturation"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
