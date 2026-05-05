from __future__ import annotations

from datetime import UTC

from wb_sync.wb_api import WbApiClient, WbApiConfig


def test_parse_wb_datetime_falls_back_on_underflow():
    client = WbApiClient(WbApiConfig(timeout_seconds=60, retry_attempts=3, retry_base_seconds=5, rate_limit_seconds=60))

    parsed = client._parse_wb_datetime("0001-01-01T00:00:00")

    assert parsed.year == 1
    assert parsed.tzinfo == UTC
