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


def test_schema_contains_browser_etl_tables_and_latest_view():
    schema_sql = build_schema_sql("wb_test")

    assert "create table if not exists wb_test.browser_sources" in schema_sql
    assert "create table if not exists wb_test.browser_etl_state" in schema_sql
    assert "create table if not exists wb_test.browser_etl_runs" in schema_sql
    assert "create table if not exists wb_test.browser_etl_snapshots" in schema_sql
    assert "source_type in ('product_page', 'wildberries_product')" in schema_sql
    assert "wallet_price numeric(18, 2) null" in schema_sql
    assert "add column if not exists wallet_price" in schema_sql
    assert "create view wb_test.v_browser_etl_latest_prices as" in schema_sql
    assert "browser_etl_snapshots_source_observed_idx" in schema_sql


def test_schema_contains_cost_price_dictionary_and_enriched_weekly_views():
    schema_sql = build_schema_sql("wb_test")

    assert "create table if not exists wb_test.dic_cost_price" in schema_sql
    assert "vendor_code text not null" in schema_sql
    assert "cost numeric(18, 6) not null" in schema_sql
    assert "create view wb_test.v_dic_cost_price_current as" in schema_sql
    assert "create view wb_test.wb_finance_sales_report_weekly_enriched as" in schema_sql
    assert "create view wb_test.wb_finance_weekly_summary_by_sku as" in schema_sql
    assert " as cost," in schema_sql
    assert " as profit" in schema_sql
