from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "windows_offline_bundle"


def test_windows_bundle_has_install_and_run_entrypoints() -> None:
    for name in ("install.ps1", "install.cmd", "run.ps1", "run.cmd", "README.md"):
        assert (BUNDLE / name).is_file(), name


def test_install_is_offline_and_relocates_the_bundled_environment() -> None:
    source = (BUNDLE / "install.ps1").read_text(encoding="utf-8")

    assert "payload" in source
    assert "pyvenv.cfg" in source
    assert "__MLPERF_APP_ROOT__" in source
    assert 'Join-Path $bundleRoot "run.ps1"' in source
    assert 'Join-Path $bundleRoot "run.cmd"' in source
    assert 'Join-Path $bundleRoot "verify_windows_benchmark_environment.ps1"' in source
    assert "uv sync" not in source
    assert "pip install" not in source


def test_run_calls_the_installed_case_directly() -> None:
    source = (BUNDLE / "run.ps1").read_text(encoding="utf-8")

    assert "full_test_plan_cases" in source
    assert "venv\\Scripts\\python.exe" in source
    assert "--confirm-dut" in source
    assert "--mode" in source


def test_bundle_builder_includes_runtime_sources_and_mpi_installer() -> None:
    source = (ROOT / "tools" / "build_windows_offline_bundle.ps1").read_text(encoding="utf-8")

    for required in (".venv", "mlpstorage_py", "configs", "full_test_plan_cases", "kv_cache_benchmark", "vdb_benchmark", "MSMpiSetup.exe", "verify_windows_benchmark_environment.ps1"):
        assert required in source
    for excluded in (".pytest_cache", "__pycache__", '"results"', '"data"', '"checkpoints"', '"tests"', '"fixtures"', '".pyc"', '".pyo"'):
        assert excluded in source
