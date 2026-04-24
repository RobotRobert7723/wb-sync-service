# Развёртывание `wb-sync-service` на Ubuntu VPS

## 1. Что понадобится

- Ubuntu VPS;
- доступ по SSH;
- Docker Engine;
- Docker Compose plugin;
- доступ к PostgreSQL;
- пользователь PostgreSQL с правами на создание схемы и таблиц;
- исходники проекта `wb-sync-service`.

## 2. Получение проекта

Склонируйте проект на сервер:

```bash
git clone <URL_РЕПОЗИТОРИЯ> wb-sync-service
cd wb-sync-service
```

Если репозиторий ещё не опубликован, перенесите исходники проекта на сервер любым удобным способом и перейдите в корневую папку проекта.

## 3. Проверка Docker

На сервере должны быть доступны:

```bash
docker --version
docker compose version
```

Если Docker ещё не установлен, установите его заранее. Установщик проекта сам проверит наличие Docker, но не ставит его автоматически.

## 4. Установка системы

Запустите:

```bash
chmod +x install.sh
./install.sh
```

Установщик задаст вопросы:

- `PostgreSQL host`
- `PostgreSQL port`
- `PostgreSQL database`
- `PostgreSQL user`
- `PostgreSQL password`
- `PostgreSQL schema`

По умолчанию схема production — `wb_prod`.

## 5. Что делает установщик

Установщик:

1. проверяет Docker и Docker Compose;
2. собирает production-конфиг;
3. собирает Docker-образ проекта;
4. подключается к PostgreSQL через контейнер приложения;
5. создаёт схему `wb_prod`, если она отсутствует;
6. создаёт необходимые таблицы проекта;
7. запускает контейнер в фоне;
8. проверяет, что контейнер действительно стартовал.

## 6. Результат установки

После успешной установки:

- создан файл `deploy/.env.production`;
- поднят контейнер сервиса;
- контейнер настроен на автоперезапуск;
- в PostgreSQL существует схема `wb_prod`;
- сервис уже работает и ждёт настройки магазинов.

## 7. Команды эксплуатации

### Посмотреть статус контейнера

```bash
docker compose ps
```

### Посмотреть логи

```bash
docker compose logs -f wb-sync
```

### Перезапустить сервис

```bash
docker compose restart wb-sync
```

### Пересобрать и обновить сервис

```bash
docker compose build --no-cache
docker compose up -d wb-sync
```

### Остановить сервис

```bash
docker compose stop wb-sync
```

### Запустить снова

```bash
docker compose up -d wb-sync
```

## 8. Проверка схемы в БД

После установки можно проверить, что схема создана:

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = 'wb_prod'
order by table_name;
```

Ожидаемые таблицы:

- `wb_accounts`
- `wb_sync_workers`
- `wb_sync_state`
- `wb_sync_runs`
- `wb_orders`
- `wb_sales`

## 9. Что делать дальше

После установки перейдите к пользовательскому руководству и настройте:

1. магазин;
2. токен WB;
3. воркеры `orders` и `sales`.

Документ:

- [Руководство пользователя](user-guide.md)

## 10. Диагностика

### Контейнер не стартует

Проверьте:

- `docker compose logs wb-sync`
- правильность параметров PostgreSQL в `deploy/.env.production`
- доступность PostgreSQL с сервера

### Сервис работает, но загрузка не начинается

Проверьте:

- есть ли записи в `wb_prod.wb_accounts`
- есть ли записи в `wb_prod.wb_sync_workers`
- включены ли они через `enabled = true`
- заполнен ли токен магазина

### Данные не появляются

Проверьте:

- `wb_prod.wb_sync_state`
- `wb_prod.wb_sync_runs`
- логи контейнера

## 11. Важно

- Для production использовать только схему `wb_prod`.
- Dev-схема `wb` не должна использоваться в production-развёртывании.
- Повторный запуск `install.sh` допустим: установка должна быть идемпотентной и не ломать существующее развёртывание.
