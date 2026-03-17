from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.config import get_settings
from app.db import get_db
from app.models import PointVisit, Redemption, User


settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header is required")

    telegram_id = decode_access_token(credentials.credentials)
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def get_user_balance(db: Session, user_id: int) -> int:
    awarded = db.scalar(select(func.coalesce(func.sum(PointVisit.points_awarded), 0)).where(PointVisit.user_id == user_id)) or 0
    spent = db.scalar(select(func.coalesce(func.sum(Redemption.points_spent), 0)).where(Redemption.user_id == user_id)) or 0
    return int(awarded - spent)
