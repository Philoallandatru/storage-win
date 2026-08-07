"""Windows regression tests for MLPerf Storage YAML loading."""

from __future__ import annotations

import mlpstorage_py.utils as utils


def test_read_config_from_file_uses_utf8(tmp_path, monkeypatch) -> None:
    config = tmp_path / "workload.yaml"
    config.write_text('description: "early → late"\n', encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIGS_ROOT_DIR", str(tmp_path))

    loaded = utils.read_config_from_file("workload.yaml")

    assert loaded["description"] == "early → late"
