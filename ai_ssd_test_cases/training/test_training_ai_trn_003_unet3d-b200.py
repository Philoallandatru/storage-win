r"""Wrapper for AI-TRN-003 — UNet3D / B200, native, 983.0 GiB dataset.

Original xlsx row: 3 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  xlsx 'test cmd' 缺 --execute/--prepare；Capacity 列含义混淆；unet3d_b200.yaml 写 fork

真实根因（在本工作站上跑之前要知道）:
  983 GiB 装不下 389 GiB G 盘；fork 在 Windows 必 fail；CAP-01 容量门禁先阻断

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_003_unet3d-b200.py ^
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
    info = DEFAULT_CASES["AI-TRN-003"]
    raise SystemExit(main(info.case_id, info))
