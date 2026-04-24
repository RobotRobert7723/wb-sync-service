from __future__ import annotations

from dataclasses import replace

from wb_sync.dispatcher import Dispatcher, WorkerFactory
from wb_sync.models import WorkerConfig


class FakeRepository:
    def __init__(self, configs):
        self.configs = configs

    def load_worker_configs(self):
        return list(self.configs)


class FakeWorker:
    def __init__(self, config):
        self.config = config
        self.started = False
        self.stopped = False
        self.joined = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def join(self, timeout=None):
        self.joined = True


class FakeFactory(WorkerFactory):
    def __init__(self):
        self.instances = []

    def build(self, config):
        worker = FakeWorker(config)
        self.instances.append(worker)
        return worker


def make_config(account_id=1, api_type="orders", revision=1, enabled=True, schedule_seconds=300):
    return WorkerConfig(
        id=account_id * 10,
        account_id=account_id,
        account_code=f"shop_{account_id}",
        account_name=f"Shop {account_id}",
        token_env_var=f"WB_TOKEN_{account_id}",
        api_type=api_type,
        enabled=enabled,
        schedule_seconds=schedule_seconds,
        lookback_days=30,
        batch_limit=80000,
        revision=revision,
    )


def test_dispatcher_starts_enabled_workers():
    repo = FakeRepository([make_config(1, "orders"), make_config(2, "sales")])
    factory = FakeFactory()
    dispatcher = Dispatcher(repo, factory, poll_seconds=10)

    dispatcher.reconcile()

    assert len(dispatcher.workers) == 2
    assert all(worker.started for worker in factory.instances)


def test_dispatcher_restarts_worker_on_config_change():
    config = make_config(1, "orders", revision=1, schedule_seconds=300)
    repo = FakeRepository([config])
    factory = FakeFactory()
    dispatcher = Dispatcher(repo, factory, poll_seconds=10)

    dispatcher.reconcile()
    first_worker = factory.instances[0]

    repo.configs = [replace(config, revision=2, schedule_seconds=600)]
    dispatcher.reconcile()

    assert first_worker.stopped is True
    assert first_worker.joined is True
    assert len(factory.instances) == 2
    assert factory.instances[1].started is True


def test_dispatcher_stops_missing_worker():
    config = make_config(1, "orders")
    repo = FakeRepository([config])
    factory = FakeFactory()
    dispatcher = Dispatcher(repo, factory, poll_seconds=10)

    dispatcher.reconcile()
    first_worker = factory.instances[0]

    repo.configs = []
    dispatcher.reconcile()

    assert first_worker.stopped is True
    assert dispatcher.workers == {}
