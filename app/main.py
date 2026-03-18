from __future__ import annotations

import secrets
from io import BytesIO
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import qrcode
from sqlalchemy import desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_telegram_init_data
from app.config import get_settings
from app.db import Base, engine, get_db
from app.deps import get_current_user, get_user_balance, require_admin
from app.models import Point, PointVisit, Product, QrToken, Redemption, User
from app.schemas import (
    CabinetResponse,
    LeaderboardItem,
    PointCreate,
    PointRead,
    PurchaseHistoryItem,
    ProductCreate,
    ProductRead,
    RedemptionResponse,
    ScanRequest,
    ScanResponse,
    TelegramAuthRequest,
    TokenResponse,
    VisitHistoryItem,
)


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
MINIAPP_FILE = BASE_DIR / "static" / "miniapp.html"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["System"])
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
@app.get("/mini", include_in_schema=False)
def miniapp_page() -> FileResponse:
    return FileResponse(MINIAPP_FILE)


@app.post(f"{settings.api_prefix}/auth/telegram", response_model=TokenResponse, tags=["Auth"])
def telegram_auth(payload: TelegramAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    telegram_user = verify_telegram_init_data(payload.init_data)

    user = db.scalar(select(User).where(User.telegram_id == telegram_user["id"]))
    if not user:
        user = User(telegram_id=telegram_user["id"])
        db.add(user)

    user.first_name = telegram_user.get("first_name")
    user.last_name = telegram_user.get("last_name")
    user.username = telegram_user.get("username")
    db.commit()

    return TokenResponse(access_token=create_access_token(user.telegram_id))


@app.get(f"{settings.api_prefix}/me", response_model=CabinetResponse, tags=["User"])
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CabinetResponse:
    visits = db.execute(
        select(PointVisit, Point)
        .join(Point, Point.id == PointVisit.point_id)
        .where(PointVisit.user_id == current_user.id)
        .order_by(desc(PointVisit.created_at))
    ).all()
    purchases_rows = db.execute(
        select(Redemption, Product)
        .join(Product, Product.id == Redemption.product_id)
        .where(Redemption.user_id == current_user.id)
        .order_by(desc(Redemption.created_at))
    ).all()

    history = [
        VisitHistoryItem(
            visited_at=visit.created_at,
            point_id=point.id,
            point_name=point.name,
            points_awarded=visit.points_awarded,
        )
        for visit, point in visits
    ]
    purchases = [
        PurchaseHistoryItem(
            purchased_at=redemption.created_at,
            product_id=product.id,
            product_name=product.name,
            points_spent=redemption.points_spent,
        )
        for redemption, product in purchases_rows
    ]
    return CabinetResponse(balance=get_user_balance(db, current_user.id), history=history, purchases=purchases)


@app.post(f"{settings.api_prefix}/scan", response_model=ScanResponse, tags=["User"])
def scan_qr(
    payload: ScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanResponse:
    qr_token = db.scalar(select(QrToken).where(QrToken.token == payload.token))
    if not qr_token or not qr_token.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR token is invalid")

    now = datetime.now(tz=UTC)
    expires_at = qr_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR token expired")

    point = db.get(Point, qr_token.point_id)
    existing_visit = db.scalar(
        select(PointVisit).where(PointVisit.user_id == current_user.id, PointVisit.point_id == point.id)
    )
    if existing_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Вы уже посетили эту точку")

    visit = PointVisit(
        user_id=current_user.id,
        point_id=point.id,
        qr_token_id=qr_token.id,
        points_awarded=point.reward_points,
    )
    db.add(visit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Вы уже посетили эту точку") from exc

    return ScanResponse(
        message="Баллы успешно начислены",
        awarded_points=point.reward_points,
        balance=get_user_balance(db, current_user.id),
        point_id=point.id,
        point_name=point.name,
    )


@app.get(f"{settings.api_prefix}/shop/products", response_model=list[ProductRead], tags=["Shop"])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.id)).all())


@app.post(
    f"{settings.api_prefix}/shop/products",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
    tags=["Admin"],
)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.post(f"{settings.api_prefix}/shop/redeem/{{product_id}}", response_model=RedemptionResponse, tags=["Shop"])
def redeem_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.stock <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Товар закончился")

    balance = get_user_balance(db, current_user.id)
    if balance < product.price_points:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно баллов")

    product.stock -= 1
    redemption = Redemption(user_id=current_user.id, product_id=product.id, points_spent=product.price_points)
    db.add(redemption)
    db.commit()
    db.refresh(product)

    return RedemptionResponse(
        message="Товар успешно обменян",
        product_id=product.id,
        product_name=product.name,
        remaining_stock=product.stock,
        spent_points=product.price_points,
        balance=get_user_balance(db, current_user.id),
    )


@app.post(
    f"{settings.api_prefix}/admin/points",
    response_model=PointRead,
    dependencies=[Depends(require_admin)],
    tags=["Admin"],
)
def create_point(payload: PointCreate, db: Session = Depends(get_db)) -> Point:
    point = Point(**payload.model_dump())
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


@app.post(
    f"{settings.api_prefix}/admin/points/{{point_id}}/qr-code",
    dependencies=[Depends(require_admin)],
    tags=["Admin"],
)
def get_point_qr_code(point_id: int, db: Session = Depends(get_db)) -> Response:
    point = db.get(Point, point_id)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point not found")

    db.execute(update(QrToken).where(QrToken.point_id == point_id, QrToken.is_active.is_(True)).values(is_active=False))
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(tz=UTC) + timedelta(seconds=settings.qr_ttl_seconds)
    qr_token = QrToken(point_id=point_id, token=token, expires_at=expires_at, is_active=True)
    db.add(qr_token)
    db.commit()

    qr_image = qrcode.make(qr_token.token)
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@app.get(f"{settings.api_prefix}/leaderboard", response_model=list[LeaderboardItem], tags=["User"])
def leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[LeaderboardItem]:
    awarded_subquery = (
        select(PointVisit.user_id.label("user_id"), func.coalesce(func.sum(PointVisit.points_awarded), 0).label("awarded"))
        .group_by(PointVisit.user_id)
        .subquery()
    )

    rows = db.execute(
        select(
            User.telegram_id,
            User.first_name,
            User.last_name,
            User.username,
            func.coalesce(awarded_subquery.c.awarded, 0).label("balance"),
        )
        .outerjoin(awarded_subquery, awarded_subquery.c.user_id == User.id)
        .order_by(desc("balance"), User.id)
        .limit(limit)
        .offset(offset)
    ).all()

    return [LeaderboardItem(**row._mapping) for row in rows]
