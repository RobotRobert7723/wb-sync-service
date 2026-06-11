from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from psycopg import sql
from psycopg.types.json import Jsonb

from wb_sync.db import Database
from wb_sync.models import WorkerConfig, WorkerState
from wb_sync.schema import _article_daily_facts_insert_sql
from wb_sync.time_utils import utcnow


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _none_if_empty(value: object) -> object | None:
    if value == "":
        return None
    return value


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

    def checkpoint_run_progress(
        self,
        account_id: int,
        api_type: str,
        run_id: str,
        cursor_timestamp: datetime | None,
        cursor_key: str | None,
    ) -> None:
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update wb_sync_state
                set heartbeat_at = %s,
                    run_id = %s,
                    status = 'running',
                    cursor_timestamp = %s,
                    cursor_key = %s
                where account_id = %s and api_type = %s
                """,
                (utcnow(), run_id, cursor_timestamp, cursor_key, account_id, api_type),
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

    def upsert_finance_sales_report_details(self, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        return self._upsert_finance_rows("wb_finance_sales_report_details", account_id, rows)

    def upsert_finance_sales_report_weekly(self, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        return self._upsert_finance_rows("wb_finance_sales_report_weekly", account_id, rows)

    def replace_warehouse_remains(self, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        snapshot_at = utcnow()
        records = [self._normalize_warehouse_remains_row(account_id, row, warehouse, snapshot_at) for row in rows for warehouse in row.get("warehouses", [])]
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute("delete from wb_warehouse_remains where account_id = %s", (account_id,))
            if records:
                columns = list(records[0].keys())
                insert_sql = sql.SQL(
                    """
                    insert into wb_warehouse_remains ({fields})
                    values ({values})
                    on conflict (account_id, nm_id, barcode, tech_size, warehouse_name) do update set
                    {updates}
                    """
                ).format(
                    fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
                    values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                    updates=sql.SQL(", ").join(
                        sql.SQL("{} = excluded.{}").format(sql.Identifier(col), sql.Identifier(col))
                        for col in columns
                        if col not in {"account_id", "nm_id", "barcode", "tech_size", "warehouse_name"}
                    ),
                )
                cur.executemany(insert_sql, [tuple(record[col] for col in columns) for record in records])
            conn.commit()
        return len(records)

    def get_existing_weekly_report_ids(self, account_id: int, report_ids: Iterable[int]) -> set[int]:
        report_ids = [int(report_id) for report_id in report_ids]
        if not report_ids:
            return set()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select distinct report_id
                from wb_finance_sales_report_weekly
                where account_id = %s
                  and report_id = any(%s)
                """,
                (account_id, report_ids),
            )
            return {int(row["report_id"]) for row in cur.fetchall()}

    def load_article_daily_facts(self, account_id: int) -> int:
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select exists (
                    select 1
                    from wb_article_daily_facts
                    where fact_date = (now() at time zone 'Europe/Moscow')::date
                      and account_id = %s
                ) as already_loaded
                """,
                (account_id,),
            )
            row = cur.fetchone()
            if row and row["already_loaded"]:
                return 0

            cur.execute(
                _article_daily_facts_insert_sql(
                    self.db.schema,
                    "wb_article_daily_facts",
                    "      and d.account_id = %s",
                ),
                (account_id,),
            )
            rows_inserted = cur.rowcount if cur.rowcount is not None and cur.rowcount > 0 else 0
            conn.commit()
            return rows_inserted

    def _upsert_finance_rows(self, table_name: str, account_id: int, rows: Iterable[dict[str, object]]) -> int:
        records = [self._normalize_finance_sales_report_detail(account_id, row) for row in rows]
        if not records:
            return 0
        columns = list(records[0].keys())
        insert_sql = sql.SQL(
            """
            insert into {table_name} ({fields})
            values ({values})
            on conflict (account_id, report_id, rrd_id) do update set
            {updates}
            """
        ).format(
            table_name=sql.Identifier(table_name),
            fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            updates=sql.SQL(", ").join(
                sql.SQL("{} = excluded.{}").format(sql.Identifier(col), sql.Identifier(col))
                for col in columns
                if col not in {"account_id", "report_id", "rrd_id"}
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

    def _normalize_finance_sales_report_detail(self, account_id: int, row: dict[str, object]) -> dict[str, object]:
        return {
            "account_id": account_id,
            "report_id": row.get("reportId"),
            "rrd_id": row.get("rrdId"),
            "date_from": row.get("dateFrom"),
            "date_to": _none_if_empty(row.get("dateTo")),
            "create_date": _none_if_empty(row.get("createDate")),
            "currency": row.get("currency"),
            "report_type": row.get("reportType"),
            "gi_id": row.get("giId"),
            "dlv_prc": _to_decimal(row.get("dlvPrc")),
            "fix_tariff_date_from": _none_if_empty(row.get("fixTariffDateFrom")),
            "fix_tariff_date_to": _none_if_empty(row.get("fixTariffDateTo")),
            "subject_name": row.get("subjectName"),
            "nm_id": row.get("nmId"),
            "brand_name": row.get("brandName"),
            "vendor_code": row.get("vendorCode"),
            "title": row.get("title"),
            "tech_size": row.get("techSize"),
            "sku": row.get("sku"),
            "doc_type_name": row.get("docTypeName"),
            "quantity": row.get("quantity"),
            "retail_price": _to_decimal(row.get("retailPrice")),
            "retail_amount": _to_decimal(row.get("retailAmount")),
            "sale_percent": _to_decimal(row.get("salePercent")),
            "commission_percent": _to_decimal(row.get("commissionPercent")),
            "office_name": row.get("officeName"),
            "seller_oper_name": row.get("sellerOperName"),
            "order_dt": _none_if_empty(row.get("orderDt")),
            "sale_dt": _none_if_empty(row.get("saleDt")),
            "rr_date": _none_if_empty(row.get("rrDate")),
            "shk_id": row.get("shkId"),
            "retail_price_with_disc": _to_decimal(row.get("retailPriceWithDisc")),
            "delivery_amount": _to_decimal(row.get("deliveryAmount")),
            "return_amount": _to_decimal(row.get("returnAmount")),
            "delivery_service": _to_decimal(row.get("deliveryService")),
            "gi_box_type_name": row.get("giBoxTypeName"),
            "product_discount_for_report": _to_decimal(row.get("productDiscountForReport")),
            "seller_promo": _to_decimal(row.get("sellerPromo")),
            "spp": _to_decimal(row.get("spp")),
            "kvw_base": _to_decimal(row.get("kvwBase")),
            "kvw": _to_decimal(row.get("kvw")),
            "sup_rating_up": _to_decimal(row.get("supRatingUp")),
            "is_kgvp_v2": row.get("isKgvpV2"),
            "ppvz_sales_commission": _to_decimal(row.get("ppvzSalesCommission")),
            "for_pay": _to_decimal(row.get("forPay")),
            "ppvz_reward": _to_decimal(row.get("ppvzReward")),
            "acquiring_fee": _to_decimal(row.get("acquiringFee")),
            "acquiring_percent": _to_decimal(row.get("acquiringPercent")),
            "payment_processing": row.get("paymentProcessing"),
            "acquiring_bank": row.get("acquiringBank"),
            "vw": _to_decimal(row.get("vw")),
            "vw_nds": _to_decimal(row.get("vwNds")),
            "ppvz_office_name": row.get("ppvzOfficeName"),
            "ppvz_office_id": row.get("ppvzOfficeId"),
            "ppvz_supplier_name": row.get("ppvzSupplierName"),
            "ppvz_supplier_inn": row.get("ppvzSupplierInn"),
            "declaration_number": row.get("declarationNumber"),
            "bonus_type_name": row.get("bonusTypeName"),
            "sticker_id": row.get("stickerId"),
            "country": row.get("country"),
            "srv_dbs": row.get("srvDbs"),
            "penalty": _to_decimal(row.get("penalty")),
            "additional_payment": _to_decimal(row.get("additionalPayment")),
            "rebill_logistic_cost": _to_decimal(row.get("rebillLogisticCost")),
            "rebill_logistic_org": row.get("rebillLogisticOrg"),
            "paid_storage": _to_decimal(row.get("paidStorage")),
            "deduction": _to_decimal(row.get("deduction")),
            "paid_acceptance": _to_decimal(row.get("paidAcceptance")),
            "order_id": row.get("orderId"),
            "kiz": row.get("kiz"),
            "is_b2b": row.get("isB2b"),
            "trbx_id": row.get("trbxId"),
            "installment_cofinancing_amount": _to_decimal(row.get("installmentCofinancingAmount")),
            "wibes_discount_percent": _to_decimal(row.get("wibesDiscountPercent")),
            "cashback_amount": _to_decimal(row.get("cashbackAmount")),
            "cashback_discount": _to_decimal(row.get("cashbackDiscount")),
            "cashback_commission_change": _to_decimal(row.get("cashbackCommissionChange")),
            "payment_schedule": row.get("paymentSchedule"),
            "delivery_method": row.get("deliveryMethod"),
            "seller_promo_id": row.get("sellerPromoId"),
            "seller_promo_discount": _to_decimal(row.get("sellerPromoDiscount")),
            "loyalty_id": row.get("loyaltyId"),
            "loyalty_discount": _to_decimal(row.get("loyaltyDiscount")),
            "uuid_promocode": row.get("uuidPromocode"),
            "sale_price_promocode_discount_prc": _to_decimal(row.get("salePricePromocodeDiscountPrc")),
            "article_substitution": row.get("articleSubstitution"),
            "sale_price_affiliated_discount_prc": _to_decimal(row.get("salePriceAffiliatedDiscountPrc")),
            "agency_vat": _to_decimal(row.get("agencyVat")),
            "sale_price_wholesale_discount_prc": _to_decimal(row.get("salePriceWholesaleDiscountPrc")),
            "order_uid": row.get("orderUid"),
            "srid": row.get("srid"),
            "raw_payload": Jsonb(json.loads(json.dumps(row, default=str))),
            "updated_at": utcnow(),
        }

    def _normalize_warehouse_remains_row(
        self,
        account_id: int,
        row: dict[str, object],
        warehouse: dict[str, object],
        snapshot_at: datetime,
    ) -> dict[str, object]:
        payload = dict(row)
        payload["warehouse"] = warehouse
        return {
            "account_id": account_id,
            "snapshot_at": snapshot_at,
            "brand": row.get("brand"),
            "subject_name": row.get("subjectName"),
            "vendor_code": row.get("vendorCode"),
            "nm_id": row.get("nmId"),
            "barcode": row.get("barcode"),
            "tech_size": row.get("techSize"),
            "volume": _to_decimal(row.get("volume")),
            "warehouse_name": str(warehouse.get("warehouseName") or ""),
            "quantity": int(warehouse.get("quantity") or 0),
            "raw_payload": Jsonb(json.loads(json.dumps(payload, default=str))),
            "updated_at": utcnow(),
        }
