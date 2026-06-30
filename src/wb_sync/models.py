from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


ApiType = Literal[
    "orders",
    "sales",
    "finance_sales_report_details",
    "finance_sales_report_weekly",
    "warehouse_remains",
    "fbw_supplies",
]


@dataclass(frozen=True, slots=True)
class AccountConfig:
    id: int
    account_code: str
    account_name: str
    enabled: bool
    token_env_var: str


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    id: int
    account_id: int
    account_code: str
    account_name: str
    token_env_var: str
    api_type: ApiType
    enabled: bool
    schedule_seconds: int
    lookback_days: int
    batch_limit: int
    revision: int

    @property
    def worker_key(self) -> tuple[int, str]:
        return (self.account_id, self.api_type)

    @property
    def config_signature(self) -> tuple[object, ...]:
        return (
            self.account_id,
            self.account_code,
            self.account_name,
            self.token_env_var,
            self.api_type,
            self.enabled,
            self.schedule_seconds,
            self.lookback_days,
            self.batch_limit,
            self.revision,
        )


@dataclass(frozen=True, slots=True)
class WorkerState:
    account_id: int
    api_type: ApiType
    cursor_timestamp: datetime | None
    cursor_key: str | None
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None
    heartbeat_at: datetime | None
    run_id: str | None
    status: str | None


@dataclass(frozen=True, slots=True)
class SyncResult:
    rows_written: int
    cursor_timestamp: datetime | None
    cursor_key: str | None
    status: Literal["success", "noop"]


@dataclass(frozen=True, slots=True)
class FinanceSyncResult:
    rows_written: int
    cursor_timestamp: datetime | None
    status: Literal["success", "noop"]
