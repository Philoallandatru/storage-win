"""Regression tests for deterministic request queue ordering."""

from datetime import datetime
import queue

import kv_cache.benchmark as benchmark_module
from kv_cache.benchmark import IntegratedBenchmark
from kv_cache.models import InferencePhase, InferenceRequest, QoSLevel


def _request(request_id: str) -> InferenceRequest:
    return InferenceRequest(
        user_id="user",
        request_id=request_id,
        timestamp=datetime.now(),
        context_tokens=128,
        generate_tokens=32,
        priority=1,
        phase=InferencePhase.PREFILL_DECODE,
        qos_level=QoSLevel.BATCH,
    )


def test_equal_priority_timestamps_do_not_compare_requests(monkeypatch):
    benchmark = object.__new__(IntegratedBenchmark)
    benchmark.request_queue = queue.PriorityQueue()
    monkeypatch.setattr(benchmark_module.time, "time", lambda: 123.0)

    benchmark._enqueue_request(_request("req-1"))
    benchmark._enqueue_request(_request("req-2"))

    assert benchmark.request_queue.get()[1].request_id == "req-1"
    assert benchmark.request_queue.get()[1].request_id == "req-2"
