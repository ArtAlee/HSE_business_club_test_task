import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_PRODUCTS = [
    {
        "name": "Футболка HSE Business Club",
        "description": "Белая футболка",
        "price_points": 120,
        "stock": 15,
    },
    {
        "name": "Термокружка",
        "description": "Металлическая термокружка",
        "price_points": 180,
        "stock": 10,
    },
    {
        "name": "Стикерпак",
        "description": "Набор брендированных стикеров",
        "price_points": 40,
        "stock": 50,
    },
    {
        "name": "Шоппер",
        "description": "Тканевый шоппер",
        "price_points": 90,
        "stock": 20,
    },
    {
        "name": "Блокнот",
        "description": "Блокнот",
        "price_points": 70,
        "stock": 25,
    },
    {
        "name": "Ручка",
        "description": "Металлическая ручка HSE",
        "price_points": 35,
        "stock": 60,
    },
]


def getenv_or_fail(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def create_product(api_url: str, admin_token: str, product: dict) -> None:
    payload = json.dumps(product).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/shop/products",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            print(f"created {product['name']}: {response.status} {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        print(f"failed {product['name']}: {exc.code} {body}")


def main() -> int:
    api_url = os.getenv("API_URL", "http://localhost:8000")
    admin_token = getenv_or_fail("ADMIN_TOKEN")

    for product in DEFAULT_PRODUCTS:
        create_product(api_url, admin_token, product)

    print("seed finished")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
