from __future__ import annotations

import pytest

from app.source_config import SourceConfigError, parse_source_limits

pytestmark = pytest.mark.m11


def test_default_total_remains_1200():
    assert parse_source_limits({}).max_chunks_total == 1200


@pytest.mark.parametrize("value", [2000, 3000, 4000])
def test_explicit_total_limit_accepts_approved_range(value):
    assert parse_source_limits({"SA_SOURCE_MAX_CHUNKS_TOTAL": str(value)}).max_chunks_total == value


@pytest.mark.parametrize("value", ["0", "-1", "4001", "not-an-int"] )
def test_total_limit_rejects_invalid_or_beyond_hard_max(value):
    with pytest.raises(SourceConfigError):
        parse_source_limits({"SA_SOURCE_MAX_CHUNKS_TOTAL": value})


def test_other_limits_remain_independently_bounded():
    with pytest.raises(SourceConfigError):
        parse_source_limits({
            "SA_SOURCE_MAX_CHUNKS_TOTAL": "4000",
            "SA_SOURCE_MAX_CHUNKS_PER_SOURCE": "1001",
        })
