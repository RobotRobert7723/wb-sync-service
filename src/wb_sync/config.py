from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True, slots=True)
class AppConfig:
    pg_dsn: str
    db_schema: str = "wb_prod"
    dispatcher_poll_seconds: int = 10
    http_timeout_seconds: int = 60
    retry_attempts: int = 5
    retry_base_seconds: int = 2
    rate_limit_seconds: int = 60
    supplies_rate_limit_seconds: int = 2
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        pg_dsn = cls._build_dsn_from_env()
        return cls(
            pg_dsn=pg_dsn,
            db_schema=os.getenv("WB_SYNC_DB_SCHEMA", "wb_prod"),
            dispatcher_poll_seconds=_env_int("WB_SYNC_DISPATCHER_POLL_SECONDS", 10),
            http_timeout_seconds=_env_int("WB_SYNC_HTTP_TIMEOUT_SECONDS", 60),
            retry_attempts=_env_int("WB_SYNC_RETRY_ATTEMPTS", 5),
            retry_base_seconds=_env_int("WB_SYNC_RETRY_BASE_SECONDS", 2),
            rate_limit_seconds=_env_int("WB_SYNC_RATE_LIMIT_SECONDS", 60),
            supplies_rate_limit_seconds=_env_int("WB_SYNC_SUPPLIES_RATE_LIMIT_SECONDS", 2),
            log_level=os.getenv("WB_SYNC_LOG_LEVEL", "INFO").upper(),
        )

    @staticmethod
    def _build_dsn_from_env() -> str:
        pg_dsn = os.getenv("WB_SYNC_PG_DSN")
        if pg_dsn:
            return pg_dsn

        host = os.getenv("WB_SYNC_PG_HOST")
        port = os.getenv("WB_SYNC_PG_PORT", "5432")
        dbname = os.getenv("WB_SYNC_PG_DATABASE")
        user = os.getenv("WB_SYNC_PG_USER")
        password = os.getenv("WB_SYNC_PG_PASSWORD")
        if all([host, port, dbname, user, password]):
            return (
                f"postgresql://{quote_plus(user)}:{quote_plus(password)}@"
                f"{host}:{port}/{quote_plus(dbname)}"
            )

        raise ValueError(
            "Set either WB_SYNC_PG_DSN or the full set of "
            "WB_SYNC_PG_HOST/WB_SYNC_PG_PORT/WB_SYNC_PG_DATABASE/WB_SYNC_PG_USER/WB_SYNC_PG_PASSWORD"
        )
