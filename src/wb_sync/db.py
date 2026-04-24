from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, dsn: str, schema: str = "public"):
        self._dsn = dsn
        self._schema = schema

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(f"set search_path to {self._schema}, public")
            yield conn

    def execute_script(self, sql: str) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
