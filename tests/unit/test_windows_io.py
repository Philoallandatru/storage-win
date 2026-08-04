"""Regression tests for Windows command and local-checkpoint I/O paths."""

import logging
import os
import subprocess
import sys

import pytest
from unittest.mock import MagicMock


def test_file_reader_reads_binary_data_at_arbitrary_offset(tmp_path, monkeypatch):
    from mlpstorage_py.checkpointing.storage_readers import file_reader as module

    payload = (b"prefix" + b"\x1a" + bytes(range(256))) * 16
    path = tmp_path / "checkpoint.bin"
    path.write_bytes(payload)

    # Force the Windows fallback even on POSIX CI so the seek/read emulation
    # is covered independently of os.pread availability.
    monkeypatch.delattr(module.os, "pread", raising=False)
    reader = module.FileStorageReader(str(path), fadvise_mode="none")
    try:
        offset = 185
        assert reader.read_chunk(offset, 128) == 128
        assert reader.total_bytes == 128
    finally:
        reader.close()


@pytest.mark.skipif(os.name != "nt", reason="exercises the native Windows argv parser")
def test_command_executor_preserves_windows_backslashes(tmp_path):
    from mlpstorage_py.utils import CommandExecutor

    logger = MagicMock(spec=logging.Logger)
    executor = CommandExecutor(logger=logger)
    value = str(tmp_path / "with space" / "value.bin")
    code = "import sys; print(sys.argv[1])"
    command = subprocess.list2cmdline([sys.executable, "-c", code, value])

    stdout, stderr, returncode = executor.execute(command)

    assert returncode == 0, stderr
    assert value in stdout
