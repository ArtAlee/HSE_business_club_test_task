from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

import jwt
from fastapi import HTTPException, status

from app.config import get_settings


settings = get_settings()


def verify_telegram_init_data(init_data: str) -> dict:
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Telegram hash")

    auth_date = data.get("auth_date")
    if not auth_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Telegram auth_date")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram signature")

    auth_dt = datetime.fromtimestamp(int(auth_date), tz=UTC)
    if datetime.now(tz=UTC) - auth_dt > timedelta(seconds=settings.telegram_auth_max_age_seconds):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram auth data expired")

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Telegram user payload")

    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Telegram user payload") from exc

    if "id" not in user_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram user id is required")
    return user_data


def create_access_token(telegram_id: int) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(telegram_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT subject is missing")
    return int(subject)
