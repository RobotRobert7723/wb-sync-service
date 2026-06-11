from __future__ import annotations


def _finance_raw_table_sql(schema: str, table_name: str) -> str:
    index_name = f"{table_name}_account_rrd_idx"
    nm_sale_index_name = f"{table_name}_account_nm_sale_idx"
    nm_report_index_name = f"{table_name}_account_nm_report_idx"
    return f"""
create table if not exists {schema}.{table_name} (
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

create index if not exists {index_name}
    on {schema}.{table_name} (account_id, rrd_id desc);

create index if not exists {nm_sale_index_name}
    on {schema}.{table_name} (account_id, nm_id, sale_dt desc);

create index if not exists {nm_report_index_name}
    on {schema}.{table_name} (account_id, nm_id, rr_date desc);
"""


def _finance_summary_view_sql(schema: str, view_name: str, table_name: str) -> str:
    sale_operation = "\u041f\u0440\u043e\u0434\u0430\u0436\u0430"
    return_operation = "\u0412\u043e\u0437\u0432\u0440\u0430\u0442"
    voluntary_return_compensation = (
        "\u0414\u043e\u0431\u0440\u043e\u0432\u043e\u043b\u044c\u043d\u0430\u044f "
        "\u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f "
        "\u043f\u0440\u0438 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0435"
    )
    loyalty_compensation_operation = (
        "\u041a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f "
        "\u0441\u043a\u0438\u0434\u043a\u0438 \u043f\u043e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435 "
        "\u043b\u043e\u044f\u043b\u044c\u043d\u043e\u0441\u0442\u0438"
    )
    acquiring_adjustment_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u043a\u0430 "
        "\u044d\u043a\u0432\u0430\u0439\u0440\u0438\u043d\u0433\u0430"
    )
    returns_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u043e\u0432"
    )
    sales_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u043f\u0440\u043e\u0434\u0430\u0436"
    )
    report_type_main = "\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439"
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
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
        d.quantity,
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
    from {schema}.{table_name} d
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
        when 1 then '{report_type_main}'
        else max(report_type)::text
    end as report_type_name,
    currency,
    coalesce(sum(retail_amount) filter (where seller_oper_name = '{sale_operation}'), 0)
      - coalesce(sum(retail_amount) filter (where seller_oper_name = '{return_operation}'), 0) as sale_amount,
    coalesce(sum(cashback_amount), 0)
      + case
            when bool_or(seller_oper_name = '{voluntary_return_compensation}')
            then coalesce(
                sum(cashback_discount)
                filter (where seller_oper_name = '{loyalty_compensation_operation}'),
                0
            )
            else 0
        end as loyalty_discount_compensation,
    coalesce(sum(for_pay) filter (where seller_oper_name = '{sale_operation}'), 0)
      - coalesce(sum(for_pay) filter (where seller_oper_name = '{return_operation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{voluntary_return_compensation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{returns_correction_operation}'), 0)
      - coalesce(sum(for_pay) filter (where seller_oper_name = '{sales_correction_operation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{acquiring_adjustment_operation}'), 0) as to_transfer_for_goods,
    case
        when
            (coalesce(sum(retail_price) filter (where seller_oper_name = '{sale_operation}'), 0)
             - coalesce(sum(retail_price) filter (where seller_oper_name = '{return_operation}'), 0)) = 0
        then 0::numeric(18, 2)
        else round(
            (
                1 - (
                    (coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = '{sale_operation}'), 0)
                     - coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = '{return_operation}'), 0))
                    /
                    nullif(
                        coalesce(sum(retail_price) filter (where seller_oper_name = '{sale_operation}'), 0)
                        - coalesce(sum(retail_price) filter (where seller_oper_name = '{return_operation}'), 0),
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
    coalesce(sum(additional_payment), 0) as wb_reward_adjustment,
    0::numeric as loyalty_program_cost,
    coalesce(sum(cashback_commission_change), 0) as loyalty_points_withheld,
    (
        coalesce(sum(for_pay) filter (where seller_oper_name = '{sale_operation}'), 0)
        - coalesce(sum(for_pay) filter (where seller_oper_name = '{return_operation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{voluntary_return_compensation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{returns_correction_operation}'), 0)
        - coalesce(sum(for_pay) filter (where seller_oper_name = '{sales_correction_operation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{acquiring_adjustment_operation}'), 0)
        - coalesce(sum(delivery_service), 0)
        - coalesce(sum(paid_storage), 0)
        - coalesce(sum(paid_acceptance), 0)
        - coalesce(sum(deduction), 0)
        - coalesce(sum(penalty), 0)
        - coalesce(sum(cashback_commission_change), 0)
        + coalesce(sum(cashback_amount), 0)
        + coalesce(sum(additional_payment), 0)
    ) as total_to_pay
from localized
group by
    account_id,
    account_code,
    account_name,
    report_id,
    currency;
"""


def _finance_summary_by_sku_view_sql(schema: str, view_name: str, table_name: str) -> str:
    sale_operation = "\u041f\u0440\u043e\u0434\u0430\u0436\u0430"
    return_operation = "\u0412\u043e\u0437\u0432\u0440\u0430\u0442"
    voluntary_return_compensation = (
        "\u0414\u043e\u0431\u0440\u043e\u0432\u043e\u043b\u044c\u043d\u0430\u044f "
        "\u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f "
        "\u043f\u0440\u0438 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0435"
    )
    loyalty_compensation_operation = (
        "\u041a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f "
        "\u0441\u043a\u0438\u0434\u043a\u0438 \u043f\u043e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435 "
        "\u043b\u043e\u044f\u043b\u044c\u043d\u043e\u0441\u0442\u0438"
    )
    acquiring_adjustment_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u043a\u0430 "
        "\u044d\u043a\u0432\u0430\u0439\u0440\u0438\u043d\u0433\u0430"
    )
    returns_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u043e\u0432"
    )
    sales_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u043f\u0440\u043e\u0434\u0430\u0436"
    )
    report_type_main = "\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439"
    missing_cost_value = "999999999"
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
with localized as (
    select
        d.account_id,
        a.account_code,
        a.account_name,
        d.report_id,
        d.sku,
        d.nm_id,
        d.brand_name,
        d.vendor_code,
        d.title,
        d.tech_size,
        d.currency,
        d.report_type,
        (d.date_from at time zone 'Europe/Moscow')::date as local_date_from,
        (d.date_to at time zone 'Europe/Moscow')::date as local_date_to,
        (d.create_date at time zone 'Europe/Moscow')::date as local_create_date,
        d.seller_oper_name,
        d.quantity,
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
    from {schema}.{table_name} d
    join {schema}.wb_accounts a on a.id = d.account_id
),
aggregated as (
select
    account_id,
    account_code,
    account_name as legal_entity_name,
    report_id,
    sku,
    case when sku = '' then 0 else coalesce(max(nm_id), 0) end as nm_id,
    case when sku = '' then 'N/A' else coalesce(max(nullif(brand_name, '')), 'N/A') end as brand_name,
    case when sku = '' then 'N/A' else coalesce(max(nullif(vendor_code, '')), 'N/A') end as vendor_code,
    case when sku = '' then 'N/A' else coalesce(max(nullif(title, '')), 'N/A') end as title,
    case when sku = '' then 'N/A' else coalesce(max(nullif(tech_size, '')), 'N/A') end as tech_size,
    coalesce(sum(quantity) filter (where seller_oper_name = '{sale_operation}'), 0)
      - coalesce(sum(quantity) filter (where seller_oper_name = '{return_operation}'), 0) as quantity,
    date_trunc('week', min(local_date_from)::timestamp)::date as week_start,
    min(local_date_from) as period_from,
    max(local_date_to) as period_to,
    max(local_create_date) as report_created_date,
    case max(report_type)
        when 1 then '{report_type_main}'
        else max(report_type)::text
    end as report_type_name,
    currency,
    coalesce(sum(retail_amount) filter (where seller_oper_name = '{sale_operation}'), 0)
      - coalesce(sum(retail_amount) filter (where seller_oper_name = '{return_operation}'), 0) as sale_amount,
    coalesce(sum(cashback_amount), 0)
      + case
            when bool_or(seller_oper_name = '{voluntary_return_compensation}')
            then coalesce(
                sum(cashback_discount)
                filter (where seller_oper_name = '{loyalty_compensation_operation}'),
                0
            )
            else 0
        end as loyalty_discount_compensation,
    coalesce(sum(for_pay) filter (where seller_oper_name = '{sale_operation}'), 0)
      - coalesce(sum(for_pay) filter (where seller_oper_name = '{return_operation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{voluntary_return_compensation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{returns_correction_operation}'), 0)
      - coalesce(sum(for_pay) filter (where seller_oper_name = '{sales_correction_operation}'), 0)
      + coalesce(sum(for_pay) filter (where seller_oper_name = '{acquiring_adjustment_operation}'), 0) as to_transfer_for_goods,
    case
        when
            (coalesce(sum(retail_price) filter (where seller_oper_name = '{sale_operation}'), 0)
             - coalesce(sum(retail_price) filter (where seller_oper_name = '{return_operation}'), 0)) = 0
        then 0::numeric(18, 2)
        else round(
            (
                1 - (
                    (coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = '{sale_operation}'), 0)
                     - coalesce(sum(retail_price_with_disc) filter (where seller_oper_name = '{return_operation}'), 0))
                    /
                    nullif(
                        coalesce(sum(retail_price) filter (where seller_oper_name = '{sale_operation}'), 0)
                        - coalesce(sum(retail_price) filter (where seller_oper_name = '{return_operation}'), 0),
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
    coalesce(sum(additional_payment), 0) as wb_reward_adjustment,
    0::numeric as loyalty_program_cost,
    coalesce(sum(cashback_commission_change), 0) as loyalty_points_withheld,
    (
        coalesce(sum(for_pay) filter (where seller_oper_name = '{sale_operation}'), 0)
        - coalesce(sum(for_pay) filter (where seller_oper_name = '{return_operation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{voluntary_return_compensation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{returns_correction_operation}'), 0)
        - coalesce(sum(for_pay) filter (where seller_oper_name = '{sales_correction_operation}'), 0)
        + coalesce(sum(for_pay) filter (where seller_oper_name = '{acquiring_adjustment_operation}'), 0)
        - coalesce(sum(delivery_service), 0)
        - coalesce(sum(paid_storage), 0)
        - coalesce(sum(paid_acceptance), 0)
        - coalesce(sum(deduction), 0)
        - coalesce(sum(penalty), 0)
        - coalesce(sum(cashback_commission_change), 0)
        + coalesce(sum(cashback_amount), 0)
        + coalesce(sum(additional_payment), 0)
    ) as total_to_pay
from localized
group by
    account_id,
    account_code,
    account_name,
    report_id,
    sku,
    currency
)
select
    aggregated.*,
    case
        when aggregated.vendor_code = 'N/A' then 0::numeric(18, 6)
        else coalesce(current_cost.cost, {missing_cost_value}::numeric(18, 6)) * aggregated.quantity::numeric
    end as cost,
    aggregated.total_to_pay - (
        case
            when aggregated.vendor_code = 'N/A' then 0::numeric(18, 6)
            else coalesce(current_cost.cost, {missing_cost_value}::numeric(18, 6)) * aggregated.quantity::numeric
        end
    ) as profit
from aggregated
left join {schema}.v_dic_cost_price_current current_cost
    on current_cost.account_id = aggregated.account_id
   and current_cost.vendor_code = aggregated.vendor_code;
"""


def _finance_sku_reference_view_sql(schema: str, view_name: str, table_name: str) -> str:
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
with normalized as (
    select
        coalesce(nullif(d.sku, ''), 'N/A') as sku,
        d.nm_id,
        d.brand_name,
        d.vendor_code,
        d.title,
        d.tech_size
    from {schema}.{table_name} d
)
select
    sku,
    case when sku = 'N/A' then 0 else coalesce(max(nm_id), 0) end as nm_id,
    case when sku = 'N/A' then 'N/A' else coalesce(max(nullif(brand_name, '')), 'N/A') end as brand_name,
    case when sku = 'N/A' then 'N/A' else coalesce(max(nullif(vendor_code, '')), 'N/A') end as vendor_code,
    case when sku = 'N/A' then 'N/A' else coalesce(max(nullif(title, '')), 'N/A') end as title,
    case when sku = 'N/A' then 'N/A' else coalesce(max(nullif(tech_size, '')), 'N/A') end as tech_size
from normalized
group by sku;
"""


def _cost_price_current_view_sql(schema: str, view_name: str) -> str:
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
select distinct on (d.account_id, d.vendor_code)
    d.account_id,
    d.vendor_code,
    d.cost,
    d.valid_from,
    d.valid_to,
    d.created_at,
    d.updated_at
from {schema}.dic_cost_price d
where d.valid_to is null
order by d.account_id, d.vendor_code, d.valid_from desc, d.id desc;
"""


def _finance_sales_report_weekly_enriched_view_sql(schema: str, view_name: str, table_name: str) -> str:
    sale_operation = "\u041f\u0440\u043e\u0434\u0430\u0436\u0430"
    return_operation = "\u0412\u043e\u0437\u0432\u0440\u0430\u0442"
    voluntary_return_compensation = (
        "\u0414\u043e\u0431\u0440\u043e\u0432\u043e\u043b\u044c\u043d\u0430\u044f "
        "\u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f "
        "\u043f\u0440\u0438 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0435"
    )
    acquiring_adjustment_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u043a\u0430 "
        "\u044d\u043a\u0432\u0430\u0439\u0440\u0438\u043d\u0433\u0430"
    )
    returns_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u043e\u0432"
    )
    sales_correction_operation = (
        "\u041a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f \u043f\u0440\u043e\u0434\u0430\u0436"
    )
    missing_cost_value = "999999999"
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
with base as (
    select
        d.*,
        case
            when nullif(d.vendor_code, '') is null then 0::numeric(18, 6)
            else coalesce(cp.cost, {missing_cost_value}::numeric(18, 6))
        end as unit_cost
    from {schema}.{table_name} d
    left join {schema}.v_dic_cost_price_current cp
        on cp.account_id = d.account_id
       and cp.vendor_code = nullif(d.vendor_code, '')
)
select
    base.*,
    case
        when base.seller_oper_name = '{sale_operation}' then coalesce(base.quantity, 0)::numeric * base.unit_cost
        when base.seller_oper_name = '{return_operation}' then -coalesce(base.quantity, 0)::numeric * base.unit_cost
        else 0::numeric(18, 6)
    end as cost,
    (
        case
            when base.seller_oper_name = '{sale_operation}' then coalesce(base.for_pay, 0)
            when base.seller_oper_name = '{return_operation}' then -coalesce(base.for_pay, 0)
            when base.seller_oper_name = '{voluntary_return_compensation}' then coalesce(base.for_pay, 0)
            when base.seller_oper_name = '{returns_correction_operation}' then coalesce(base.for_pay, 0)
            when base.seller_oper_name = '{sales_correction_operation}' then -coalesce(base.for_pay, 0)
            when base.seller_oper_name = '{acquiring_adjustment_operation}' then coalesce(base.for_pay, 0)
            else 0::numeric(18, 6)
        end
        - coalesce(base.delivery_service, 0)
        - coalesce(base.paid_storage, 0)
        - coalesce(base.paid_acceptance, 0)
        - coalesce(base.deduction, 0)
        - coalesce(base.penalty, 0)
        - coalesce(base.cashback_commission_change, 0)
        + coalesce(base.cashback_amount, 0)
        + coalesce(base.additional_payment, 0)
    ) - (
        case
            when base.seller_oper_name = '{sale_operation}' then coalesce(base.quantity, 0)::numeric * base.unit_cost
            when base.seller_oper_name = '{return_operation}' then -coalesce(base.quantity, 0)::numeric * base.unit_cost
            else 0::numeric(18, 6)
        end
    ) as profit
from base;
"""


def _finance_sales_product_details_view_sql(schema: str, view_name: str, table_name: str) -> str:
    return f"""
drop view if exists {schema}.{view_name};

create view {schema}.{view_name} as
with known_identifier_kiz as (
    select distinct
        d.account_id,
        'srid'::text as match_type,
        nullif(d.srid, '') as match_value,
        nullif(d.kiz, '') as kiz
    from {schema}.{table_name} d
    where nullif(d.kiz, '') is not null
      and nullif(d.srid, '') is not null

    union all

    select distinct
        d.account_id,
        'order_id'::text as match_type,
        d.order_id::text as match_value,
        nullif(d.kiz, '') as kiz
    from {schema}.{table_name} d
    where nullif(d.kiz, '') is not null
      and d.order_id is not null

    union all

    select distinct
        d.account_id,
        'order_uid'::text as match_type,
        nullif(d.order_uid, '') as match_value,
        nullif(d.kiz, '') as kiz
    from {schema}.{table_name} d
    where nullif(d.kiz, '') is not null
      and nullif(d.order_uid, '') is not null

    union all

    select distinct
        d.account_id,
        'shk_id'::text as match_type,
        d.shk_id::text as match_value,
        nullif(d.kiz, '') as kiz
    from {schema}.{table_name} d
    where nullif(d.kiz, '') is not null
      and d.shk_id is not null
),
identifier_kiz_map as (
    select
        account_id,
        match_type,
        match_value,
        max(kiz) as kiz
    from known_identifier_kiz
    group by account_id, match_type, match_value
    having count(distinct kiz) = 1
),
row_kiz_matches as (
    select
        d.id,
        m.kiz
    from {schema}.{table_name} d
    join lateral (
        values
            ('srid'::text, nullif(d.srid, '')),
            ('order_id'::text, d.order_id::text),
            ('order_uid'::text, nullif(d.order_uid, '')),
            ('shk_id'::text, d.shk_id::text)
    ) row_identifier(match_type, match_value) on row_identifier.match_value is not null
    join identifier_kiz_map m
      on m.account_id = d.account_id
     and m.match_type = row_identifier.match_type
     and m.match_value = row_identifier.match_value
    where nullif(d.kiz, '') is null
),
row_kiz_resolution as (
    select
        id,
        case
            when count(distinct kiz) = 1 then max(kiz)
            else null::text
        end as restored_kiz
    from row_kiz_matches
    group by id
),
resolved_rows as (
    select
        d.*,
        coalesce(nullif(d.kiz, ''), r.restored_kiz) as restored_kiz
    from {schema}.{table_name} d
    left join row_kiz_resolution r on r.id = d.id
)
select
    r.*,
    case
        when r.restored_kiz is not null then 'kiz:' || r.restored_kiz
        when r.shk_id is not null then 'shk_id:' || r.shk_id::text
        when nullif(r.srid, '') is not null then 'srid:' || nullif(r.srid, '')
        when r.order_id is not null then 'order_id:' || r.order_id::text
        when nullif(r.order_uid, '') is not null then 'order_uid:' || nullif(r.order_uid, '')
        else 'finance_row:' || r.account_id::text || ':' || r.report_id::text || ':' || r.rrd_id::text
    end as uniq_product_id
from resolved_rows r;
"""


ARTICLE_DAILY_FACT_COLUMNS = (
    "fact_date",
    "account_id",
    "account_code",
    "legal_entity_name",
    "nm_id",
    "brand_name",
    "vendor_code",
    "title",
    "tech_size",
    "buyout_basis_units",
    "ordered_units",
    "logistics_basis_units",
    "buyout_units",
    "returned_units",
    "no_final_status_units",
    "buyout_ratio_sum",
    "buyout_ratio_avg",
    "buyout_percent",
    "delivery_iterations",
    "return_iterations",
    "logistics_iterations",
    "logistics_cost_units",
    "delivery_runs",
    "return_runs",
    "logistics_runs",
    "logistics_cost_total",
    "avg_logistics_cost",
)


def _article_daily_facts_column_list(prefix: str = "") -> str:
    return ",\n".join(f"{prefix}{column}" for column in ARTICLE_DAILY_FACT_COLUMNS)


def _article_daily_facts_select_sql(schema: str, account_id_filter_sql: str = "") -> str:
    sale_operation = "\u041f\u0440\u043e\u0434\u0430\u0436\u0430"
    return_operation = "\u0412\u043e\u0437\u0432\u0440\u0430\u0442"
    return f"""
with snapshot as (
    select
        (now() at time zone 'Europe/Moscow')::date as fact_date
),
finance_rows as (
    select
        d.id,
        d.account_id,
        d.nm_id,
        d.rrd_id,
        d.brand_name,
        d.vendor_code,
        d.title,
        d.tech_size,
        d.uniq_product_id,
        d.seller_oper_name,
        d.quantity,
        d.delivery_amount,
        d.return_amount,
        d.delivery_service,
        (d.order_dt at time zone 'Europe/Moscow')::date as local_order_date,
        (d.sale_dt at time zone 'Europe/Moscow')::date as local_sale_date,
        (coalesce(d.rr_date, d.sale_dt, d.order_dt, d.date_from) at time zone 'Europe/Moscow')::date as local_report_date,
        coalesce(d.rr_date, d.sale_dt, d.order_dt, d.date_from, d.create_date) as event_at
    from {schema}.v_wb_finance_sales_product_details d
    where d.nm_id is not null
      and d.uniq_product_id is not null
{account_id_filter_sql}
),
article_ref as (
    select
        f.account_id,
        f.nm_id,
        coalesce(max(nullif(f.brand_name, '')), 'N/A') as brand_name,
        coalesce(max(nullif(f.vendor_code, '')), 'N/A') as vendor_code,
        coalesce(max(nullif(f.title, '')), 'N/A') as title,
        coalesce(max(nullif(f.tech_size, '')), 'N/A') as tech_size
    from finance_rows f
    group by f.account_id, f.nm_id
),
order_basis as (
    select
        f.account_id,
        f.nm_id,
        f.uniq_product_id
    from finance_rows f
    where f.local_order_date is not null
    group by f.account_id, f.nm_id, f.uniq_product_id
),
logistics_basis as (
    select
        f.account_id,
        f.nm_id,
        f.uniq_product_id
    from finance_rows f
    where (
          coalesce(f.delivery_amount, 0) <> 0
          or coalesce(f.return_amount, 0) <> 0
          or coalesce(f.delivery_service, 0) <> 0
      )
    group by f.account_id, f.nm_id, f.uniq_product_id
),
buyout_basis_products as (
    select
        source.account_id,
        source.nm_id,
        source.uniq_product_id,
        bool_or(source.has_order) as has_order,
        bool_or(source.has_logistics) as has_logistics
        from (
        select
            o.account_id,
            o.nm_id,
            o.uniq_product_id,
            true as has_order,
            false as has_logistics
        from order_basis o

        union all

        select
            l.account_id,
            l.nm_id,
            l.uniq_product_id,
            false as has_order,
            true as has_logistics
        from logistics_basis l
    ) source
    group by source.account_id, source.nm_id, source.uniq_product_id
),
buyout_basis as (
    select
        b.account_id,
        b.nm_id,
        count(*)::bigint as buyout_basis_units,
        count(*) filter (where b.has_order)::bigint as ordered_units,
        count(*) filter (where b.has_logistics)::bigint as logistics_basis_units
    from buyout_basis_products b
    group by b.account_id, b.nm_id
),
unit_logistics as (
    select
        b.account_id,
        b.nm_id,
        b.uniq_product_id,
        coalesce(sum(f.delivery_amount), 0) as delivery_iterations,
        coalesce(sum(f.return_amount), 0) as return_iterations,
        coalesce(sum(f.delivery_service), 0) as logistics_cost_total
    from buyout_basis_products b
    join finance_rows f on f.account_id = b.account_id and f.uniq_product_id = b.uniq_product_id
    group by b.account_id, b.nm_id, b.uniq_product_id
),
unit_sale_flags as (
    select
        b.account_id,
        b.nm_id,
        b.uniq_product_id,
        bool_or(f.seller_oper_name = '{sale_operation}') as has_sale
    from buyout_basis_products b
    join finance_rows f on f.account_id = b.account_id and f.uniq_product_id = b.uniq_product_id
    group by b.account_id, b.nm_id, b.uniq_product_id
),
latest_unit_status as (
    select
        ranked.account_id,
        ranked.uniq_product_id,
        ranked.seller_oper_name as latest_seller_oper_name
    from (
        select
            f.account_id,
            f.uniq_product_id,
            f.seller_oper_name,
            row_number() over (
                partition by f.account_id, f.uniq_product_id
                order by f.event_at desc nulls last, f.rrd_id desc, f.id desc
            ) as rn
        from finance_rows f
        where f.seller_oper_name in ('{sale_operation}', '{return_operation}')
    ) ranked
    where ranked.rn = 1
),
unit_buyout_metrics as (
    select
        b.account_id,
        b.nm_id,
        b.uniq_product_id,
        coalesce(u.delivery_iterations, 0) as delivery_iterations,
        coalesce(u.return_iterations, 0) as return_iterations,
        coalesce(u.delivery_iterations, 0) + coalesce(u.return_iterations, 0) as logistics_iterations,
        coalesce(u.logistics_cost_total, 0) as logistics_cost_total,
        coalesce(sf.has_sale, false) as has_sale,
        s.latest_seller_oper_name,
        case
            when not coalesce(sf.has_sale, false) then 0::numeric
            when s.latest_seller_oper_name = '{sale_operation}'
                 and coalesce(u.delivery_iterations, 0) > 0
            then 1::numeric / u.delivery_iterations
            when (coalesce(u.delivery_iterations, 0) + coalesce(u.return_iterations, 0)) > 0
            then 1::numeric / (coalesce(u.delivery_iterations, 0) + coalesce(u.return_iterations, 0))
            else 0::numeric
        end as unit_buyout_ratio
    from buyout_basis_products b
    left join unit_logistics u on u.account_id = b.account_id and u.uniq_product_id = b.uniq_product_id
    left join unit_sale_flags sf on sf.account_id = b.account_id and sf.uniq_product_id = b.uniq_product_id
    left join latest_unit_status s on s.account_id = b.account_id and s.uniq_product_id = b.uniq_product_id
),
buyout_status as (
    select
        m.account_id,
        m.nm_id,
        count(*) filter (where m.latest_seller_oper_name = '{sale_operation}')::bigint as buyout_units,
        count(*) filter (where m.latest_seller_oper_name = '{return_operation}')::bigint as returned_units,
        count(*) filter (where m.latest_seller_oper_name is null)::bigint as no_final_status_units,
        coalesce(sum(m.unit_buyout_ratio), 0) as buyout_ratio_sum,
        coalesce(avg(m.unit_buyout_ratio), 0) as buyout_ratio_avg,
        coalesce(sum(m.delivery_iterations), 0) as delivery_iterations,
        coalesce(sum(m.return_iterations), 0) as return_iterations,
        coalesce(sum(m.logistics_iterations), 0) as logistics_iterations
    from unit_buyout_metrics m
    group by m.account_id, m.nm_id
),
unit_logistics_cost as (
    select
        p.account_id,
        p.nm_id,
        p.uniq_product_id,
        coalesce(sum(f.delivery_amount), 0) as delivery_runs,
        coalesce(sum(f.return_amount), 0) as return_runs,
        coalesce(sum(f.delivery_service), 0) as logistics_cost_total
    from buyout_basis_products p
    join finance_rows f on f.account_id = p.account_id and f.uniq_product_id = p.uniq_product_id
    group by p.account_id, p.nm_id, p.uniq_product_id
),
logistics_summary as (
    select
        l.account_id,
        l.nm_id,
        count(*)::bigint as logistics_cost_units,
        coalesce(sum(l.delivery_runs), 0) as delivery_runs,
        coalesce(sum(l.return_runs), 0) as return_runs,
        coalesce(sum(l.logistics_cost_total), 0) as logistics_cost_total
    from unit_logistics_cost l
    group by l.account_id, l.nm_id
),
article_keys as (
    select account_id, nm_id from article_ref
    union
    select account_id, nm_id from buyout_basis
    union
    select account_id, nm_id from buyout_status
    union
    select account_id, nm_id from logistics_summary
)
select
    snap.fact_date,
    k.account_id,
    a.account_code,
    a.account_name as legal_entity_name,
    k.nm_id,
    coalesce(r.brand_name, 'N/A') as brand_name,
    coalesce(r.vendor_code, 'N/A') as vendor_code,
    coalesce(r.title, 'N/A') as title,
    coalesce(r.tech_size, 'N/A') as tech_size,
    coalesce(o.buyout_basis_units, 0) as buyout_basis_units,
    coalesce(o.ordered_units, 0) as ordered_units,
    coalesce(o.logistics_basis_units, 0) as logistics_basis_units,
    coalesce(s.buyout_units, 0) as buyout_units,
    coalesce(s.returned_units, 0) as returned_units,
    coalesce(s.no_final_status_units, 0) as no_final_status_units,
    coalesce(s.buyout_ratio_sum, 0) as buyout_ratio_sum,
    round(coalesce(s.buyout_ratio_avg, 0), 4) as buyout_ratio_avg,
    round(coalesce(s.buyout_ratio_avg, 0) * 100, 2) as buyout_percent,
    coalesce(s.delivery_iterations, 0) as delivery_iterations,
    coalesce(s.return_iterations, 0) as return_iterations,
    coalesce(s.logistics_iterations, 0) as logistics_iterations,
    coalesce(l.logistics_cost_units, 0) as logistics_cost_units,
    coalesce(l.delivery_runs, 0) as delivery_runs,
    coalesce(l.return_runs, 0) as return_runs,
    coalesce(l.delivery_runs, 0) + coalesce(l.return_runs, 0) as logistics_runs,
    coalesce(l.logistics_cost_total, 0) as logistics_cost_total,
    case
        when coalesce(s.buyout_units, 0) = 0 then null::numeric(18, 2)
        else round(coalesce(l.logistics_cost_total, 0) / s.buyout_units::numeric, 2)
    end as avg_logistics_cost
from article_keys k
join {schema}.wb_accounts a on a.id = k.account_id
cross join snapshot snap
left join article_ref r on r.account_id = k.account_id and r.nm_id = k.nm_id
left join buyout_basis o on o.account_id = k.account_id and o.nm_id = k.nm_id
left join buyout_status s on s.account_id = k.account_id and s.nm_id = k.nm_id
left join logistics_summary l on l.account_id = k.account_id and l.nm_id = k.nm_id
"""


def _article_daily_facts_table_sql(schema: str, table_name: str) -> str:
    return f"""
do $$
begin
    if exists (
        select 1
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = '{schema}'
          and c.relname = '{table_name}'
          and c.relkind = 'v'
    ) then
        execute format('drop view %I.%I', '{schema}', '{table_name}');
    end if;
end $$;

create table if not exists {schema}.{table_name} (
    fact_date date not null,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    account_code text not null,
    legal_entity_name text not null,
    nm_id bigint not null,
    brand_name text not null,
    vendor_code text not null,
    title text not null,
    tech_size text not null,
    buyout_basis_units bigint not null,
    ordered_units bigint not null,
    logistics_basis_units bigint not null,
    buyout_units bigint not null,
    returned_units bigint not null,
    no_final_status_units bigint not null,
    buyout_ratio_sum numeric(18, 6) not null,
    buyout_ratio_avg numeric(18, 4) not null,
    buyout_percent numeric(18, 2) not null,
    delivery_iterations numeric(18, 6) not null,
    return_iterations numeric(18, 6) not null,
    logistics_iterations numeric(18, 6) not null,
    logistics_cost_units bigint not null,
    delivery_runs numeric(18, 6) not null,
    return_runs numeric(18, 6) not null,
    logistics_runs numeric(18, 6) not null,
    logistics_cost_total numeric(18, 6) not null,
    avg_logistics_cost numeric(18, 2) null,
    primary key (fact_date, account_id, nm_id)
);

create index if not exists wb_article_daily_facts_account_nm_date_idx
    on {schema}.{table_name} (account_id, nm_id, fact_date desc);
"""


def _article_daily_facts_insert_sql(schema: str, table_name: str, account_id_filter_sql: str = "") -> str:
    insert_columns = _article_daily_facts_column_list("    ")
    select_columns = _article_daily_facts_column_list("    facts.")
    return f"""
insert into {schema}.{table_name} (
{insert_columns}
)
select
{select_columns}
from (
{_article_daily_facts_select_sql(schema, account_id_filter_sql)}
) facts
where not exists (
    select 1
    from {schema}.{table_name} existing
    where existing.fact_date = facts.fact_date
      and existing.account_id = facts.account_id
)
on conflict (fact_date, account_id, nm_id) do nothing;
"""


def _browser_etl_schema_sql(schema: str) -> str:
    return f"""
create table if not exists {schema}.browser_sources (
    id bigserial primary key,
    source_code text not null unique,
    source_name text not null,
    url text not null,
    source_type text not null default 'product_page'
        check (source_type in ('product_page', 'wildberries_product')),
    enabled boolean not null default true,
    schedule_seconds integer not null check (schedule_seconds > 0),
    extraction_config jsonb not null default '{{}}'::jsonb,
    revision integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists {schema}.browser_etl_state (
    source_id bigint primary key references {schema}.browser_sources(id) on delete cascade,
    last_started_at timestamptz null,
    last_finished_at timestamptz null,
    last_success_at timestamptz null,
    last_error_at timestamptz null,
    last_error_message text null,
    heartbeat_at timestamptz null,
    run_id text null,
    status text null
);

create table if not exists {schema}.browser_etl_runs (
    id bigserial primary key,
    source_id bigint not null references {schema}.browser_sources(id) on delete cascade,
    run_id text not null,
    started_at timestamptz not null,
    finished_at timestamptz null,
    status text not null,
    rows_written integer not null default 0,
    error_message text null
);

create index if not exists browser_etl_runs_source_started_idx
    on {schema}.browser_etl_runs (source_id, started_at desc);

create table if not exists {schema}.browser_etl_snapshots (
    id bigserial primary key,
    source_id bigint not null references {schema}.browser_sources(id) on delete cascade,
    source_code text not null,
    observed_at timestamptz not null,
    requested_url text not null,
    final_url text not null,
    page_title text null,
    item_key text null,
    item_name text null,
    price numeric(18, 2) null,
    wallet_price numeric(18, 2) null,
    old_price numeric(18, 2) null,
    currency text null,
    availability text null,
    html_sha256 text null,
    raw_payload jsonb not null,
    created_at timestamptz not null default now()
);

alter table {schema}.browser_etl_snapshots
    add column if not exists wallet_price numeric(18, 2) null;

create index if not exists browser_etl_snapshots_source_observed_idx
    on {schema}.browser_etl_snapshots (source_id, observed_at desc);

create index if not exists browser_etl_snapshots_item_observed_idx
    on {schema}.browser_etl_snapshots (source_id, item_key, observed_at desc);

drop view if exists {schema}.v_browser_etl_latest_prices;

create view {schema}.v_browser_etl_latest_prices as
select distinct on (s.source_id)
    s.source_id,
    bs.source_code,
    bs.source_name,
    bs.source_type,
    s.item_key,
    s.item_name,
    s.price,
    s.wallet_price,
    s.old_price,
    s.currency,
    s.availability,
    s.observed_at,
    s.final_url,
    s.page_title
from {schema}.browser_etl_snapshots s
join {schema}.browser_sources bs on bs.id = s.source_id
order by s.source_id, s.observed_at desc, s.id desc;
"""


def build_schema_sql(schema: str) -> str:
    finance_api_types = "'orders', 'sales', 'finance_sales_report_details', 'finance_sales_report_weekly', 'warehouse_remains'"
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
    api_type text not null check (api_type in ({finance_api_types})),
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
    api_type text not null check (api_type in ({finance_api_types})),
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
    api_type text not null check (api_type in ({finance_api_types})),
    run_id text not null,
    started_at timestamptz not null,
    finished_at timestamptz null,
    status text not null,
    rows_written integer not null default 0,
    error_message text null
);

create table if not exists {schema}.dic_cost_price (
    id bigserial primary key,
    account_id bigint null references {schema}.wb_accounts(id) on delete cascade,
    vendor_code text not null,
    cost numeric(18, 6) not null,
    valid_from timestamptz not null default now(),
    valid_to timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (account_id, vendor_code, valid_from)
);

alter table {schema}.dic_cost_price
    add column if not exists account_id bigint null references {schema}.wb_accounts(id) on delete cascade;

alter table {schema}.dic_cost_price
    drop constraint if exists dic_cost_price_vendor_code_valid_from_key;
alter table {schema}.dic_cost_price
    drop constraint if exists dic_cost_price_account_vendor_valid_from_key;
alter table {schema}.dic_cost_price
    add constraint dic_cost_price_account_vendor_valid_from_key
    unique (account_id, vendor_code, valid_from);

drop index if exists dic_cost_price_vendor_current_idx;
create index if not exists dic_cost_price_vendor_current_idx
    on {schema}.dic_cost_price (account_id, vendor_code, valid_from desc)
    where valid_to is null;

alter table {schema}.wb_sync_workers
    drop constraint if exists wb_sync_workers_api_type_check;
alter table {schema}.wb_sync_workers
    add constraint wb_sync_workers_api_type_check
    check (api_type in ({finance_api_types}));

alter table {schema}.wb_sync_state
    drop constraint if exists wb_sync_state_api_type_check;
alter table {schema}.wb_sync_state
    add constraint wb_sync_state_api_type_check
    check (api_type in ({finance_api_types}));

alter table {schema}.wb_sync_runs
    drop constraint if exists wb_sync_runs_api_type_check;
alter table {schema}.wb_sync_runs
    add constraint wb_sync_runs_api_type_check
    check (api_type in ({finance_api_types}));

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

create index if not exists wb_orders_account_nm_order_idx
    on {schema}.wb_orders (account_id, nm_id, order_date desc);

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

create table if not exists {schema}.wb_warehouse_remains (
    id bigserial primary key,
    account_id bigint not null references {schema}.wb_accounts(id) on delete cascade,
    snapshot_at timestamptz not null,
    brand text null,
    subject_name text null,
    vendor_code text null,
    nm_id bigint null,
    barcode text null,
    tech_size text null,
    volume numeric(18,6) null,
    warehouse_name text not null,
    quantity integer not null,
    raw_payload jsonb not null,
    updated_at timestamptz not null default now(),
    unique (account_id, nm_id, barcode, tech_size, warehouse_name)
);

create index if not exists wb_warehouse_remains_account_snapshot_idx
    on {schema}.wb_warehouse_remains (account_id, snapshot_at desc);

create index if not exists wb_warehouse_remains_account_nm_idx
    on {schema}.wb_warehouse_remains (account_id, nm_id, warehouse_name);

{_finance_raw_table_sql(schema, "wb_finance_sales_report_details")}

{_finance_raw_table_sql(schema, "wb_finance_sales_report_weekly")}

insert into {schema}.dic_cost_price (
    account_id,
    vendor_code,
    cost,
    valid_from,
    valid_to,
    created_at,
    updated_at
)
select
    src.account_id,
    legacy.vendor_code,
    legacy.cost,
    legacy.valid_from,
    legacy.valid_to,
    legacy.created_at,
    legacy.updated_at
from {schema}.dic_cost_price legacy
join (
    select distinct account_id, nullif(vendor_code, '') as vendor_code
    from {schema}.wb_finance_sales_report_details
    union
    select distinct account_id, nullif(vendor_code, '') as vendor_code
    from {schema}.wb_finance_sales_report_weekly
) src
    on src.vendor_code = legacy.vendor_code
where legacy.account_id is null
  and src.vendor_code is not null
  and not exists (
      select 1
      from {schema}.dic_cost_price d
      where d.account_id = src.account_id
        and d.vendor_code = legacy.vendor_code
        and d.valid_from = legacy.valid_from
  )
on conflict (account_id, vendor_code, valid_from) do nothing;

delete from {schema}.dic_cost_price
where account_id is null;

insert into {schema}.dic_cost_price (account_id, vendor_code, cost, valid_from)
select distinct src.account_id, src.vendor_code, 999999999::numeric(18, 6), now()
from (
    select distinct account_id, nullif(vendor_code, '') as vendor_code
    from {schema}.wb_finance_sales_report_details
    union
    select distinct account_id, nullif(vendor_code, '') as vendor_code
    from {schema}.wb_finance_sales_report_weekly
) src
where src.vendor_code is not null
  and not exists (
      select 1
      from {schema}.dic_cost_price d
      where d.account_id = src.account_id
        and d.vendor_code = src.vendor_code
        and d.valid_to is null
  )
on conflict (account_id, vendor_code, valid_from) do nothing;

drop view if exists {schema}.wb_finance_sales_report_weekly_enriched;
drop view if exists {schema}.wb_finance_weekly_summary_by_sku;
drop view if exists {schema}.wb_finance_weekly_sku_reference;
drop view if exists {schema}.v_dic_cost_price_current;

{_cost_price_current_view_sql(schema, "v_dic_cost_price_current")}

{_finance_summary_view_sql(schema, "wb_finance_daily_summary", "wb_finance_sales_report_details")}

{_finance_summary_view_sql(schema, "wb_finance_weekly_summary", "wb_finance_sales_report_weekly")}

{_finance_summary_by_sku_view_sql(schema, "wb_finance_weekly_summary_by_sku", "wb_finance_sales_report_weekly")}

{_finance_sales_report_weekly_enriched_view_sql(schema, "wb_finance_sales_report_weekly_enriched", "wb_finance_sales_report_weekly")}

{_finance_sku_reference_view_sql(schema, "wb_finance_weekly_sku_reference", "wb_finance_sales_report_weekly")}

{_finance_sales_product_details_view_sql(schema, "v_wb_finance_sales_product_details", "wb_finance_sales_report_details")}

{_article_daily_facts_table_sql(schema, "wb_article_daily_facts")}

{_browser_etl_schema_sql(schema)}
"""
