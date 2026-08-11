r"""Wrapper for AI-TRN-005 — RetinaNet / MI355, native, 351.6 GiB dataset.

Original xlsx row: 5 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  xlsx 写 MI355 但 compute time 是模拟,无真实 GPU 需求；retinanet_mi355.yaml 写 fork；与 TRN-004 同样本不同节奏

真实根因（在本工作站上跑之前要知道）:
  同 TRN-004 数据集；G 盘 389 GiB 够装 351 GiB；fork 在 Windows 必 fail

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_005_retinanet-mi355-jpeg.py ^
        --data-dir D:\AI-SSD-Data ^
        --result-dir E:\AI-SSD-Results ^
        --duration-sec 300 --repeat 3

The wrapper auto-cleans the python_scaled/ subtree on exit unless
--keep-data is passed; native cases are left untouched because the
real training data is the caller's responsibility.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_ssd_test_cases.training._common import DEFAULT_CASES, main  # noqa: E402


if __name__ == "__main__":
    info = DEFAULT_CASES["AI-TRN-005"]
    raise SystemExit(main(info.case_id, info))
