from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from wb_sync.models import SyncResult, WorkerConfig, WorkerState
from wb_sync.time_utils import default_lookback


class Fetcher(Protocol):
    def __call__(self, api_type: str, token: str, date_from: datetime, stop_event: object) -> list[dict[str, object]]: ...


class Writer(Protocol):
    def __call__(self, account_id: int, rows: list[dict[str, object]]) -> int: ...


@dataclass(slots=True)
class PageProgress:
    rows: list[dict[str, object]]
    next_cursor_timestamp: datetime | None
    next_cursor_key: str | None
    had_forward_progress: bool


def resolve_token(token_ref: str) -> str:
    env_value = os.getenv(token_ref)
    if env_value:
        return env_value
    if "." in token_ref and len(token_ref) > 40:
        return token_ref
    raise RuntimeError(f"WB token is not available: env var {token_ref} is not set and inline token was not detected")


def initial_cursor(worker: WorkerConfig, state: WorkerState | None) -> tuple[datetime, str | None]:
    if state and state.cursor_timestamp is not None:
        return state.cursor_timestamp, state.cursor_key
    return default_lookback(worker.lookback_days), None


def filter_page(
    payload: list[dict[str, object]],
    current_cursor_ts: datetime | None,
    current_cursor_key: str | None,
    key_builder: Callable[[dict[str, object]], str],
) -> PageProgress:
    filtered: list[dict[str, object]] = []
    next_cursor_ts = current_cursor_ts
    next_cursor_key = current_cursor_key
    had_forward_progress = False
    for row in payload:
        row_ts = row["lastChangeDate"]
        row_key = key_builder(row)
        if current_cursor_ts is not None:
            if row_ts < current_cursor_ts:
                continue
            if row_ts == current_cursor_ts and current_cursor_key is not None and row_key <= current_cursor_key:
                continue
        filtered.append(row)
        if next_cursor_ts is None or row_ts > next_cursor_ts or (row_ts == next_cursor_ts and (next_cursor_key is None or row_key > next_cursor_key)):
            next_cursor_ts = row_ts
            next_cursor_key = row_key
            had_forward_progress = True
    return PageProgress(filtered, next_cursor_ts, next_cursor_key, had_forward_progress)


def run_incremental_sync(
    worker: WorkerConfig,
    state: WorkerState | None,
    stop_event: object,
    fetch_rows: Fetcher,
    write_rows: Writer,
    key_builder: Callable[[dict[str, object]], str],
) -> SyncResult:
    token = resolve_token(worker.token_env_var)
    cursor_ts, cursor_key = initial_cursor(worker, state)
    rows_written = 0
    safety_guard = 0

    while True:
        safety_guard += 1
        if safety_guard > 1000:
            raise RuntimeError("sync paging exceeded safety limit")
        payload = fetch_rows(worker.api_type, token, cursor_ts, stop_event)
        if not payload:
            return SyncResult(rows_written, cursor_ts, cursor_key, "success" if rows_written else "noop")

        progress = filter_page(payload, cursor_ts, cursor_key, key_builder)
        if progress.rows:
            rows_written += write_rows(worker.account_id, progress.rows)

        if progress.next_cursor_timestamp is not None:
            cursor_ts = progress.next_cursor_timestamp
            cursor_key = progress.next_cursor_key

        if len(payload) < worker.batch_limit:
            return SyncResult(rows_written, cursor_ts, cursor_key, "success" if rows_written else "noop")

        if not progress.had_forward_progress:
            raise RuntimeError(
                f"cursor did not advance for account_id={worker.account_id} api_type={worker.api_type}; "
                "likely repeated page boundary on identical lastChangeDate"
            )
