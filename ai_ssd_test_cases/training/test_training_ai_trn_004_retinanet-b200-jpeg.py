r"""Wrapper for AI-TRN-004 — RetinaNet / B200, native, 351.6 GiB dataset.

Original xlsx row: 4 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  xlsx 'test cmd' 缺 --prepare/--confirm-dut；测试工具列写 mlperform；retinanet_b200.yaml 写 fork

真实根因（在本工作站上跑之前要知道）:
  1.17M JPEG 文件 351.64 GiB（datagen 7 分钟）；fork 必 fail；G 盘容量够但缺 datagen 触发

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_004_retinanet-b200-jpeg.py ^
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
    info = DEFAULT_CASES["AI-TRN-004"]
    raise SystemExit(main(info.case_id, info))
