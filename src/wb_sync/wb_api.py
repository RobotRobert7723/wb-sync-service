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

from wb_sync.time_utils import format_wb_datetime


LOGGER = logging.getLogger(__name__)
DATETIME_FIELDS = {"date", "lastChangeDate", "cancelDate"}


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

    def _request_json(
        self,
        url: str,
        headers: dict[str, str],
        stop_event: threading.Event,
    ) -> list[dict[str, Any]]:
        attempt = 0
        while True:
            if stop_event.is_set():
                raise RuntimeError("worker stopped before request")
            attempt += 1
            try:
                request = Request(url=url, headers=headers, method="GET")
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    payload = response.read().decode("utf-8")
                data = json.loads(payload)
                if not isinstance(data, list):
                    raise RuntimeError(f"unexpected WB response type: {type(data)!r}")
                return [self._normalize_row(row) for row in data]
            except HTTPError as exc:
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
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
