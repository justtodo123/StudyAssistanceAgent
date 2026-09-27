from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.m11


def _report(**overrides):
    report = {"document_count": 1, "chunk_count": 3, "source_count": 1}
    report.update(overrides)
    return report


@pytest.mark.parametrize("field", ["document_count", "chunk_count", "source_count"])
def test_gate_report_requires_all_counts(field):
    report = _report()
    report.pop(field)
    assert field not in report
    assert not {"document_count", "chunk_count", "source_count"} <= report.keys()


def test_gate_report_counts_are_non_empty_and_serializable():
    report = _report()
    assert all(isinstance(report[field], int) and report[field] > 0 for field in report)
    encoded = json.dumps(report, ensure_ascii=False)
    assert "D:\\" not in encoded
    assert "password" not in encoded.lower()
