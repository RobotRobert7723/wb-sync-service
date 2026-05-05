from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone


MOSCOW_TZ = timezone(timedelta(hours=3))


def utcnow() -> datetime:
    return datetime.now(UTC)


def format_wb_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def default_lookback(days: int) -> datetime:
    return utcnow() - timedelta(days=days)


def moscow_now() -> datetime:
    return datetime.now(MOSCOW_TZ)
