from __future__ import annotations

import argparse
import signal
import sys

from wb_sync.config import AppConfig
from wb_sync.db import Database
from wb_sync.logging_utils import configure_logging
from wb_sync.schema import build_schema_sql
from wb_sync.service import build_dispatcher


def ensure_database_objects(app_config: AppConfig) -> None:
    Database(app_config.pg_dsn, app_config.db_schema).execute_script(build_schema_sql(app_config.db_schema))


def cmd_init_db(app_config: AppConfig) -> int:
    ensure_database_objects(app_config)
    print("schema initialized")
    return 0


def cmd_run(app_config: AppConfig) -> int:
    ensure_database_objects(app_config)
    dispatcher = build_dispatcher(app_config)

    def _shutdown(*_args):
        dispatcher.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    dispatcher.run_forever()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wb-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    subparsers.add_parser("run")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    app_config = AppConfig.from_env()
    configure_logging(app_config.log_level)
    if args.command == "init-db":
        return cmd_init_db(app_config)
    if args.command == "run":
        return cmd_run(app_config)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
