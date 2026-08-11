r"""Wrapper for AI-TRN-008 -- ResNet50 / A100, python_scaled, 1.0 GiB dataset.

Original xlsx row: 8 (Training Case table).

xlsx irrational points (corrected inside the wrapper):
  catalog 标 python_scaled; 'TFRecord 文件内多 sample 读取' in Python scaled does not reproduce
  1.0 GiB xlsx capacity is the *target SSD tier*; the actual dataset footprint is a few MB
  catalog 标 python_scaled, xlsx 测试命令走 native runner 必 BLOCKED；缺 --scale-mb

Real root cause (read this before running on the workstation):
  无 native 入口; verdict=NOT_FORMAL
  Python scaled loop writes a small flat file; no GPU / no fork blocker.

Usage::

    .venv\\Scripts\\python.exe ai_ssd_test_cases\\training\\test_training_ai_trn_008_resnet50_a100_tfrecord.py ^
        --data-dir D:\\AI-SSD-Data ^
        --result-dir E:\\AI-SSD-Results ^
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
    info = DEFAULT_CASES["AI-TRN-008"]
    raise SystemExit(main(info.case_id, info))
