"""Read-only access to the generated FULL_TEST_PLAN catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


SOURCE_SHA256 = "fada60afe5124244551ce248d3e8e3149a57a5b1b25bed2bc212d860d1d27656"
_CATALOG_PATH = Path(__file__).with_name("case_catalog.json")


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict[str, Any], ...]:
    payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"FULL_TEST_PLAN catalog must be a list: {_CATALOG_PATH}")
    return tuple(payload)


def load_catalog() -> list[dict[str, Any]]:
    """Return the executable native cases in workbook order."""
    return list(_catalog())


def get_case(case_id: str) -> dict[str, Any]:
    """Return one case by its exact ID."""
    normalized = case_id.upper()
    for case in _catalog():
        if case["case_id"] == normalized:
            return case
    raise KeyError(f"Unknown FULL_TEST_PLAN case: {case_id}")
