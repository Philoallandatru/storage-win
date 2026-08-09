from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_windows_build_guide_and_scripts_are_present() -> None:
    required = (
        ROOT / "docs" / "WINDOWS_OFFLINE_BUNDLE_BUILD.md",
        ROOT / "tools" / "download_msmpi.ps1",
        ROOT / "tools" / "setup_windows_build_env.ps1",
        ROOT / "tools" / "activate_windows_venv.ps1",
        ROOT / "tools" / "verify_windows_benchmark_environment.ps1",
        ROOT / "tools" / "prepare_windows_offline_bundle.ps1",
        ROOT / "tools" / "build_windows_offline_bundle.cmd",
    )
    assert all(path.is_file() for path in required)


def test_windows_build_scripts_use_repository_entrypoints() -> None:
    prepare = (ROOT / "tools" / "prepare_windows_offline_bundle.ps1").read_text(encoding="utf-8")
    setup = (ROOT / "tools" / "setup_windows_build_env.ps1").read_text(encoding="utf-8")
    download = (ROOT / "tools" / "download_msmpi.ps1").read_text(encoding="utf-8")
    builder = (ROOT / "tools" / "build_windows_offline_bundle.ps1").read_text(encoding="utf-8")
    verifier = (ROOT / "tools" / "verify_windows_benchmark_environment.ps1").read_text(encoding="utf-8")

    assert "download_msmpi.ps1" in prepare
    assert "setup_windows_build_env.ps1" in prepare
    assert "build_windows_offline_bundle.ps1" in prepare
    cmd = (ROOT / "tools" / "build_windows_offline_bundle.cmd").read_text(encoding="utf-8")
    assert "prepare_windows_offline_bundle.ps1" in cmd
    assert "ExecutionPolicy Bypass" in cmd
    assert "uv sync" in setup
    assert "--frozen" in setup
    assert "UV_INDEX_URL" in setup
    assert "pypi.tuna.tsinghua.edu.cn" in setup
    assert "kv_cache_benchmark" in setup
    assert "vdb_benchmark" in setup
    assert "Microsoft-MPI/releases/tags" in download
    assert "msmpisetup.exe" in download
    assert "MpiInstaller" in builder
    assert "verify_windows_benchmark_environment.ps1" in builder
    assert "SUPPORTED_PREFLIGHT_OK" in verifier
    assert "PYTHON_IMPORTS_OK" in verifier
    assert "MPI_OK" in verifier
    assert "Test-NetConnection" in verifier
    assert '[Alias("Destination")]' in builder
    assert '[Alias("Destination")]' in prepare
    assert "PythonIndexUrl" in prepare


def test_prepare_windows_bundle_accepts_named_parameters(tmp_path: Path) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to exercise the Windows bundle entrypoint")

    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    prepare = tools_dir / "prepare_windows_offline_bundle.ps1"
    shutil.copy2(ROOT / "tools" / prepare.name, prepare)

    (tools_dir / "download_msmpi.ps1").write_text(
        """param([string]$Version, [string]$Destination)
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Set-Content -LiteralPath (Join-Path $Destination 'msmpisetup.exe') -Value 'stub'
@{ Version = $Version; Destination = $Destination } |
    ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $PSScriptRoot 'download-args.json')
""",
        encoding="utf-8",
    )
    (tools_dir / "setup_windows_build_env.ps1").write_text(
        "param([string]$RepoRoot, [string]$PythonIndexUrl, [switch]$RecreateVenv, [switch]$UpdateLock)\n",
        encoding="utf-8",
    )
    (tools_dir / "build_windows_offline_bundle.ps1").write_text(
        """param([string]$Output, [string]$MpiInstaller)
Set-Content -LiteralPath $Output -Value $MpiInstaller
""",
        encoding="utf-8",
    )

    output = tmp_path / "bundle.zip"
    mpi_directory = tmp_path / "mpi"
    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(prepare),
            "-Output",
            str(output),
            "-MpiDirectory",
            str(mpi_directory),
            "-PythonIndexUrl",
            "https://pypi.tuna.tsinghua.edu.cn/simple",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.is_file()
    download_args = json.loads((tools_dir / "download-args.json").read_text(encoding="utf-8-sig"))
    assert download_args == {
        "Version": "v10.1.1",
        "Destination": str(mpi_directory),
    }
