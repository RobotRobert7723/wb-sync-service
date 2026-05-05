from __future__ import annotations

from collections import defaultdict

from wb_sync.config import AppConfig
from wb_sync.db import Database
from wb_sync.dispatcher import Dispatcher, WorkerFactory
from wb_sync.repository import SyncRepository
from wb_sync.wb_api import AccountRateLimiter, WbApiClient, WbApiConfig
from wb_sync.worker import SyncWorker


class DefaultWorkerFactory(WorkerFactory):
    def __init__(self, repository: SyncRepository, app_config: AppConfig):
        self.repository = repository
        self.api_client = WbApiClient(
            WbApiConfig(
                timeout_seconds=app_config.http_timeout_seconds,
                retry_attempts=app_config.retry_attempts,
                retry_base_seconds=app_config.retry_base_seconds,
                rate_limit_seconds=app_config.rate_limit_seconds,
            )
        )
        self.rate_limiters: dict[tuple[int, str], AccountRateLimiter] = defaultdict(
            lambda: AccountRateLimiter(app_config.rate_limit_seconds)
        )

    def _rate_limiter_key(self, config) -> tuple[int, str]:
        api_group = "finance" if config.api_type == "finance_sales_report_details" else "statistics"
        return (config.account_id, api_group)

    def build(self, config):
        return SyncWorker(
            worker_config=config,
            repository=self.repository,
            api_client=self.api_client,
            rate_limiter=self.rate_limiters[self._rate_limiter_key(config)],
        )


def build_dispatcher(app_config: AppConfig) -> Dispatcher:
    db = Database(app_config.pg_dsn, app_config.db_schema)
    repository = SyncRepository(db)
    factory = DefaultWorkerFactory(repository, app_config)
    return Dispatcher(repository, factory, app_config.dispatcher_poll_seconds)
