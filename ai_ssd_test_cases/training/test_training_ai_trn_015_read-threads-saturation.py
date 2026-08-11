r"""Wrapper for AI-TRN-015 — read_threads sweep, python_scaled, 1.0 GiB dataset.

Original xlsx row: 15 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  xlsx 'read_threads 1..32 sweep' 在 Python 缩版下不能复现；sweep 实现缺失

真实根因（在本工作站上跑之前要知道）:
  verdict=NOT_FORMAL；wrapper 只跑单点

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_015_read-threads-saturation.py ^
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
    info = DEFAULT_CASES["AI-TRN-015"]
    raise SystemExit(main(info.case_id, info))
