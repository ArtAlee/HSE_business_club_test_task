import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_POINTS = [
    {
        "name": "Предпринимательский лекторий с Борисом Альхимовичем",
        "description": "Выступление Бориса Альхимовича",
        "reward_points": 300,
    },
    {
        "name": "Предпринимательский лекторий с Антоном Козловым",
        "description": "Выступление Антона Козлова",
        "reward_points": 500,
    },
    {
        "name": "Кейс чемпионат",
        "description": "Участие в кейс-чемпионате",
        "reward_points": 1000,
    },
]


def getenv_or_fail(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def create_point(api_url: str, admin_token: str, point: dict) -> None:
    payload = json.dumps(point).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/admin/points",
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
            print(f"created {point['name']}: {response.status} {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        print(f"failed {point['name']}: {exc.code} {body}")


def main() -> int:
    api_url = os.getenv("API_URL", "http://localhost:8000")
    admin_token = getenv_or_fail("ADMIN_TOKEN")

    for point in DEFAULT_POINTS:
        create_point(api_url, admin_token, point)

    print("seed finished")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
