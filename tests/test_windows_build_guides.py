from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_build_guide_and_scripts_are_present() -> None:
    required = (
        ROOT / "docs" / "WINDOWS_OFFLINE_BUNDLE_BUILD.md",
        ROOT / "tools" / "download_msmpi.ps1",
        ROOT / "tools" / "setup_windows_build_env.ps1",
        ROOT / "tools" / "activate_windows_venv.ps1",
        ROOT / "tools" / "prepare_windows_offline_bundle.ps1",
    )
    assert all(path.is_file() for path in required)


def test_windows_build_scripts_use_repository_entrypoints() -> None:
    prepare = (ROOT / "tools" / "prepare_windows_offline_bundle.ps1").read_text(encoding="utf-8")
    setup = (ROOT / "tools" / "setup_windows_build_env.ps1").read_text(encoding="utf-8")
    download = (ROOT / "tools" / "download_msmpi.ps1").read_text(encoding="utf-8")
    builder = (ROOT / "tools" / "build_windows_offline_bundle.ps1").read_text(encoding="utf-8")

    assert "download_msmpi.ps1" in prepare
    assert "setup_windows_build_env.ps1" in prepare
    assert "build_windows_offline_bundle.ps1" in prepare
    assert "uv sync" in setup
    assert "kv_cache_benchmark" in setup
    assert "vdb_benchmark" in setup
    assert "Microsoft-MPI/releases/tags" in download
    assert "msmpisetup.exe" in download
    assert "MpiInstaller" in builder
