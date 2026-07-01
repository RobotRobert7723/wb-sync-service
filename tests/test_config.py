from __future__ import annotations

import pytest

from wb_sync.config import AppConfig


def test_config_uses_dsn_from_env(monkeypatch):
    monkeypatch.setenv("WB_SYNC_PG_DSN", "postgresql://user:pass@localhost:5432/db")

    config = AppConfig.from_env()

    assert config.pg_dsn == "postgresql://user:pass@localhost:5432/db"
    assert config.db_schema == "wb_prod"


def test_config_builds_dsn_from_parts(monkeypatch):
    monkeypatch.delenv("WB_SYNC_PG_DSN", raising=False)
    monkeypatch.setenv("WB_SYNC_PG_HOST", "db.example.local")
    monkeypatch.setenv("WB_SYNC_PG_PORT", "5432")
    monkeypatch.setenv("WB_SYNC_PG_DATABASE", "warehouse")
    monkeypatch.setenv("WB_SYNC_PG_USER", "sync_user")
    monkeypatch.setenv("WB_SYNC_PG_PASSWORD", "s3cret")

    config = AppConfig.from_env()

    assert config.pg_dsn == "postgresql://sync_user:s3cret@db.example.local:5432/warehouse"


def test_config_reads_supplies_rate_limit(monkeypatch):
    monkeypatch.setenv("WB_SYNC_PG_DSN", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("WB_SYNC_SUPPLIES_RATE_LIMIT_SECONDS", "3")

    config = AppConfig.from_env()

    assert config.rate_limit_seconds == 60
    assert config.supplies_rate_limit_seconds == 3


def test_config_requires_db_settings(monkeypatch):
    monkeypatch.delenv("WB_SYNC_PG_DSN", raising=False)
    monkeypatch.delenv("WB_SYNC_PG_HOST", raising=False)
    monkeypatch.delenv("WB_SYNC_PG_PORT", raising=False)
    monkeypatch.delenv("WB_SYNC_PG_DATABASE", raising=False)
    monkeypatch.delenv("WB_SYNC_PG_USER", raising=False)
    monkeypatch.delenv("WB_SYNC_PG_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="WB_SYNC_PG_DSN"):
        AppConfig.from_env()
