"""AI-TRN-003 · unet3d_b200_large_read

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
    "case_id": "AI-TRN-003",
    "category": "training",
    "case_name": "unet3d_b200_large_read",
    "config": "UNet3D/B200 NPZ，accelerator 1/2/4/8",
    "purpose": "验证大规模 NPZ 数据长时间连续读取。",
    "steps": [
        "准备 UNet3D/B200 NPZ，accelerator 1/2/4/8 对应的训练数据，数据盘与结果盘分离。",
        "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
        "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
        "对齐 AU、AU、samples/s、GiB/s、后半程漂移、PhysicalDisk 队列和温度，检查后半程退化。"
    ],
    "test_duration": "约 60–90 分钟",
    "command": "python ai_ssd_test_cases/test_training_unet3d_b200_large_read.py --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
    "standard": "PASS：AU≥90%；后半程吞吐下降≤10%；温度、队列和数据完整性正常。",
    "metrics": "AU、samples/s、GiB/s、后半程漂移",
    "mode": "sequential"
}


if __name__ == "__main__":
    raise SystemExit(execute_case(CASE_SPEC))
