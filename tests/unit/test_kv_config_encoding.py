"""Windows regression tests for KV-cache YAML configuration loading."""

from __future__ import annotations

from kv_cache.config import ConfigLoader


def test_config_loader_reads_utf8_independently_of_windows_code_page(tmp_path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        'model_configs:\n  demo:\n    name: "Model’s UTF-8 configuration"\n',
        encoding="utf-8",
    )

    loaded = ConfigLoader(str(config))

    assert loaded.config["model_configs"]["demo"]["name"] == "Model’s UTF-8 configuration"
