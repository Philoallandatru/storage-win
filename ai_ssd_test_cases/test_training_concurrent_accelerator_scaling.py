"""AI-TRN-014 · concurrent_accelerator_scaling

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
    "case_id": "AI-TRN-014",
    "category": "training",
    "case_name": "concurrent_accelerator_scaling",
    "config": "UNet3D/RetinaNet，workers 1/2/4/8/16",
    "purpose": "定位并发增加后的最大合格供数能力。",
    "steps": [
        "准备 UNet3D/RetinaNet，workers 1/2/4/8/16 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、AU、speedup、吞吐、P99、queue、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 90–120 分钟",
    "command": "python ai_ssd_test_cases/test_training_concurrent_accelerator_scaling.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：输出最大合格并发；AU 达标；speedup 可解释；饱和拐点明确。",
    "metrics": "AU、speedup、吞吐、P99、queue",
    "mode": "saturation"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
