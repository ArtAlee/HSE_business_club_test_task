# HSE Business Club Backend

Небольшой backend для Telegram Mini App. Пользователь сканирует QR-коды на точках форума, получает баллы и тратит их на товары в магазине.

Внутри:
- FastAPI
- PostgreSQL
- JWT-авторизация после проверки Telegram `initData`
- QR-коды с TTL и ротацией
- Mini App frontend прямо внутри сервиса

## Как запустить

Сначала скопируй переменные окружения:

```bash
cp .env.example .env
```

Минимум, что стоит проверить в `.env`:

```env
DATABASE_URL=postgresql+psycopg2://app:app@db:5432/hse_business_club
JWT_SECRET=your-secret
TELEGRAM_BOT_TOKEN=your-bot-token
QR_TTL_SECONDS=120
ADMIN_TOKEN=admin
```

Дальше обычный запуск:

```bash
docker compose up --build
```

После старта:
- Swagger: `http://localhost:8000/docs`
- Mini App: `http://localhost:8000/mini`
- Healthcheck: `http://localhost:8000/health`
- Adminer: `http://localhost:8080`

## Что умеет API

- `POST /api/auth/telegram` — логин через Telegram Mini App
- `GET /api/me` — баланс, история начислений и покупки
- `POST /api/scan` — начисление баллов по QR
- `GET /api/shop/products` — список товаров
- `POST /api/shop/redeem/{product_id}` — обмен баллов на товар
- `GET /api/leaderboard` — рейтинг пользователей

Админские ручки:
- `POST /api/admin/points` — создать точку
- `POST /api/admin/points/{point_id}/qr-code` — выпустить новый QR и сразу получить PNG
- `POST /api/shop/products` — создать товар

## Пара полезных запросов

Создать точку:

```bash
curl -X POST http://localhost:8000/api/admin/points \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: admin' \
  -d '{
    "name": "Стенд 1",
    "description": "Партнёрская зона",
    "reward_points": 50
  }'
```

Сгенерировать QR-картинку:

```bash
curl -X POST http://localhost:8000/api/admin/points/1/qr-code \
  -H 'X-Admin-Token: admin' \
  --output point-1.png
```

Для быстрой ручной проверки в репозитории есть готовый пример QR-кода:
[assets/qr_for_testing.png](/Users/artaleee/projects/test_tasks/HSE_business_club_backend/assets/qr_for_testing.png)

Создать товар:

```bash
curl -X POST http://localhost:8000/api/shop/products \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: admin' \
  -d '{
    "name": "Футболка",
    "description": "Мерч форума",
    "price_points": 100,
    "stock": 10
  }'
```

## Быстрая локальная проверка

Есть smoke test:

```bash
DATABASE_URL=sqlite:////tmp/hse_business_club_smoke.db \
TELEGRAM_BOT_TOKEN=test-bot-token \
ADMIN_TOKEN=admin \
JWT_SECRET=test-secret \
python3 scripts/smoke_test.py
```

И скрипт для заполнения магазина товарами:

```bash
ADMIN_TOKEN=admin python3 scripts/seed_products.py
```

Если API не на `localhost:8000`, можно передать `API_URL`:

```bash
API_URL=https://your-host \
ADMIN_TOKEN=admin \
python3 scripts/seed_products.py
```
