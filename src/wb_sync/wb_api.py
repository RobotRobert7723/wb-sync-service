from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from wb_sync.time_utils import MOSCOW_TZ, format_wb_datetime


LOGGER = logging.getLogger(__name__)
DATETIME_FIELDS = {
    "date",
    "lastChangeDate",
    "cancelDate",
    "dateFrom",
    "dateTo",
    "createDate",
    "supplyDate",
    "factDate",
    "updatedDate",
    "fixTariffDateFrom",
    "fixTariffDateTo",
    "orderDt",
    "saleDt",
    "rrDate",
}


@dataclass(slots=True)
class WbApiConfig:
    timeout_seconds: int
    retry_attempts: int
    retry_base_seconds: int
    rate_limit_seconds: int


class AccountRateLimiter:
    def __init__(self, interval_seconds: int):
        self._interval_seconds = interval_seconds
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            with self._lock:
                now = time.monotonic()
                delay = self._next_allowed - now
                if delay <= 0:
                    self._next_allowed = now + self._interval_seconds
                    return
            stop_event.wait(min(delay, 1))


class WbApiClient:
    BASE_URL = "https://statistics-api.wildberries.ru"
    FINANCE_BASE_URL = "https://finance-api.wildberries.ru"
    ANALYTICS_BASE_URL = "https://seller-analytics-api.wildberries.ru"
    SUPPLIES_BASE_URL = "https://supplies-api.wildberries.ru"

    def __init__(self, config: WbApiConfig):
        self.config = config

    def fetch_rows(
        self,
        api_type: str,
        token: str,
        date_from: datetime,
        stop_event: threading.Event,
    ) -> list[dict[str, Any]]:
        path = f"/api/v1/supplier/{api_type}"
        query = urlencode({"dateFrom": format_wb_datetime(date_from), "flag": 0})
        url = f"{self.BASE_URL}{path}?{query}"
        headers = {"Authorization": token}
        return self._request_json(url, headers, stop_event)

    def fetch_finance_sales_report_details(
        self,
        token: str,
        date_from: str,
        date_to: str,
        rrd_id: int,
        stop_event: threading.Event,
        limit: int = 100000,
        period: str = "daily",
    ) -> list[dict[str, Any]] | None:
        url = f"{self.FINANCE_BASE_URL}/api/finance/v1/sales-reports/detailed"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": limit,
            "rrdId": rrd_id,
            "period": period,
        }
        return self._request_json(url, headers, stop_event, payload=payload)

    def fetch_finance_sales_report_by_id(
        self,
        token: str,
        report_id: int,
        stop_event: threading.Event,
    ) -> list[dict[str, Any]] | None:
        url = f"{self.FINANCE_BASE_URL}/api/finance/v1/sales-reports/detailed/{report_id}"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        return self._request_json(url, headers, stop_event, payload={})

    def fetch_finance_sales_report_list(
        self,
        token: str,
        date_from: str,
        date_to: str,
        stop_event: threading.Event,
    ) -> list[dict[str, Any]] | None:
        url = f"{self.FINANCE_BASE_URL}/api/finance/v1/sales-reports/list"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        return self._request_json(url, headers, stop_event, payload=payload)

    def fetch_warehouse_remains(
        self,
        token: str,
        stop_event: threading.Event,
        locale: str = "ru",
    ) -> list[dict[str, Any]] | None:
        headers = {"Authorization": token}
        query = urlencode(
            {
                "locale": locale,
                "groupByBrand": "true",
                "groupBySubject": "true",
                "groupBySa": "true",
                "groupByNm": "true",
                "groupByBarcode": "true",
                "groupBySize": "true",
            }
        )
        create_url = f"{self.ANALYTICS_BASE_URL}/api/v1/warehouse_remains?{query}"
        task_response = self._request_object(create_url, headers, stop_event)
        task_id = ((task_response or {}).get("data") or {}).get("taskId")
        if not task_id:
            raise RuntimeError("WB warehouse_remains: taskId missing in create response")

        status_url = f"{self.ANALYTICS_BASE_URL}/api/v1/warehouse_remains/tasks/{task_id}/status"
        while True:
            if stop_event.is_set():
                raise RuntimeError("worker stopped before warehouse_remains status check")
            status_response = self._request_object(status_url, headers, stop_event)
            status = str(((status_response or {}).get("data") or {}).get("status") or "").lower()
            if status == "done":
                break
            if status in {"failed", "error", "cancelled"}:
                raise RuntimeError(f"WB warehouse_remains task failed: {status}")
            stop_event.wait(5)

        download_url = f"{self.ANALYTICS_BASE_URL}/api/v1/warehouse_remains/tasks/{task_id}/download"
        return self._request_json(download_url, headers, stop_event)

    def fetch_fbw_supplies(
        self,
        token: str,
        date_from: str,
        date_to: str,
        stop_event: threading.Event,
        limit: int = 1000,
        date_type: str = "createDate",
    ) -> list[dict[str, Any]]:
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        payload = {
            "dates": [{"from": date_from, "till": date_to, "type": date_type}],
            "statusIDs": [1, 2, 3, 4, 5, 6],
        }
        supplies: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = urlencode({"limit": limit, "offset": offset})
            url = f"{self.SUPPLIES_BASE_URL}/api/v1/supplies?{query}"
            page = self._request_json(url, headers, stop_event, payload=payload) or []
            supplies.extend(page)
            if len(page) < limit:
                return supplies
            offset += limit

    def fetch_fbw_supply_details(
        self,
        token: str,
        supply_id: int,
        is_preorder_id: bool,
        stop_event: threading.Event,
    ) -> dict[str, Any] | None:
        headers = {"Authorization": token}
        query = urlencode({"isPreorderID": str(is_preorder_id).lower()})
        url = f"{self.SUPPLIES_BASE_URL}/api/v1/supplies/{supply_id}?{query}"
        return self._request_object(url, headers, stop_event, not_found_none=True)

    def fetch_fbw_supply_goods(
        self,
        token: str,
        supply_id: int,
        is_preorder_id: bool,
        stop_event: threading.Event,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        headers = {"Authorization": token}
        goods: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = urlencode(
                {
                    "limit": limit,
                    "offset": offset,
                    "isPreorderID": str(is_preorder_id).lower(),
                }
            )
            url = f"{self.SUPPLIES_BASE_URL}/api/v1/supplies/{supply_id}/goods?{query}"
            page = self._request_json(url, headers, stop_event, not_found_none=True) or []
            goods.extend(page)
            if len(page) < limit:
                return goods
            offset += limit

    def fetch_fbw_supply_package(
        self,
        token: str,
        supply_id: int,
        stop_event: threading.Event,
    ) -> list[dict[str, Any]]:
        headers = {"Authorization": token}
        url = f"{self.SUPPLIES_BASE_URL}/api/v1/supplies/{supply_id}/package"
        return self._request_json(url, headers, stop_event, not_found_none=True) or []

    def _request_json(
        self,
        url: str,
        headers: dict[str, str],
        stop_event: threading.Event,
        payload: dict[str, Any] | None = None,
        not_found_none: bool = False,
    ) -> list[dict[str, Any]] | None:
        attempt = 0
        while True:
            if stop_event.is_set():
                raise RuntimeError("worker stopped before request")
            attempt += 1
            try:
                method = "GET" if payload is None else "POST"
                data = None if payload is None else json.dumps(payload).encode("utf-8")
                request = Request(url=url, headers=headers, method=method, data=data)
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    payload = response.read().decode("utf-8")
                data_obj = json.loads(payload) if payload else []
                if not isinstance(data_obj, list):
                    raise RuntimeError(f"unexpected WB response type: {type(data_obj)!r}")
                return [self._normalize_row(row) for row in data_obj]
            except HTTPError as exc:
                if exc.code == 204:
                    return None
                if exc.code == 404 and not_found_none:
                    return None
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.config.retry_attempts:
                    self._sleep_backoff(attempt, stop_event)
                    continue
                detail = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"WB API HTTP {exc.code}: {detail}") from exc
            except URLError as exc:
                if attempt < self.config.retry_attempts:
                    self._sleep_backoff(attempt, stop_event)
                    continue
                raise RuntimeError(f"WB API network error: {exc.reason}") from exc

    def _request_object(
        self,
        url: str,
        headers: dict[str, str],
        stop_event: threading.Event,
        payload: dict[str, Any] | None = None,
        not_found_none: bool = False,
    ) -> dict[str, Any] | None:
        attempt = 0
        while True:
            if stop_event.is_set():
                raise RuntimeError("worker stopped before request")
            attempt += 1
            try:
                method = "GET" if payload is None else "POST"
                data = None if payload is None else json.dumps(payload).encode("utf-8")
                request = Request(url=url, headers=headers, method=method, data=data)
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    payload_text = response.read().decode("utf-8")
                data_obj = json.loads(payload_text) if payload_text else None
                if data_obj is not None and not isinstance(data_obj, dict):
                    raise RuntimeError(f"unexpected WB response type: {type(data_obj)!r}")
                return data_obj
            except HTTPError as exc:
                if exc.code == 204:
                    return None
                if exc.code == 404 and not_found_none:
                    return None
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.config.retry_attempts:
                    self._sleep_backoff(attempt, stop_event)
                    continue
                detail = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"WB API HTTP {exc.code}: {detail}") from exc
            except URLError as exc:
                if attempt < self.config.retry_attempts:
                    self._sleep_backoff(attempt, stop_event)
                    continue
                raise RuntimeError(f"WB API network error: {exc.reason}") from exc

    def _sleep_backoff(self, attempt: int, stop_event: threading.Event) -> None:
        delay = self.config.retry_base_seconds * attempt
        LOGGER.warning("wb request retry scheduled", extra={"status": "retrying"})
        stop_event.wait(delay)

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        for field in DATETIME_FIELDS:
            value = normalized.get(field)
            if isinstance(value, str) and value:
                normalized[field] = self._parse_wb_datetime(value)
        return normalized

    def _parse_wb_datetime(self, value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            try:
                return parsed.replace(tzinfo=MOSCOW_TZ).astimezone(UTC)
            except OverflowError:
                # Some WB payloads contain minimum representable naive dates.
                # Converting them from UTC+3 to UTC may underflow Python datetime.
                return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
