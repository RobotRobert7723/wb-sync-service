# Руководство пользователя `wb-sync-service`

## 1. Что делает система

Сервис автоматически загружает данные из Wildberries API в PostgreSQL.

После установки он постоянно работает в фоне и следит за таблицами настроек. Как только вы добавляете магазин и включаете нужные потоки загрузки, система сама начинает синхронизацию.

## 2. Где хранятся данные

Production-данные находятся в схеме:

```sql
wb_prod
```

Основные таблицы:

- `wb_prod.wb_accounts` — магазины;
- `wb_prod.wb_sync_workers` — настройки потоков;
- `wb_prod.wb_sync_state` — текущее состояние и курсоры;
- `wb_prod.wb_sync_runs` — история запусков;
- `wb_prod.wb_orders` — загруженные заказы;
- `wb_prod.wb_sales` — загруженные продажи.
- `wb_prod.wb_finance_sales_report_details` — детализация финансовых отчётов реализации.

## 3. Как добавить магазин

Добавьте запись в `wb_prod.wb_accounts`.

Пример:

```sql
insert into wb_prod.wb_accounts (
    account_code,
    account_name,
    enabled,
    token_env_var
)
values (
    'shop_1',
    'Магазин 1',
    true,
    'ВАШ_WB_TOKEN'
);
```

### Поле `token_env_var`

В текущей версии туда можно положить:

- либо имя env-переменной;
- либо сам токен WB.

Для пользовательского сценария проще сразу хранить там сам токен WB.

## 4. Как включить загрузку `orders` и `sales`

После добавления магазина создайте воркеры.

### Включить `orders`

```sql
insert into wb_prod.wb_sync_workers (
    account_id,
    api_type,
    enabled,
    schedule_seconds,
    lookback_days,
    batch_limit,
    revision
)
select
    id,
    'orders',
    true,
    300,
    30,
    80000,
    1
from wb_prod.wb_accounts
where account_code = 'shop_1';
```

### Включить `sales`

```sql
insert into wb_prod.wb_sync_workers (
    account_id,
    api_type,
    enabled,
    schedule_seconds,
    lookback_days,
    batch_limit,
    revision
)
select
    id,
    'sales',
    true,
    300,
    30,
    80000,
    1
from wb_prod.wb_accounts
where account_code = 'shop_1';
```

После этого сервис сам подхватит настройки и начнёт загрузку без рестарта.

## 5. Как проверить, что загрузка пошла

### Проверить текущее состояние потоков

```sql
select
    account_id,
    api_type,
    status,
    cursor_timestamp,
    last_success_at,
    last_error_at,
    last_error_message
from wb_prod.wb_sync_state
order by account_id, api_type;
```

### Проверить историю запусков

```sql
select
    account_id,
    api_type,
    status,
    rows_written,
    started_at,
    finished_at,
    error_message
from wb_prod.wb_sync_runs
order by id desc
limit 20;
```

### Проверить, что данные реально появились

```sql
select count(*) from wb_prod.wb_orders;
select count(*) from wb_prod.wb_sales;
select count(*) from wb_prod.wb_finance_sales_report_details;
```

## 6. Как смотреть логи

На сервере:

```bash
docker compose logs -f wb-sync
```

В логах видно:

- старт и остановку worker-ов;
- успешные синхронизации;
- ошибки API и БД;
- число обработанных строк;
- движение курсора.

## 7. Как отключить загрузку

### Отключить только один поток

```sql
update wb_prod.wb_sync_workers
set enabled = false,
    revision = revision + 1
where account_id = 1
  and api_type = 'orders';
```

### Отключить весь магазин

```sql
update wb_prod.wb_accounts
set enabled = false
where id = 1;
```

Сервис сам заметит изменения и остановит соответствующие потоки.

## 8. Как изменить интервал загрузки

```sql
update wb_prod.wb_sync_workers
set schedule_seconds = 600,
    revision = revision + 1
where account_id = 1
  and api_type = 'sales';
```

После изменения `revision` сервис выполняет hot reload и применяет новый интервал без рестарта.

## 9. Что означает `rows_written`

Поле `rows_written` в `wb_prod.wb_sync_runs` показывает число строк, которые были обработаны и записаны через upsert в рамках запуска.

Это не обязательно означает количество только новых строк:

- часть могла быть новой;
- часть могла обновить уже существующие записи.

## 10. Важные замечания

- Первая версия поддерживает только `orders` и `sales`.
- Также поддерживается `finance_sales_report_details` для детализации финансовых отчётов реализации.
- Сервис сохраняет все поля, доступные на сегодня в этих API.
- Если WB добавит новые поля, потребуется обновление проекта.
- Production работает только в схеме `wb_prod`.
