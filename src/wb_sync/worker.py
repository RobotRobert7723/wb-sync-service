from __future__ import annotations

import logging
import threading
import uuid
from typing import Callable

from wb_sync.models import WorkerConfig
from wb_sync.repository import SyncRepository
from wb_sync.sync_logic import run_finance_sales_report_sync, run_incremental_sync
from wb_sync.wb_api import AccountRateLimiter, WbApiClient


LOGGER = logging.getLogger(__name__)


class SyncWorker:
    def __init__(
        self,
        worker_config: WorkerConfig,
        repository: SyncRepository,
        api_client: WbApiClient,
        rate_limiter: AccountRateLimiter,
    ):
        self.worker_config = worker_config
        self.repository = repository
        self.api_client = api_client
        self.rate_limiter = rate_limiter
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name=f"wb-{worker_config.account_code}-{worker_config.api_type}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        self.thread.join(timeout)

    def _row_key(self, row: dict[str, object]) -> str:
        if self.worker_config.api_type == "orders":
            return str(row.get("srid") or row.get("gNumber") or row.get("sticker"))
        if self.worker_config.api_type == "sales":
            return str(row.get("saleID") or row.get("srid") or row.get("gNumber") or row.get("sticker"))
        return str(row.get("reportId")) + ":" + str(row.get("rrdId"))

    def _writer(self) -> Callable[[int, list[dict[str, object]]], int]:
        if self.worker_config.api_type == "orders":
            return self.repository.upsert_orders
        if self.worker_config.api_type == "sales":
            return self.repository.upsert_sales
        return self.repository.upsert_finance_sales_report_details

    def _run(self) -> None:
        while not self.stop_event.is_set():
            run_id = str(uuid.uuid4())
            logger_extra = {
                "account_id": self.worker_config.account_id,
                "account_code": self.worker_config.account_code,
                "api_type": self.worker_config.api_type,
                "worker_id": self.worker_config.id,
                "run_id": run_id,
            }
            try:
                self.repository.mark_run_started(self.worker_config.account_id, self.worker_config.api_type, run_id)
                state = self.repository.get_state(self.worker_config.account_id, self.worker_config.api_type)
                self.rate_limiter.wait(self.stop_event)
                if self.stop_event.is_set():
                    self.repository.mark_run_interrupted(
                        self.worker_config.account_id,
                        self.worker_config.api_type,
                        run_id,
                    )
                    break
                if self.worker_config.api_type == "finance_sales_report_details":
                    result = run_finance_sales_report_sync(
                        worker=self.worker_config,
                        state=state,
                        stop_event=self.stop_event,
                        fetch_rows=self.api_client.fetch_finance_sales_report_details,
                        write_rows=self._writer(),
                    )
                else:
                    result = run_incremental_sync(
                        worker=self.worker_config,
                        state=state,
                        stop_event=self.stop_event,
                        fetch_rows=self.api_client.fetch_rows,
                        write_rows=self._writer(),
                        key_builder=self._row_key,
                    )
                self.repository.mark_run_success(
                    self.worker_config.account_id,
                    self.worker_config.api_type,
                    run_id,
                    result.rows_written,
                    result.cursor_timestamp,
                    getattr(result, "cursor_key", None),
                )
                LOGGER.info(
                    "worker sync finished",
                    extra={
                        **logger_extra,
                        "cursor_to": result.cursor_timestamp.isoformat() if result.cursor_timestamp else None,
                        "rows_written": result.rows_written,
                        "status": result.status,
                    },
                )
            except Exception as exc:
                if self.stop_event.is_set():
                    self.repository.mark_run_interrupted(
                        self.worker_config.account_id,
                        self.worker_config.api_type,
                        run_id,
                        str(exc),
                    )
                    LOGGER.info("worker stopped during sync", extra={**logger_extra, "status": "stopped"})
                    break
                self.repository.mark_run_error(self.worker_config.account_id, self.worker_config.api_type, run_id, str(exc))
                LOGGER.exception("worker sync failed", extra={**logger_extra, "status": "error"})
            if self.stop_event.wait(self.worker_config.schedule_seconds):
                break
