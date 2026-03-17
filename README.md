# HSE Business Club Backend

REST API для Telegram Mini App бизнес-форума. Сервис хранит участников, начисляет баллы за посещение точек по QR-кодам, показывает баланс и историю, а также позволяет обменивать баллы на товары в магазине.

## Стек

- FastAPI
- PostgreSQL
- SQLAlchemy ORM
- JWT

## Локальный запуск через Docker Compose

1. Скопировать переменные окружения:

```bash
cp .env.example .env
```

2. При необходимости изменить значения в `.env`:

- `DATABASE_URL` должен указывать на контейнер `db`
- `JWT_SECRET` нужен для подписи JWT
- `TELEGRAM_BOT_TOKEN` нужен для валидации `initData` от Telegram Mini App
- `QR_TTL_SECONDS` задаёт TTL QR-токена
- `ADMIN_TOKEN` используется в заголовке `X-Admin-Token` для админских эндпоинтов

3. Поднять сервисы одной командой:

```bash
docker compose up --build
```

4. После запуска:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Healthcheck: `http://localhost:8000/health`
- Mini App page: `http://localhost:8000/mini`

## Реализованные эндпоинты

- `POST /api/auth/telegram` - авторизация по `initData` Telegram Mini App, выдаёт JWT.
- `GET /api/me` - текущий баланс пользователя и история начислений.
- `POST /api/scan` - начисление баллов по QR-токену, только один раз на точку.
- `GET /api/shop/products` - список товаров магазина.
- `POST /api/shop/products` - создать товар, только администратор.
- `POST /api/shop/redeem/{product_id}` - обменять баллы на товар.
- `POST /api/admin/points` - создать точку начисления, только администратор.
- `POST /api/admin/points/{point_id}/qr-token` - сгенерировать или ротировать QR-токен точки, только администратор.
- `GET /api/admin/points/{point_id}/qr-code` - получить PNG-картинку QR для активного токена точки, только администратор.
- `GET /api/leaderboard?limit=10&offset=0` - рейтинг участников по балансу баллов.

## Примеры curl

### Создать точку

```bash
curl -X POST http://localhost:8000/api/admin/points \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: super-admin-token' \
  -d '{
    "name": "Стенд партнёра 1",
    "description": "Сканирование у стенда",
    "reward_points": 50
  }'
```

### Сгенерировать QR-токен для точки

```bash
curl -X POST http://localhost:8000/api/admin/points/1/qr-token \
  -H 'X-Admin-Token: super-admin-token'
```

### Получить PNG QR-кода для точки

```bash
curl http://localhost:8000/api/admin/points/1/qr-code \
  -H 'X-Admin-Token: super-admin-token' \
  --output point-1.png
```

### Создать товар

```bash
curl -X POST http://localhost:8000/api/shop/products \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: super-admin-token' \
  -d '{
    "name": "Футболка",
    "description": "Мерч форума",
    "price_points": 100,
    "stock": 10
  }'
```

### Авторизация пользователя

`initData` должен приходить из Telegram Mini App. Пример запроса:

```bash
curl -X POST http://localhost:8000/api/auth/telegram \
  -H 'Content-Type: application/json' \
  -d '{
    "init_data": "query_id=AAHdF6IQAAAAAN0XohDhrOrc&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Ivan%22%7D&auth_date=1710000000&hash=replace_me"
  }'
```

### Просканировать QR

```bash
curl -X POST http://localhost:8000/api/scan \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <JWT>' \
  -d '{
    "token": "<qr_token>"
  }'
```

### Получить личный кабинет

```bash
curl http://localhost:8000/api/me \
  -H 'Authorization: Bearer <JWT>'
```

### Обменять баллы на товар

```bash
curl -X POST http://localhost:8000/api/shop/redeem/1 \
  -H 'Authorization: Bearer <JWT>'
```

## Smoke test

Для быстрого локального прогона без Docker можно использовать готовый скрипт [scripts/smoke_test.py](/Users/artaleee/projects/test_tasks/HSE_business_club_backend/scripts/smoke_test.py):

```bash
DATABASE_URL=sqlite:////tmp/hse_business_club_smoke.db \
TELEGRAM_BOT_TOKEN=test-bot-token \
ADMIN_TOKEN=super-admin-token \
JWT_SECRET=test-secret \
python3 scripts/smoke_test.py
```

Скрипт последовательно проверяет:

- создание точки
- ротацию QR-токена
- создание товара
- авторизацию через Telegram `initData`
- первое и повторное сканирование
- личный кабинет
- обмен баллов на товар
- leaderboard

## Принятые решения

- Баланс считается как сумма начислений минус сумма списаний.
- Повторный визит на ту же точку запрещён на уровне БД и API.
- Ротация QR-токена помечает предыдущие активные токены неактивными.
- Для админских операций используется простой заголовок `X-Admin-Token`, потому что отдельная admin-auth схема в задаче не задана.
