from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from wb_sync.models import WorkerConfig
from wb_sync.repository import SyncRepository
from wb_sync.worker import SyncWorker


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ManagedWorker:
    config: WorkerConfig
    worker: SyncWorker


class WorkerFactory:
    def build(self, config: WorkerConfig) -> SyncWorker:
        raise NotImplementedError


class Dispatcher:
    def __init__(self, repository: SyncRepository, worker_factory: WorkerFactory, poll_seconds: int):
        self.repository = repository
        self.worker_factory = worker_factory
        self.poll_seconds = poll_seconds
        self.stop_event = threading.Event()
        self.workers: dict[tuple[int, str], ManagedWorker] = {}

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            self.reconcile()
            self.stop_event.wait(self.poll_seconds)
        self._stop_all()

    def stop(self) -> None:
        self.stop_event.set()

    def reconcile(self) -> None:
        desired = {config.worker_key: config for config in self.repository.load_worker_configs() if config.enabled}
        current_keys = set(self.workers)
        desired_keys = set(desired)

        for key in current_keys - desired_keys:
            self._stop_worker(key)

        for key in desired_keys:
            desired_config = desired[key]
            managed = self.workers.get(key)
            if managed is None:
                self._start_worker(desired_config)
                continue
            if managed.config.config_signature != desired_config.config_signature:
                self._stop_worker(key)
                self._start_worker(desired_config)

    def _start_worker(self, config: WorkerConfig) -> None:
        worker = self.worker_factory.build(config)
        worker.start()
        self.workers[config.worker_key] = ManagedWorker(config=config, worker=worker)
        LOGGER.info(
            "worker started",
            extra={
                "account_id": config.account_id,
                "account_code": config.account_code,
                "api_type": config.api_type,
                "worker_id": config.id,
                "status": "started",
            },
        )

    def _stop_worker(self, key: tuple[int, str]) -> None:
        managed = self.workers.pop(key, None)
        if managed is None:
            return
        managed.worker.stop()
        managed.worker.join(timeout=5)
        LOGGER.info(
            "worker stopped",
            extra={
                "account_id": managed.config.account_id,
                "account_code": managed.config.account_code,
                "api_type": managed.config.api_type,
                "worker_id": managed.config.id,
                "status": "stopped",
            },
        )

    def _stop_all(self) -> None:
        for key in list(self.workers):
            self._stop_worker(key)
