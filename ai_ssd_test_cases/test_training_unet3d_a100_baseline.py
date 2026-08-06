"""AI-TRN-001 · unet3d_a100_baseline

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
    "case_id": "AI-TRN-001",
    "category": "training",
    "case_name": "unet3d_a100_baseline",
    "config": "UNet3D/A100 NPZ，accelerator 1/2/4",
    "purpose": "建立大文件训练数据的连续供给基线。",
    "steps": [
        "准备 UNet3D/A100 NPZ，accelerator 1/2/4 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、samples/s、GiB/s、AU、P99、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 45–60 分钟",
    "command": "python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；3 次吞吐 CV≤5%；PhysicalDisk 实际读字节可解释；无数据错误。",
    "metrics": "samples/s、GiB/s、AU、P99",
    "mode": "sequential"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
