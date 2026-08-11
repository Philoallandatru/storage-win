r"""Wrapper for AI-TRN-001 — UNet3D / A100, native_special, 983.0 GiB dataset.

Original xlsx row: 1 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  xlsx 'test cmd' 缺 --execute/--prepare/--confirm-dut；'test tool' 写 mlperform 实为 mlpstorage；Capacity 是被测 SSD 档位 (2TB/4TB) 不是数据集大小 (983 GiB)

真实根因（在本工作站上跑之前要知道）:
  983 GiB 7,200 文件 装不下 389 GiB G 盘；unet3d_a100.yaml 写 multiprocessing_context=fork 在 Windows 直接 fail；不传 --prepare 就跳过 datagen 直接 run

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_001_unet3d-a100.py ^
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
    info = DEFAULT_CASES["AI-TRN-001"]
    raise SystemExit(main(info.case_id, info))
