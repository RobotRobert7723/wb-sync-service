from __future__ import annotations

from wb_sync.models import WorkerConfig
from wb_sync.worker import SyncWorker


class OneShotStopEvent:
    def is_set(self):
        return False

    def wait(self, _seconds):
        return True


class FakeRateLimiter:
    def wait(self, _stop_event):
        return None


class FakeApiClient:
    def fetch_finance_sales_report_details(self, *_args, **_kwargs):
        return None

    def fetch_finance_sales_report_by_id(self, *_args, **_kwargs):
        return None


class FakeRepository:
    def __init__(self):
        self.fact_loads = []
        self.successes = []

    def mark_run_started(self, _account_id, _api_type, _run_id):
        return None

    def get_state(self, _account_id, _api_type):
        return None

    def checkpoint_run_progress(self, *_args):
        return None

    def upsert_finance_sales_report_details(self, _account_id, rows):
        return len(rows)

    def upsert_finance_sales_report_weekly(self, _account_id, rows):
        return len(rows)

    def load_article_daily_facts(self, account_id):
        self.fact_loads.append(account_id)
        return 3

    def mark_run_success(self, account_id, api_type, run_id, rows_written, cursor_timestamp, cursor_key):
        self.successes.append(
            {
                "account_id": account_id,
                "api_type": api_type,
                "run_id": run_id,
                "rows_written": rows_written,
                "cursor_timestamp": cursor_timestamp,
                "cursor_key": cursor_key,
            }
        )

    def mark_run_error(self, *_args):
        raise AssertionError("worker should not mark this run as failed")

    def mark_run_interrupted(self, *_args):
        raise AssertionError("worker should not mark this run as interrupted")


def make_config(api_type="finance_sales_report_details"):
    return WorkerConfig(
        id=1,
        account_id=10,
        account_code="shop_10",
        account_name="Shop 10",
        token_env_var="WB_TOKEN_10",
        api_type=api_type,
        enabled=True,
        schedule_seconds=300,
        lookback_days=30,
        batch_limit=100000,
        revision=1,
    )


def test_worker_loads_article_daily_facts_after_finance_details_run(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_10", "secret")
    repository = FakeRepository()
    worker = SyncWorker(make_config(), repository, FakeApiClient(), FakeRateLimiter())
    worker.stop_event = OneShotStopEvent()

    worker.run_once()

    assert repository.fact_loads == [10]
    assert repository.successes[0]["api_type"] == "finance_sales_report_details"


def test_worker_does_not_load_article_daily_facts_after_weekly_finance_run(monkeypatch):
    monkeypatch.setenv("WB_TOKEN_10", "secret")
    repository = FakeRepository()
    worker = SyncWorker(make_config("finance_sales_report_weekly"), repository, FakeApiClient(), FakeRateLimiter())
    worker.stop_event = OneShotStopEvent()

    worker.run_once()

    assert repository.fact_loads == []
    assert repository.successes[0]["api_type"] == "finance_sales_report_weekly"
