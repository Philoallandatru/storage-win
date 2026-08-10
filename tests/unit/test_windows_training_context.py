"""Windows-specific DLIO parameter normalization tests."""

from types import SimpleNamespace
from unittest.mock import patch

from mlpstorage_py.benchmarks.dlio import TrainingBenchmark
from mlpstorage_py.config import BENCHMARK_TYPES, PARAM_VALIDATION
from mlpstorage_py.rules.models import BenchmarkRun, BenchmarkRunData
from mlpstorage_py.rules.run_checkers.training import TrainingRunRulesChecker


def _benchmark(params=None):
    benchmark = TrainingBenchmark.__new__(TrainingBenchmark)
    benchmark.args = SimpleNamespace(params=params)
    noop = lambda *_args, **_kwargs: None
    benchmark.logger = SimpleNamespace(
        debug=noop,
        info=noop,
        status=noop,
        warning=noop,
        error=noop,
    )
    return benchmark


def test_training_params_use_spawn_on_windows():
    benchmark = _benchmark()

    with patch("mlpstorage_py.benchmarks.dlio.os.name", "nt"):
        params, _yaml, _combined = benchmark.process_dlio_params("unet3d_a100.yaml")

    assert params["reader.multiprocessing_context"] == "spawn"


def test_explicit_reader_context_is_preserved_on_windows():
    benchmark = _benchmark(["reader.multiprocessing_context=fork"])

    with patch("mlpstorage_py.benchmarks.dlio.os.name", "nt"):
        params, _yaml, _combined = benchmark.process_dlio_params("unet3d_a100.yaml")

    assert params["reader.multiprocessing_context"] == "fork"


def test_windows_spawn_is_not_an_invalid_training_override():
    data = BenchmarkRunData(
        benchmark_type=BENCHMARK_TYPES.training,
        model="unet3d",
        command="run",
        run_datetime="20260810_000000",
        num_processes=1,
        parameters={"reader": {"multiprocessing_context": "spawn"}},
        override_parameters={"reader.multiprocessing_context": "spawn"},
    )
    run = BenchmarkRun.from_data(data, _benchmark().logger)
    checker = TrainingRunRulesChecker(run, logger=_benchmark().logger)

    with patch("mlpstorage_py.rules.run_checkers.training.os.name", "nt"):
        issues = checker.check_allowed_params()

    assert issues[0].validation == PARAM_VALIDATION.CLOSED


def test_windows_explicit_fork_remains_invalid():
    data = BenchmarkRunData(
        benchmark_type=BENCHMARK_TYPES.training,
        model="unet3d",
        command="run",
        run_datetime="20260810_000001",
        num_processes=1,
        parameters={"reader": {"multiprocessing_context": "fork"}},
        override_parameters={"reader.multiprocessing_context": "fork"},
    )
    run = BenchmarkRun.from_data(data, _benchmark().logger)
    checker = TrainingRunRulesChecker(run, logger=_benchmark().logger)

    with patch("mlpstorage_py.rules.run_checkers.training.os.name", "nt"):
        issues = checker.check_allowed_params()

    assert issues[0].validation == PARAM_VALIDATION.INVALID
