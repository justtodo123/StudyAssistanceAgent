from __future__ import annotations

import pytest

pytestmark = [pytest.mark.m11, pytest.mark.online]


@pytest.mark.skip(reason="real P0 downloads require explicit external confirmation")
def test_real_p0_download_is_not_a_blocking_offline_test():
    raise AssertionError("must remain explicitly gated")
