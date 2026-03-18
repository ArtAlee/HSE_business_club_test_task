# HSE Business Club Backend

Backend для Telegram Mini App (+примитивный frontend для мини аппа). Пользователь сканирует QR-коды на точках форума, получает баллы и тратит их на товары в магазине.

Стек:
- FastAPI
- PostgreSQL
- Telegram Mini App 

## Как запустить

Cкопировать переменные окружения:

```bash
cp .env.example .env
```

Опционально, изменить содержимое в `.env`:

```env
DATABASE_URL=postgresql+psycopg2://app:app@db:5432/hse_business_club
JWT_SECRET=your-secret
TELEGRAM_BOT_TOKEN=your-bot-token
QR_TTL_SECONDS=120
ADMIN_TOKEN=admin
```

Запустить сервис черещ docker compose:

```bash
docker compose up --build -d
```

После старта:
- Swagger: `http://localhost:8000/docs`
- Mini App (front): `http://localhost:8000/mini`
- Healthcheck: `http://localhost:8000/health`

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
![Тестовый QR-код](assets/qr_for_testing.png)

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

Smoke test:

```bash
DATABASE_URL=sqlite:////tmp/hse_business_club_smoke.db \
TELEGRAM_BOT_TOKEN=test-bot-token \
ADMIN_TOKEN=admin \
JWT_SECRET=test-secret \
python3 scripts/smoke_test.py
```

Cкрипт для заполнения магазина товарами:

```bash
ADMIN_TOKEN=admin python3 scripts/seed_products.py
```

Cкрипт для создания тестовых точек:

```bash
ADMIN_TOKEN=admin python3 scripts/seed_points.py
```