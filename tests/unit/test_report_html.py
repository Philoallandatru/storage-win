"""Tests for the styled HTML/Markdown test report generator (tools/gen_test_report.py).

Covers the two user-facing contracts of the report:
  1. ``run_ai_ssd_suite.py`` always renders a self-contained HTML report
     (``render_html``) — the suite no longer ships JSON-only summaries.
  2. The HTML report is styled (badges, summary cards, per-family section)
     and includes every family incl. the new MIX family.
"""

from __future__ import annotations

import json

from tools.gen_test_report import (
    _flatten,
    _totals,
    load_summaries,
    render_html,
    render_md,
)


def _make_summary(tmp_path) -> dict:
    summary = {
        "capacity": "512GB",
        "memory": "32GB",
        "timestamp": "2026-08-15 21:00:00",
        "results": [
            {"case_id": "AI-TRN-003", "family": "Training", "result": "PASS", "rc": 0, "duration": "120s"},
            {"case_id": "AI-CKP-001", "family": "Checkpoint", "result": "PASS", "rc": 0, "duration": "394s"},
            {"case_id": "AI-KV-001", "family": "KV Cache", "result": "FAIL", "rc": 1, "duration": "60s",
             "note": "dlio crash"},
            {"case_id": "AI-VDB-001", "family": "VectorDB", "result": "SKIP", "rc": -1, "duration": "0s",
             "note": "AISAQ"},
            {"case_id": "AI-MIX-001", "family": "MIX", "result": "PASS", "rc": 0, "duration": "90s"},
        ],
    }
    p = tmp_path / "suite_summary_512GB_32GB.json"
    p.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return summary


def test_render_html_contains_styled_sections(tmp_path):
    """The HTML report must be self-contained, styled, and cover all families."""
    _make_summary(tmp_path)
    scenarios = load_summaries(tmp_path)
    html = render_html(scenarios, tmp_path)

    assert html.startswith("<!DOCTYPE html>")
    assert "AI SSD 测试报告" in html
    # summary cards
    for cls in ("card total", "card pass", "card fail", "card skip", "card rate"):
        assert cls in html
    # result badges
    assert 'badge PASS' in html
    assert 'badge FAIL' in html
    assert 'badge SKIP' in html
    # per-case rows for every family incl. MIX
    assert "AI-MIX-001" in html
    assert "AI-TRN-003" in html
    assert "AI-CKP-001" in html
    # per-family section header
    assert "按家族汇总" in html
    assert "MIX" in html
    # inline CSS (self-contained, no external assets)
    assert "<style>" in html and "linear-gradient" in html


def test_render_html_totals(tmp_path):
    """PASS/FAIL/SKIP tallies must be computed correctly."""
    _make_summary(tmp_path)
    scenarios = load_summaries(tmp_path)
    total, passed, failed, skipped = _totals(_flatten(scenarios))
    assert (total, passed, failed, skipped) == (5, 3, 1, 1)


def test_render_md_legacy_still_works(tmp_path):
    """The legacy Markdown renderer must remain functional."""
    _make_summary(tmp_path)
    scenarios = load_summaries(tmp_path)
    md = render_md(scenarios, tmp_path)
    assert md.startswith("# AI SSD")
    assert "AI-MIX-001" in md
    assert "PASS 3 / FAIL 1 / SKIP 1" in md
