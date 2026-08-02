"""Windows file I/O that bypasses the operating-system page cache."""

from __future__ import annotations

import ctypes
import os
import random
from ctypes import wintypes
from pathlib import Path


_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_CREATE_ALWAYS = 2
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_FLAG_WRITE_THROUGH = 0x80000000
_FILE_FLAG_NO_BUFFERING = 0x20000000
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _round_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


class WindowsDirectIO:
    """Issue sector-aligned, unbuffered Win32 reads and write-through writes."""

    def __init__(
        self,
        data_dir: Path,
        *,
        chunk_size: int,
        random_seed: int,
    ) -> None:
        if os.name != "nt":
            raise RuntimeError("direct I/O replay is currently supported on Windows only")

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_functions()
        self.alignment = self._volume_alignment(data_dir)
        self._capacity = _round_up(max(chunk_size, self.alignment), self.alignment)

        self._buffer_owner = ctypes.create_string_buffer(
            self._capacity + self.alignment
        )
        base_address = ctypes.addressof(self._buffer_owner)
        aligned_address = _round_up(base_address, self.alignment)
        self._buffer = ctypes.c_void_p(aligned_address)
        payload = random.Random(random_seed).randbytes(self._capacity)
        ctypes.memmove(self._buffer, payload, self._capacity)

    def _configure_functions(self) -> None:
        self._kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._kernel32.CreateFileW.restype = wintypes.HANDLE
        self._kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        self._kernel32.ReadFile.restype = wintypes.BOOL
        self._kernel32.WriteFile.argtypes = self._kernel32.ReadFile.argtypes
        self._kernel32.WriteFile.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.GetDiskFreeSpaceW.argtypes = [
            wintypes.LPCWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._kernel32.GetDiskFreeSpaceW.restype = wintypes.BOOL

    def _volume_alignment(self, data_dir: Path) -> int:
        sectors_per_cluster = wintypes.DWORD()
        bytes_per_sector = wintypes.DWORD()
        free_clusters = wintypes.DWORD()
        total_clusters = wintypes.DWORD()
        volume_root = str(data_dir.resolve().anchor)
        succeeded = self._kernel32.GetDiskFreeSpaceW(
            volume_root,
            ctypes.byref(sectors_per_cluster),
            ctypes.byref(bytes_per_sector),
            ctypes.byref(free_clusters),
            ctypes.byref(total_clusters),
        )
        if not succeeded:
            raise ctypes.WinError(ctypes.get_last_error())
        # Virtual-memory pages and common NVMe physical sectors are 4 KiB.
        # A larger reported sector still wins.
        return max(4096, int(bytes_per_sector.value))

    def _open(self, path: Path, *, write: bool) -> wintypes.HANDLE:
        access = _GENERIC_WRITE if write else _GENERIC_READ
        disposition = _CREATE_ALWAYS if write else _OPEN_EXISTING
        flags = _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_NO_BUFFERING
        if write:
            flags |= _FILE_FLAG_WRITE_THROUGH
        handle = self._kernel32.CreateFileW(
            str(path),
            access,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
            None,
            disposition,
            flags,
            None,
        )
        if handle == _INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def write(self, path: Path, size_bytes: int) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        physical_bytes = _round_up(size_bytes, self.alignment) if size_bytes else 0
        handle = self._open(path, write=True)
        try:
            remaining = physical_bytes
            while remaining:
                current_size = min(remaining, self._capacity)
                transferred = wintypes.DWORD()
                succeeded = self._kernel32.WriteFile(
                    handle,
                    self._buffer,
                    current_size,
                    ctypes.byref(transferred),
                    None,
                )
                if not succeeded:
                    raise ctypes.WinError(ctypes.get_last_error())
                if transferred.value != current_size:
                    raise OSError(
                        f"short direct write to {path}: "
                        f"{transferred.value} of {current_size} bytes"
                    )
                remaining -= current_size
        finally:
            self._kernel32.CloseHandle(handle)
        return physical_bytes

    def read(self, path: Path, size_bytes: int, row_number: int) -> int:
        physical_bytes = _round_up(size_bytes, self.alignment) if size_bytes else 0
        try:
            handle = self._open(path, write=False)
        except OSError as error:
            raise ValueError(
                f"read at CSV row {row_number} has no readable prior object: {path}"
            ) from error
        try:
            remaining = physical_bytes
            while remaining:
                current_size = min(remaining, self._capacity)
                transferred = wintypes.DWORD()
                succeeded = self._kernel32.ReadFile(
                    handle,
                    self._buffer,
                    current_size,
                    ctypes.byref(transferred),
                    None,
                )
                if not succeeded:
                    raise ctypes.WinError(ctypes.get_last_error())
                if transferred.value != current_size:
                    raise ValueError(
                        f"object is shorter than requested at CSV row "
                        f"{row_number}: {path}"
                    )
                remaining -= current_size
        finally:
            self._kernel32.CloseHandle(handle)
        return physical_bytes
