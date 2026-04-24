from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from wb_sync.models import WorkerConfig, WorkerState
from wb_sync.sync_logic import filter_page, run_incremental_sync


def make_worker(batch_limit=3):
    return WorkerConfig(
        id=1,
        account_id=1,
        account_code="shop_1",
        account_name="Shop 1",
        token_env_var="WB_TOKEN_1",
        api_type="orders",
        enabled=True,
        schedule_seconds=300,
        lookback_days=30,
        batch_limit=batch_limit,
        revision=1,
    )


def test_filter_page_skips_rows_before_cursor():
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    payload = [
        {"lastChangeDate": ts, "srid": "a"},
        {"lastChangeDate": ts, "srid": "b"},
        {"lastChangeDate": ts + timedelta(minutes=1), "srid": "c"},
    ]

    progress = filter_page(payload, ts, "a", lambda row: row["srid"])

    assert [row["srid"] for row in progress.rows] == ["b", "c"]
    assert progress.next_cursor_timestamp == ts + timedelta(minutes=1)
    assert progress.next_cursor_key == "c"


def test_run_incremental_sync_pages_until_short_batch(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    calls = []

    def fetch_rows(api_type, token, date_from, stop_event):
        calls.append(date_from)
        if len(calls) == 1:
            return [
                {"lastChangeDate": ts, "srid": "a"},
                {"lastChangeDate": ts, "srid": "b"},
                {"lastChangeDate": ts + timedelta(minutes=1), "srid": "c"},
            ]
        return [{"lastChangeDate": ts + timedelta(minutes=2), "srid": "d"}]

    written = []

    def write_rows(account_id, rows):
        written.extend(rows)
        return len(rows)

    result = run_incremental_sync(
        worker=make_worker(batch_limit=3),
        state=WorkerState(1, "orders", ts, "a", None, None, None, None, None, None, None, None),
        stop_event=object(),
        fetch_rows=fetch_rows,
        write_rows=write_rows,
        key_builder=lambda row: row["srid"],
    )

    assert result.rows_written == 3
    assert result.cursor_timestamp == ts + timedelta(minutes=2)
    assert result.cursor_key == "d"
    assert [row["srid"] for row in written] == ["b", "c", "d"]


def test_run_incremental_sync_raises_on_stuck_cursor(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    ts = datetime(2026, 1, 1, tzinfo=UTC)

    def fetch_rows(api_type, token, date_from, stop_event):
        return [
            {"lastChangeDate": ts, "srid": "a"},
            {"lastChangeDate": ts, "srid": "a"},
            {"lastChangeDate": ts, "srid": "a"},
        ]

    with pytest.raises(RuntimeError, match="cursor did not advance"):
        run_incremental_sync(
            worker=make_worker(batch_limit=3),
            state=WorkerState(1, "orders", ts, "a", None, None, None, None, None, None, None, None),
            stop_event=object(),
            fetch_rows=fetch_rows,
            write_rows=lambda account_id, rows: len(rows),
            key_builder=lambda row: row["srid"],
        )
