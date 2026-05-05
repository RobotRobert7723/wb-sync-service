def build_schema_sql(schema: str) -> str:
    return f"""
create schema if not exists {schema};

create table if not exists {schema}.wb_accounts (
    id bigserial primary key,
    account_code text not null unique,
    account_name text not null,
    enabled boolean not null default true,
    token_env_var text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists {schema}.wb_sync_workers (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    api_type text not null check (api_type in ('orders', 'sales', 'finance_sales_report_details')),
    enabled boolean not null default true,
    schedule_seconds integer not null check (schedule_seconds > 0),
    lookback_days integer not null default 30 check (lookback_days > 0),
    batch_limit integer not null default 80000 check (batch_limit > 0),
    revision integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (account_id, api_type)
);

create table if not exists {schema}.wb_sync_state (
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    api_type text not null check (api_type in ('orders', 'sales', 'finance_sales_report_details')),
    cursor_timestamp timestamptz null,
    cursor_key text null,
    last_started_at timestamptz null,
    last_finished_at timestamptz null,
    last_success_at timestamptz null,
    last_error_at timestamptz null,
    last_error_message text null,
    heartbeat_at timestamptz null,
    run_id text null,
    status text null,
    primary key (account_id, api_type)
);

create table if not exists {schema}.wb_sync_runs (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    api_type text not null check (api_type in ('orders', 'sales', 'finance_sales_report_details')),
    run_id text not null,
    started_at timestamptz not null,
    finished_at timestamptz null,
    status text not null,
    rows_written integer not null default 0,
    error_message text null
);

create index if not exists wb_sync_runs_account_api_idx
    on {schema}.wb_sync_runs (account_id, api_type, started_at desc);

create table if not exists {schema}.wb_orders (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    record_key text not null,
    order_date timestamptz null,
    last_change_date timestamptz not null,
    warehouse_name text null,
    warehouse_type text null,
    country_name text null,
    oblast_okrug_name text null,
    region_name text null,
    supplier_article text null,
    nm_id bigint null,
    barcode text null,
    category text null,
    subject text null,
    brand text null,
    tech_size text null,
    income_id bigint null,
    is_supply boolean null,
    is_realization boolean null,
    total_price numeric(18,2) null,
    discount_percent numeric(10,2) null,
    spp numeric(10,2) null,
    finished_price numeric(18,2) null,
    price_with_disc numeric(18,2) null,
    is_cancel boolean null,
    cancel_date timestamptz null,
    sticker text null,
    g_number text null,
    srid text null,
    updated_at timestamptz not null default now(),
    unique (account_id, record_key)
);

create index if not exists wb_orders_account_change_idx
    on {schema}.wb_orders (account_id, last_change_date desc);

create table if not exists {schema}.wb_sales (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    record_key text not null,
    sale_id text null,
    sale_date timestamptz null,
    last_change_date timestamptz not null,
    warehouse_name text null,
    warehouse_type text null,
    country_name text null,
    oblast_okrug_name text null,
    region_name text null,
    supplier_article text null,
    nm_id bigint null,
    barcode text null,
    category text null,
    subject text null,
    brand text null,
    tech_size text null,
    income_id bigint null,
    is_supply boolean null,
    is_realization boolean null,
    total_price numeric(18,2) null,
    discount_percent numeric(10,2) null,
    spp numeric(10,2) null,
    payment_sale_amount numeric(18,2) null,
    for_pay numeric(18,2) null,
    finished_price numeric(18,2) null,
    price_with_disc numeric(18,2) null,
    sticker text null,
    g_number text null,
    srid text null,
    updated_at timestamptz not null default now(),
    unique (account_id, record_key)
);

create index if not exists wb_sales_account_change_idx
    on {schema}.wb_sales (account_id, last_change_date desc);

create table if not exists {schema}.wb_finance_sales_report_details (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    report_id bigint not null,
    rrd_id bigint not null,
    date_from timestamptz null,
    date_to timestamptz null,
    create_date timestamptz null,
    currency text null,
    report_type integer null,
    gi_id bigint null,
    dlv_prc numeric(18,6) null,
    fix_tariff_date_from timestamptz null,
    fix_tariff_date_to timestamptz null,
    subject_name text null,
    nm_id bigint null,
    brand_name text null,
    vendor_code text null,
    title text null,
    tech_size text null,
    sku text null,
    doc_type_name text null,
    quantity integer null,
    retail_price numeric(18,6) null,
    retail_amount numeric(18,6) null,
    sale_percent numeric(18,6) null,
    commission_percent numeric(18,6) null,
    office_name text null,
    seller_oper_name text null,
    order_dt timestamptz null,
    sale_dt timestamptz null,
    rr_date timestamptz null,
    shk_id bigint null,
    retail_price_with_disc numeric(18,6) null,
    delivery_amount numeric(18,6) null,
    return_amount numeric(18,6) null,
    delivery_service numeric(18,6) null,
    gi_box_type_name text null,
    product_discount_for_report numeric(18,6) null,
    seller_promo numeric(18,6) null,
    spp numeric(18,6) null,
    kvw_base numeric(18,6) null,
    kvw numeric(18,6) null,
    sup_rating_up numeric(18,6) null,
    is_kgvp_v2 integer null,
    ppvz_sales_commission numeric(18,6) null,
    for_pay numeric(18,6) null,
    ppvz_reward numeric(18,6) null,
    acquiring_fee numeric(18,6) null,
    acquiring_percent numeric(18,6) null,
    payment_processing text null,
    acquiring_bank text null,
    vw numeric(18,6) null,
    vw_nds numeric(18,6) null,
    ppvz_office_name text null,
    ppvz_office_id bigint null,
    ppvz_supplier_name text null,
    ppvz_supplier_inn text null,
    declaration_number text null,
    bonus_type_name text null,
    sticker_id text null,
    country text null,
    srv_dbs boolean null,
    penalty numeric(18,6) null,
    additional_payment numeric(18,6) null,
    rebill_logistic_cost numeric(18,6) null,
    rebill_logistic_org text null,
    paid_storage numeric(18,6) null,
    deduction numeric(18,6) null,
    paid_acceptance numeric(18,6) null,
    order_id bigint null,
    kiz text null,
    is_b2b boolean null,
    trbx_id text null,
    installment_cofinancing_amount numeric(18,6) null,
    wibes_discount_percent numeric(18,6) null,
    cashback_amount numeric(18,6) null,
    cashback_discount numeric(18,6) null,
    cashback_commission_change numeric(18,6) null,
    payment_schedule text null,
    delivery_method text null,
    seller_promo_id bigint null,
    seller_promo_discount numeric(18,6) null,
    loyalty_id bigint null,
    loyalty_discount numeric(18,6) null,
    uuid_promocode text null,
    sale_price_promocode_discount_prc numeric(18,6) null,
    article_substitution text null,
    sale_price_affiliated_discount_prc numeric(18,6) null,
    agency_vat numeric(18,6) null,
    sale_price_wholesale_discount_prc numeric(18,6) null,
    order_uid text null,
    srid text null,
    raw_payload jsonb not null,
    updated_at timestamptz not null default now(),
    unique (account_id, report_id, rrd_id)
);

create index if not exists wb_finance_sales_report_details_account_rrd_idx
    on {schema}.wb_finance_sales_report_details (account_id, rrd_id desc);

drop view if exists {schema}.wb_finance_weekly_summary;

create or replace view {schema}.wb_finance_weekly_summary as
with localized as (
    select
        d.account_id,
        a.account_code,
        a.account_name,
        d.report_id,
        d.currency,
        d.report_type,
        (d.date_from at time zone 'Europe/Moscow')::date as local_date_from,
        (d.date_to at time zone 'Europe/Moscow')::date as local_date_to,
        (d.create_date at time zone 'Europe/Moscow')::date as local_create_date,
        d.seller_oper_name,
        d.retail_price,
        d.retail_amount,
        d.retail_price_with_disc,
        d.for_pay,
        d.delivery_service,
        d.paid_storage,
        d.deduction,
        d.additional_payment,
        d.paid_acceptance,
        d.penalty,
        d.cashback_amount,
        d.cashback_discount,
        d.cashback_commission_change,
        d.rebill_logistic_cost
    from {schema}.wb_finance_sales_report_details d
    join {schema}.wb_accounts a on a.id = d.account_id
)
select
    account_id,
    account_code,
    account_name as legal_entity_name,
    report_id,
    date_trunc('week', min(local_date_from)::timestamp)::date as week_start,
    min(local_date_from) as period_from,
    max(local_date_to) as period_to,
    max(local_create_date) as report_created_date,
    case max(report_type)
        when 1 then 'Основной'
        else max(report_type)::text
    end as report_type_name,
    currency,
    coalesce(sum(retail_amount) filter (where seller_oper_name = 'Продажа'), 0)
      - coalesce(sum(retail_amount) filter (where seller_oper_name = 'Возврат'), 0) as sale_amount,
    coalesce(sum(cashback_amount), 0) as loyalty_discount_compensation,
    coalesce(sum(for_pay) filter (where seller_oper_name = 'Продажа'), 0)
      - coalesce(sum(for_pay) filter (where seller_oper_name = 'Возврат'), 0) as to_transfer_for_goods,
    case
        when
            (coalesce(sum(retail_price) filter (where seller_oper_name = 'Продажа'), 0)
             - coalesce(sum(retail_price) filter (where seller_oper_name = 'Возврат'), 0)) = 0
        then 0::numeric(18, 2)
        else round(
            (
                1 - (
                    (coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = 'Продажа'), 0)
                     - coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = 'Возврат'), 0))
                    /
                    nullif(
                        coalesce(sum(retail_price) filter (where seller_oper_name = 'Продажа'), 0)
                        - coalesce(sum(retail_price) filter (where seller_oper_name = 'Возврат'), 0),
                        0
                    )
                )
            ) * 100,
            2
        )
    end as agreed_discount_percent,
    coalesce(sum(delivery_service), 0) as logistics_cost,
    coalesce(sum(paid_storage), 0) as storage_cost,
    coalesce(sum(paid_acceptance), 0) as acceptance_cost,
    coalesce(sum(deduction), 0) as other_deductions_payouts,
    coalesce(sum(penalty), 0) as penalties_total,
    coalesce(sum(additional_payment), 0) + coalesce(sum(rebill_logistic_cost), 0) as wb_reward_adjustment,
    coalesce(sum(cashback_discount), 0) as loyalty_program_cost,
    coalesce(sum(cashback_commission_change), 0) as loyalty_points_withheld,
    (
        coalesce(sum(for_pay) filter (where seller_oper_name = 'Продажа'), 0)
        - coalesce(sum(for_pay) filter (where seller_oper_name = 'Возврат'), 0)
        - coalesce(sum(delivery_service), 0)
        - coalesce(sum(paid_storage), 0)
        - coalesce(sum(paid_acceptance), 0)
        - coalesce(sum(deduction), 0)
        - coalesce(sum(penalty), 0)
        - coalesce(sum(cashback_discount), 0)
        - coalesce(sum(cashback_commission_change), 0)
        + coalesce(sum(cashback_amount), 0)
        + coalesce(sum(additional_payment), 0)
        + coalesce(sum(rebill_logistic_cost), 0)
    ) as total_to_pay
from localized
group by
    account_id,
    account_code,
    account_name,
    report_id,
    currency;
"""
