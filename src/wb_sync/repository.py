from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from psycopg import sql

from wb_sync.db import Database
from wb_sync.models import WorkerConfig, WorkerState
from wb_sync.time_utils import utcnow


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


class SyncRepository:
    def __init__(self, db: Database):
        self.db = db

    def load_worker_configs(self) -> list[WorkerConfig]:
        query = """
            select
                w.id,
                w.account_id,
                a.account_code,
                a.account_name,
                a.token_env_var,
                w.api_type,
                (a.enabled and w.enabled) as enabled,
                w.schedule_seconds,
                w.lookback_days,
                w.batch_limit,
                w.revision
            from wb_sync_workers w
            join wb_accounts a on a.id = w.account_id
            order by w.account_id, w.api_type
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return [WorkerConfig(**row) for row in rows]

    def get_state(self, account_id: int, api_type: str) -> WorkerState | None:
        query = """
            select account_id, api_type, cursor_timestamp, cursor_key, last_started_at,
                   last_finished_at, last_success_at, last_error_at, last_error_message,
                   heartbeat_at, run_id, status
            from wb_sync_state
            where account_id = %s and api_type = %s
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (account_id, api_type))
            row = cur.fetchone()
        return WorkerState(**row) if row else None

    def mark_run_started(self, account_id: int, api_type: str, run_id: str) -> None:
        now = utcnow()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into wb_sync_runs (account_id, api_type, run_id, started_at, status)
                values (%s, %s, %s, %s, 'running')
                """,
                (account_id, api_type, run_id, now),
            )
            cur.execute(
                """
                insert into wb_sync_state (
                    account_id, api_type, last_started_at, heartbeat_at, run_id, status
                )
                values (%s, %s, %s, %s, %s, 'running')
                on conflict (account_id, api_type) do update set
                    last_started_at = excluded.last_started_at,
                    heartbeat_at = excluded.heartbeat_at,
                    run_id = excluded.run_id,
                    status = excluded.status
                """,
                (account_id, api_type, now, now, run_id),
            )
            conn.commit()

    def update_heartbeat(self, account_id: int, api_type: str, run_id: str) -> None:
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update wb_sync_state
                set heartbeat_at = %s, run_id = %s
                where account_id = %s and api_type = %s
                """,
                (utcnow(), run_id, account_id, api_type),
            )
            conn.commit()

    def mark_run_success(
        self,
        account_id: int,
        api_type: str,
        run_id: str,
        rows_written: int,
        cursor_timestamp: datetime | None,
        cursor_key: str | None,
    ) -> None:
        now = utcnow()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update wb_sync_runs
                set finished_at = %s, status = 'success', rows_written = %s
                where run_id = %s
                """,
                (now, rows_written, run_id),
            )
            cur.execute(
                """
                insert into wb_sync_state (
                    account_id, api_type, cursor_timestamp, cursor_key, last_finished_at,
                    last_success_at, heartbeat_at, run_id, status, last_error_at, last_error_message
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'idle', null, null)
                on conflict (account_id, api_type) do update set
                    cursor_timestamp = excluded.cursor_timestamp,
                    cursor_key = excluded.cursor_key,
                    last_finished_at = excluded.last_finished_at,
                    last_success_at = excluded.last_success_at,
                    heartbeat_at = excluded.heartbeat_at,
                    run_id = excluded.run_id,
                    status = excluded.status,
                    last_error_at = excluded.last_error_at,
                    last_error_message = excluded.last_error_message
                """,
                (account_id, api_type, cursor_timestamp, cursor_key, now, now, now, run_id),
            )
            conn.commit()

    def mark_run_error(self, account_id: int, api_type: str, run_id: str, message: str) -> None:
        now = utcnow()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update wb_sync_runs
                set finished_at = %s, status = 'error', error_message = %s
                where run_id = %s
                """,
                (now, message[:4000], run_id),
            )
            cur.execute(
                """
                insert into wb_sync_state (
                    account_id, api_type, last_finished_at, last_error_at, last_error_message,
                    heartbeat_at, run_id, status
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'error')
                on conflict (account_id, api_type) do update set
                    last_finished_at = excluded.last_finished_at,
                    last_error_at = excluded.last_error_at,
                    last_error_message = excluded.last_error_message,
                    heartbeat_at = excluded.heartbeat_at,
                    run_id = excluded.run_id,
                    status = excluded.status
                """,
                (account_id, api_type, now, now, message[:4000], now, run_id),
            )
            conn.commit()

    def mark_run_interrupted(self, account_id: int, api_type: str, run_id: str, message: str = "worker stopped") -> None:
        now = utcnow()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update wb_sync_runs
                set finished_at = %s, status = 'stopped', error_message = %s
                where run_id = %s and finished_at is null
                """,
                (now, message[:4000], run_id),
            )
            cur.execute(
                """
                insert into wb_sync_state (
                    account_id, api_type, last_finished_at, last_error_at, last_error_message,
                    heartbeat_at, run_id, status
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'stopped')
                on conflict (account_id, api_type) do update set
                    last_finished_at = excluded.last_finished_at,
                    last_error_at = excluded.last_error_at,
                    last_error_message = excluded.last_error_message,
                    heartbeat_at = excluded.heartbeat_at,
                    run_id = excluded.run_id,
                    status = excluded.status
                """,
                (account_id, api_type, now, now, message[:4000], now, run_id),
            )
            conn.commit()

    def upsert_orders(self, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        records = [self._normalize_order(account_id, row) for row in rows]
        if not records:
            return 0
        columns = list(records[0].keys())
        insert_sql = sql.SQL(
            """
            insert into wb_orders ({fields})
            values ({values})
            on conflict (account_id, record_key) do update set
            {updates}
            """
        ).format(
            fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            updates=sql.SQL(", ").join(
                sql.SQL("{} = excluded.{}").format(sql.Identifier(col), sql.Identifier(col))
                for col in columns
                if col not in {"account_id", "record_key"}
            ),
        )
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.executemany(insert_sql, [tuple(record[col] for col in columns) for record in records])
            conn.commit()
        return len(records)

    def upsert_sales(self, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        records = [self._normalize_sale(account_id, row) for row in rows]
        if not records:
            return 0
        columns = list(records[0].keys())
        insert_sql = sql.SQL(
            """
            insert into wb_sales ({fields})
            values ({values})
            on conflict (account_id, record_key) do update set
            {updates}
            """
        ).format(
            fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            updates=sql.SQL(", ").join(
                sql.SQL("{} = excluded.{}").format(sql.Identifier(col), sql.Identifier(col))
                for col in columns
                if col not in {"account_id", "record_key"}
            ),
        )
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.executemany(insert_sql, [tuple(record[col] for col in columns) for record in records])
            conn.commit()
        return len(records)

    def _normalize_order(self, account_id: int, row: dict[str, object]) -> dict[str, object]:
        record_key = str(row.get("srid") or row.get("gNumber") or row.get("sticker"))
        return {
            "account_id": account_id,
            "record_key": record_key,
            "order_date": row.get("date"),
            "last_change_date": row.get("lastChangeDate"),
            "warehouse_name": row.get("warehouseName"),
            "warehouse_type": row.get("warehouseType"),
            "country_name": row.get("countryName"),
            "oblast_okrug_name": row.get("oblastOkrugName"),
            "region_name": row.get("regionName"),
            "supplier_article": row.get("supplierArticle"),
            "nm_id": row.get("nmId"),
            "barcode": row.get("barcode"),
            "category": row.get("category"),
            "subject": row.get("subject"),
            "brand": row.get("brand"),
            "tech_size": row.get("techSize"),
            "income_id": row.get("incomeID"),
            "is_supply": row.get("isSupply"),
            "is_realization": row.get("isRealization"),
            "total_price": _to_decimal(row.get("totalPrice")),
            "discount_percent": _to_decimal(row.get("discountPercent")),
            "spp": _to_decimal(row.get("spp")),
            "finished_price": _to_decimal(row.get("finishedPrice")),
            "price_with_disc": _to_decimal(row.get("priceWithDisc")),
            "is_cancel": row.get("isCancel"),
            "cancel_date": row.get("cancelDate"),
            "sticker": row.get("sticker"),
            "g_number": row.get("gNumber"),
            "srid": row.get("srid"),
            "updated_at": utcnow(),
        }

    def _normalize_sale(self, account_id: int, row: dict[str, object]) -> dict[str, object]:
        record_key = str(row.get("saleID") or row.get("srid") or row.get("gNumber") or row.get("sticker"))
        return {
            "account_id": account_id,
            "record_key": record_key,
            "sale_id": row.get("saleID"),
            "sale_date": row.get("date"),
            "last_change_date": row.get("lastChangeDate"),
            "warehouse_name": row.get("warehouseName"),
            "warehouse_type": row.get("warehouseType"),
            "country_name": row.get("countryName"),
            "oblast_okrug_name": row.get("oblastOkrugName"),
            "region_name": row.get("regionName"),
            "supplier_article": row.get("supplierArticle"),
            "nm_id": row.get("nmId"),
            "barcode": row.get("barcode"),
            "category": row.get("category"),
            "subject": row.get("subject"),
            "brand": row.get("brand"),
            "tech_size": row.get("techSize"),
            "income_id": row.get("incomeID"),
            "is_supply": row.get("isSupply"),
            "is_realization": row.get("isRealization"),
            "total_price": _to_decimal(row.get("totalPrice")),
            "discount_percent": _to_decimal(row.get("discountPercent")),
            "spp": _to_decimal(row.get("spp")),
            "payment_sale_amount": _to_decimal(row.get("paymentSaleAmount")),
            "for_pay": _to_decimal(row.get("forPay")),
            "finished_price": _to_decimal(row.get("finishedPrice")),
            "price_with_disc": _to_decimal(row.get("priceWithDisc")),
            "sticker": row.get("sticker"),
            "g_number": row.get("gNumber"),
            "srid": row.get("srid"),
            "updated_at": utcnow(),
        }
