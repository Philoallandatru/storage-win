import threading
import time

from vdbbench import io_trace


class SlowWriter:
    def __init__(self, release):
        self.release = release
        self.rows = []

    def writerow(self, row):
        if self.rows:
            self.release.wait(timeout=1.0)
        self.rows.append(row)


def test_trace_log_does_not_block_formal_benchmark_timing(monkeypatch, tmp_path):
    release = threading.Event()
    slow_writer = SlowWriter(release)
    monkeypatch.setattr(io_trace.csv, "writer", lambda handle: slow_writer)
    trace = io_trace.TraceWriter(tmp_path / "trace.csv")

    started = time.perf_counter()
    trace.log(1.0, "Read", 16, "collection", "Search")
    elapsed = time.perf_counter() - started

    assert elapsed < 0.1
    release.set()
    trace.close()
    assert len(slow_writer.rows) == 2
