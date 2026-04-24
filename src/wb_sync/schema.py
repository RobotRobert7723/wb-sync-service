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
    api_type text not null check (api_type in ('orders', 'sales')),
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
    api_type text not null check (api_type in ('orders', 'sales')),
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
    api_type text not null check (api_type in ('orders', 'sales')),
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
"""
