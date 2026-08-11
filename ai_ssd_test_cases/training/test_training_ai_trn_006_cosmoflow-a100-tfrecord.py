r"""Wrapper for AI-TRN-006 — CosmoFlow / A100, python_scaled, 1.0 GiB dataset.

Original xlsx row: 6 (Training Case表).

xlsx 不合理（已在 wrapper 里修正）:
  catalog 标 python_scaled；xlsx 测试命令走 native runner 必 BLOCKED；缺 --scale-mb

真实根因（在本工作站上跑之前要知道）:
  无 native 入口；TFRecord shuffle/随机访问在 Python 缩版下不能复现

Usage::

    .venv\Scripts\python.exe ai_ssd_test_cases\training\test_training_ai_trn_006_cosmoflow-a100-tfrecord.py ^
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
    info = DEFAULT_CASES["AI-TRN-006"]
    raise SystemExit(main(info.case_id, info))
