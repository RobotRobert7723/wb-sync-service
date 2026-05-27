from __future__ import annotations

from wb_sync.schema import _article_daily_facts_insert_sql, build_schema_sql


def test_schema_contains_article_daily_facts_table():
    schema_sql = build_schema_sql("wb_test")

    assert "create table if not exists wb_test.wb_article_daily_facts" in schema_sql
    assert "primary key (fact_date, account_id, nm_id)" in schema_sql
    assert "create view wb_test.wb_article_daily_facts as" not in schema_sql
    assert "drop view %I.%I" in schema_sql
    assert "wb_article_daily_facts_account_nm_date_idx" in schema_sql
    assert "sales_period_from" not in schema_sql
    assert "logistics_period_from" not in schema_sql
    assert "create view wb_test.v_wb_article_daily_facts_by_uniq_product as" not in schema_sql
    assert "current_setting('wb.debug_uniq_product_id', true)" not in schema_sql
    assert "create view wb_test.v_wb_article_daily_facts_by_uniq_products as" not in schema_sql
    assert "current_setting('wb.debug_uniq_product_ids', true)" not in schema_sql


def test_article_daily_facts_insert_uses_product_details_source():
    insert_sql = _article_daily_facts_insert_sql("wb_test", "wb_article_daily_facts", "      and d.account_id = %s")

    assert "insert into wb_test.wb_article_daily_facts" in insert_sql
    assert "wb_test.v_wb_finance_sales_product_details" in insert_sql
    assert "ordered_units" in insert_sql
    assert "buyout_basis_units" in insert_sql
    assert "order_basis" in insert_sql
    assert "logistics_basis" in insert_sql
    assert "f.uniq_product_id = p.uniq_product_id" in insert_sql
    assert "latest_unit_status" in insert_sql
    assert "unit_logistics_cost" in insert_sql
    assert "logistics_cost_units" in insert_sql
    assert "buyout_percent" in insert_sql
    assert "avg_logistics_cost" in insert_sql
    assert "      and d.account_id = %s" in insert_sql
    assert "where not exists" in insert_sql
    assert "on conflict (fact_date, account_id, nm_id) do nothing" in insert_sql


def test_schema_contains_finance_sales_product_details_view():
    schema_sql = build_schema_sql("wb_test")

    assert "create view wb_test.v_wb_finance_sales_product_details as" in schema_sql
    assert "known_identifier_kiz" in schema_sql
    assert "row_kiz_resolution" in schema_sql
    assert "restored_kiz" in schema_sql
    assert "uniq_product_id" in schema_sql
    assert "'srid'::text" in schema_sql
    assert "'order_id'::text" in schema_sql
    assert "'order_uid'::text" in schema_sql
    assert "'shk_id'::text" in schema_sql
