from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from wb_sync.models import WorkerConfig, WorkerState
from wb_sync.sync_logic import (
    filter_page,
    run_finance_sales_report_sync,
    run_finance_sales_report_weekly_sync,
    run_incremental_sync,
)


def make_worker(batch_limit=3, api_type="orders"):
    return WorkerConfig(
        id=1,
        account_id=1,
        account_code="shop_1",
        account_name="Shop 1",
        token_env_var="WB_TOKEN_1",
        api_type=api_type,
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


def test_run_finance_sales_report_sync_pages_full_period(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    monkeypatch.setattr("wb_sync.sync_logic.moscow_now", lambda: datetime(2026, 5, 5, 12, 0, tzinfo=UTC) + timedelta(hours=3))

    calls = []
    written = []
    checkpoints = []

    def fetch_rows(token, date_from, date_to, rrd_id, stop_event, limit=100000):
        calls.append((date_from, date_to, rrd_id))
        if rrd_id == 0:
            return [
                {"reportId": 10, "rrdId": 1, "dateFrom": date_from},
                {"reportId": 10, "rrdId": 2, "dateFrom": date_from},
            ]
        if rrd_id == 2:
            return [{"reportId": 11, "rrdId": 3, "dateFrom": date_from}]
        return None

    def write_rows(account_id, rows):
        written.extend(rows)
        return len(rows)

    state = WorkerState(
        1,
        "finance_sales_report_details",
        datetime(2026, 5, 3, 0, 0, tzinfo=UTC),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )

    result = run_finance_sales_report_sync(
        worker=make_worker(batch_limit=100000, api_type="finance_sales_report_details"),
        state=state,
        stop_event=threading.Event(),
        fetch_rows=fetch_rows,
        write_rows=write_rows,
        checkpoint_progress=lambda cursor_timestamp, cursor_key: checkpoints.append((cursor_timestamp, cursor_key)),
    )

    assert result.rows_written == 3
    assert result.status == "success"
    assert [row["rrdId"] for row in written] == [1, 2, 3]
    assert calls == [
        ("2026-05-03T00:00:00+03:00", "2026-05-05T23:59:59+03:00", 0),
        ("2026-05-03T00:00:00+03:00", "2026-05-05T23:59:59+03:00", 2),
        ("2026-05-03T00:00:00+03:00", "2026-05-05T23:59:59+03:00", 3),
    ]
    assert checkpoints == [(datetime(2026, 5, 3, 0, 0, tzinfo=UTC), "2"), (datetime(2026, 5, 3, 0, 0, tzinfo=UTC), "3")]
    assert result.cursor_timestamp == datetime(2026, 5, 4, 21, 0, tzinfo=UTC)


def test_run_finance_sales_report_sync_returns_noop(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    monkeypatch.setattr("wb_sync.sync_logic.moscow_now", lambda: datetime(2026, 5, 5, 12, 0, tzinfo=UTC) + timedelta(hours=3))

    def fetch_rows(token, date_from, date_to, rrd_id, stop_event, limit=100000):
        return None

    result = run_finance_sales_report_sync(
        worker=make_worker(batch_limit=100000, api_type="finance_sales_report_details"),
        state=WorkerState(1, "finance_sales_report_details", datetime(2026, 5, 5, 0, 0, tzinfo=UTC), None, None, None, None, None, None, None, None, None),
        stop_event=threading.Event(),
        fetch_rows=fetch_rows,
        write_rows=lambda account_id, rows: len(rows),
    )

    assert result.rows_written == 0
    assert result.status == "noop"


def test_run_finance_sales_report_sync_resumes_from_cursor_key(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    monkeypatch.setattr("wb_sync.sync_logic.moscow_now", lambda: datetime(2026, 5, 5, 12, 0, tzinfo=UTC) + timedelta(hours=3))

    calls = []

    def fetch_rows(token, date_from, date_to, rrd_id, stop_event, limit=100000):
        calls.append((date_from, date_to, rrd_id))
        return None

    result = run_finance_sales_report_sync(
        worker=make_worker(batch_limit=100000, api_type="finance_sales_report_details"),
        state=WorkerState(1, "finance_sales_report_details", datetime(2026, 5, 3, 0, 0, tzinfo=UTC), "123", None, None, None, None, None, None, None, None),
        stop_event=threading.Event(),
        fetch_rows=fetch_rows,
        write_rows=lambda account_id, rows: len(rows),
    )

    assert calls == [("2026-05-03T00:00:00+03:00", "2026-05-05T23:59:59+03:00", 123)]
    assert result.status == "noop"


def test_run_finance_sales_report_weekly_sync_fetches_missing_report_ids(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_1", "secret")
    monkeypatch.setattr("wb_sync.sync_logic.moscow_now", lambda: datetime(2026, 6, 11, 12, 0, tzinfo=UTC) + timedelta(hours=3))

    list_calls = []
    detail_calls = []
    written = []

    def fetch_report_list(token, date_from, date_to, stop_event):
        list_calls.append((date_from, date_to))
        return [
            {"reportId": 726719011, "dateFrom": "2026-05-18", "dateTo": "2026-05-24", "createDate": "2026-05-25"},
            {"reportId": 736463794, "dateFrom": "2026-05-25", "dateTo": "2026-05-31", "createDate": "2026-06-01"},
            {"reportId": 743472446, "dateFrom": "2026-06-01", "dateTo": "2026-06-07", "createDate": "2026-06-08"},
        ]

    def fetch_report_rows(token, report_id, stop_event):
        detail_calls.append(report_id)
        return [{"reportId": report_id, "rrdId": report_id * 10}]

    def write_rows(account_id, rows):
        written.extend(rows)
        return len(rows)

    result = run_finance_sales_report_weekly_sync(
        worker=make_worker(batch_limit=100000, api_type="finance_sales_report_weekly"),
        stop_event=threading.Event(),
        fetch_report_list=fetch_report_list,
        fetch_report_rows=fetch_report_rows,
        get_existing_report_ids=lambda account_id, report_ids: {726719011},
        write_rows=write_rows,
    )

    assert list_calls == [("2026-05-12T00:00:00+03:00", "2026-06-11T23:59:59+03:00")]
    assert detail_calls == [736463794, 743472446]
    assert [row["reportId"] for row in written] == [736463794, 743472446]
    assert result.rows_written == 2
    assert result.status == "success"
