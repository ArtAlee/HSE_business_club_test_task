import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def build_init_data(bot_token: str, user: dict) -> str:
    data = {
        "auth_date": str(int(time.time())),
        "query_id": "smoke-test-query",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def assert_status(response, expected_status: int, step: str) -> dict:
    body = response.json()
    print(step, response.status_code, body)
    if response.status_code != expected_status:
        raise RuntimeError(f"{step} failed: expected {expected_status}, got {response.status_code}")
    return body


def main() -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    admin_token = require_env("ADMIN_TOKEN")

    user = {"id": 123456, "first_name": "Ivan", "username": "ivan"}

    with TestClient(app) as client:
        point = assert_status(
            client.post(
                "/api/admin/points",
                headers={"X-Admin-Token": admin_token},
                json={"name": "Point A", "description": "Demo", "reward_points": 50},
            ),
            200,
            "create_point",
        )

        qr = assert_status(
            client.post(
                f"/api/admin/points/{point['id']}/qr-token",
                headers={"X-Admin-Token": admin_token},
            ),
            200,
            "rotate_qr",
        )

        product = assert_status(
            client.post(
                "/api/shop/products",
                headers={"X-Admin-Token": admin_token},
                json={"name": "T-Shirt", "description": "Merch", "price_points": 30, "stock": 2},
            ),
            200,
            "create_product",
        )

        auth = assert_status(
            client.post(
                "/api/auth/telegram",
                json={"init_data": build_init_data(bot_token, user)},
            ),
            200,
            "auth",
        )
        auth_header = {"Authorization": f"Bearer {auth['access_token']}"}

        assert_status(
            client.post("/api/scan", headers=auth_header, json={"token": qr["token"]}),
            200,
            "scan",
        )

        assert_status(
            client.post("/api/scan", headers=auth_header, json={"token": qr["token"]}),
            409,
            "rescan",
        )

        assert_status(client.get("/api/me", headers=auth_header), 200, "me")
        assert_status(client.post(f"/api/shop/redeem/{product['id']}", headers=auth_header), 200, "redeem")
        assert_status(client.get("/api/leaderboard"), 200, "leaderboard")

    print("smoke_test passed")


if __name__ == "__main__":
    main()
