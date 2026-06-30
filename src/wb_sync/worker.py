from __future__ import annotations

import logging
import threading
import uuid
from typing import Callable

from wb_sync.models import WorkerConfig
from wb_sync.repository import SyncRepository
from wb_sync.sync_logic import (
    run_fbw_supplies_sync,
    run_finance_sales_report_sync,
    run_finance_sales_report_weekly_sync,
    run_incremental_sync,
    run_warehouse_remains_sync,
)
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
        if self.worker_config.api_type == "warehouse_remains":
            return self.repository.replace_warehouse_remains
        if self.worker_config.api_type == "fbw_supplies":
            return self.repository.upsert_fbw_supplies
        if self.worker_config.api_type == "finance_sales_report_weekly":
            return self.repository.upsert_finance_sales_report_weekly
        return self.repository.upsert_finance_sales_report_details

    def _finance_period(self) -> str:
        if self.worker_config.api_type == "finance_sales_report_weekly":
            return "weekly"
        return "daily"

    def _limited_stats_fetcher(self):
        def _fetch(api_type, token, date_from, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_rows(api_type, token, date_from, stop_event)

        return _fetch

    def _limited_finance_fetcher(self):
        def _fetch(token, date_from, date_to, rrd_id, stop_event, limit=100000):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_finance_sales_report_details(
                token,
                date_from,
                date_to,
                rrd_id,
                stop_event,
                limit=limit,
                period=self._finance_period(),
            )

        return _fetch

    def _limited_finance_report_fetcher(self):
        def _fetch(token, report_id, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_finance_sales_report_by_id(
                token,
                report_id,
                stop_event,
            )

        return _fetch

    def _limited_finance_report_list_fetcher(self):
        def _fetch(token, date_from, date_to, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_finance_sales_report_list(
                token,
                date_from,
                date_to,
                stop_event,
            )

        return _fetch

    def _limited_warehouse_fetcher(self):
        def _fetch(token, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_warehouse_remains(
                token,
                stop_event,
            )

        return _fetch

    def _limited_fbw_supplies_fetcher(self):
        def _fetch(token, date_from, date_to, stop_event, limit=1000):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_fbw_supplies(
                token,
                date_from,
                date_to,
                stop_event,
                limit=limit,
            )

        return _fetch

    def _limited_fbw_supply_details_fetcher(self):
        def _fetch(token, supply_id, is_preorder_id, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_fbw_supply_details(
                token,
                supply_id,
                is_preorder_id,
                stop_event,
            )

        return _fetch

    def _limited_fbw_supply_goods_fetcher(self):
        def _fetch(token, supply_id, is_preorder_id, stop_event, limit=1000):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_fbw_supply_goods(
                token,
                supply_id,
                is_preorder_id,
                stop_event,
                limit=limit,
            )

        return _fetch

    def _limited_fbw_supply_package_fetcher(self):
        def _fetch(token, supply_id, stop_event):
            self.rate_limiter.wait(self.stop_event)
            return self.api_client.fetch_fbw_supply_package(
                token,
                supply_id,
                stop_event,
            )

        return _fetch

    def run_once(self) -> bool:
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
            if self.stop_event.is_set():
                self.repository.mark_run_interrupted(
                    self.worker_config.account_id,
                    self.worker_config.api_type,
                    run_id,
                )
                return False
            if self.worker_config.api_type == "finance_sales_report_weekly":
                result = run_finance_sales_report_weekly_sync(
                    worker=self.worker_config,
                    stop_event=self.stop_event,
                    fetch_report_list=self._limited_finance_report_list_fetcher(),
                    fetch_report_rows=self._limited_finance_report_fetcher(),
                    get_existing_report_ids=self.repository.get_existing_weekly_report_ids,
                    write_rows=self._writer(),
                )
                article_fact_rows = None
            elif self.worker_config.api_type == "finance_sales_report_details":
                result = run_finance_sales_report_sync(
                    worker=self.worker_config,
                    state=state,
                    stop_event=self.stop_event,
                    fetch_rows=self._limited_finance_fetcher(),
                    write_rows=self._writer(),
                    fetch_report_rows=self._limited_finance_report_fetcher(),
                    checkpoint_progress=lambda cursor_timestamp, cursor_key: self.repository.checkpoint_run_progress(
                        self.worker_config.account_id,
                        self.worker_config.api_type,
                        run_id,
                        cursor_timestamp,
                        cursor_key,
                    ),
                )
                article_fact_rows = None
                article_fact_rows = self.repository.load_article_daily_facts(self.worker_config.account_id)
            elif self.worker_config.api_type == "warehouse_remains":
                result = run_warehouse_remains_sync(
                    worker=self.worker_config,
                    stop_event=self.stop_event,
                    fetch_rows=self._limited_warehouse_fetcher(),
                    write_rows=self._writer(),
                )
                article_fact_rows = None
            elif self.worker_config.api_type == "fbw_supplies":
                result = run_fbw_supplies_sync(
                    worker=self.worker_config,
                    stop_event=self.stop_event,
                    fetch_supplies=self._limited_fbw_supplies_fetcher(),
                    fetch_details=self._limited_fbw_supply_details_fetcher(),
                    fetch_goods=self._limited_fbw_supply_goods_fetcher(),
                    fetch_package=self._limited_fbw_supply_package_fetcher(),
                    write_rows=self._writer(),
                )
                article_fact_rows = None
            else:
                result = run_incremental_sync(
                    worker=self.worker_config,
                    state=state,
                    stop_event=self.stop_event,
                    fetch_rows=self._limited_stats_fetcher(),
                    write_rows=self._writer(),
                    key_builder=self._row_key,
                )
                article_fact_rows = None
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
                    "article_fact_rows": article_fact_rows if self.worker_config.api_type == "finance_sales_report_details" else None,
                    "status": result.status,
                },
            )
            return True
        except Exception as exc:
            if self.stop_event.is_set():
                self.repository.mark_run_interrupted(
                    self.worker_config.account_id,
                    self.worker_config.api_type,
                    run_id,
                    str(exc),
                )
                LOGGER.info("worker stopped during sync", extra={**logger_extra, "status": "stopped"})
                return False
            self.repository.mark_run_error(self.worker_config.account_id, self.worker_config.api_type, run_id, str(exc))
            LOGGER.exception("worker sync failed", extra={**logger_extra, "status": "error"})
            return True

    def _run(self) -> None:
        while not self.stop_event.is_set():
            if not self.run_once():
                break
            if self.stop_event.wait(self.worker_config.schedule_seconds):
                break
