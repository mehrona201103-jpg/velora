from sqlalchemy.orm import Session
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.migrate_schema import upgrade_schema
from app.core.ensure_payments import ensure_payment_methods
from app.core.ensure_zones import ensure_delivery_zones, cleanup_payment_methods
from app.core.database import get_db, SessionLocal  # get_db for media
from app.core.database import engine, Base, SessionLocal
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.payment import PaymentMethod
from app.models.delivery import DeliveryZone
from app.models.product import Category, Product
from app.models.settings import AppSetting

from app.api import auth, products, cart, orders, admin, reviews, favorites, analytics, visual_search, promo, telegram_bot
from app.api.reviews import ProductComment


def create_owner_if_needed():
    """Create owner if missing; always sync password from env so login never drifts."""
    email = (settings.OWNER_EMAIL or settings.FIRST_OWNER_EMAIL or "owner@velora.tj").strip()
    password = (settings.OWNER_PASSWORD or settings.FIRST_OWNER_PASSWORD or "ChangeThisStrongPassword123!").strip()
    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.role == Role.owner).first()
        if not owner:
            owner = db.query(User).filter(User.email == email).first()
        if not owner:
            owner = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="VELORA Owner",
                role=Role.owner,
                is_active=True,
                device_type="pc",
            )
            db.add(owner)
            db.commit()
            print(f"[VELORA] Owner created: {email}")
        else:
            owner.email = email
            owner.role = Role.owner
            owner.is_active = True
            owner.hashed_password = hash_password(password)
            db.commit()
            print(f"[VELORA] Owner credentials synced: {email}")
    finally:
        db.close()


def seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(Category).count() == 0:
            cats = [
                Category(name_ru="Женская одежда", slug="women", sort_order=1),
            ]
            db.add_all(cats)
            db.commit()


        # always ensure women's clothing category
        if not db.query(Category).filter(Category.slug == "women").first():
            db.add(Category(name_ru="Женская одежда", slug="women", sort_order=1))
            db.commit()

        if db.query(PaymentMethod).count() == 0:
            methods = [
                PaymentMethod(
                    code="dc",
                    name="DC (Душанбе Сити)",
                    recipient_name="VELORA",
                    account_number="Укажите номер карты DC в админке",
                    instructions="Переведите точную сумму на карту Душанбе Сити и загрузите скриншот.",
                    is_active=True,
                    sort_order=1,
                ),
                PaymentMethod(
                    code="eskhata",
                    name="Эсхата (карта)",
                    recipient_name="VELORA",
                    account_number="Укажите номер карты Эсхата в админке",
                    instructions="Переведите точную сумму на карту Эсхата и загрузите скриншот.",
                    is_active=True,
                    sort_order=2,
                ),
                PaymentMethod(
                    code="alif",
                    name="Алиф",
                    recipient_name="VELORA",
                    account_number="Укажите реквизиты Алиф в админке",
                    instructions="Оплата через Алиф. Переведите точную сумму и загрузите скриншот.",
                    is_active=True,
                    sort_order=3,
                ),
            ]
            db.add_all(methods)
            db.commit()

        if db.query(DeliveryZone).count() == 0:
            zones = [
                DeliveryZone(name="Худжанд", city="Худжанд", base_price=0, free_from_amount=0, estimated_days_min=0, estimated_days_max=2),
                DeliveryZone(name="Гафуров", city="Гафуров", base_price=0, free_from_amount=0, estimated_days_min=0, estimated_days_max=2),
                DeliveryZone(name="Бустон", city="Бустон", base_price=0, free_from_amount=0, estimated_days_min=0, estimated_days_max=2),
                DeliveryZone(name="Гулистон", city="Гулистон", base_price=0, free_from_amount=0, estimated_days_min=0, estimated_days_max=2),
                DeliveryZone(name="Хистеварз", city="Хистеварз", base_price=0, free_from_amount=0, estimated_days_min=0, estimated_days_max=2),
            ]
            db.add_all(zones)
            db.commit()

        defaults = {
            "telegram_channel_url": "https://instagram.com/_velora_shop.tj",
            "telegram_admin_dm": "https://wa.me/992918781009",
            "instagram_url": "https://instagram.com/_velora_shop.tj",
            "office_address": "Саховат 35, солаги A18, Худжанд",
            "about_text": "VELORA — магазин женской одежды. Доставка по Таджикистану. WhatsApp: 918 78 10 09. Instagram: @_velora_shop.tj",
        }
        for k, v in defaults.items():
            if not db.query(AppSetting).filter(AppSetting.key == k).first():
                db.add(AppSetting(key=k, value=v))
        db.commit()

        if db.query(Product).count() == 0:
            from decimal import Decimal
            cat = db.query(Category).filter(Category.slug == "women").first()
            demo = Product(
                sku="VELORA-DEMO-001",
                name_ru="Платье миди (демо)",
                description_ru="Женское платье. Демо-товар VELORA — замените в админке.",
                category_id=cat.id if cat else None,
                purchase_price=Decimal("120.00"),
                price=Decimal("299.00"),
                discount_percent=10,
                stock=20,
                is_published=True,
                delivery_days_min=1,
                delivery_days_max=3,
            )
            db.add(demo)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade_schema()
    try:
        ProductComment.__table__.create(bind=engine, checkfirst=True)
    except Exception as e:
        print("[VELORA] product_comments:", e)
    create_owner_if_needed()
    seed_demo_data()
    try:
        _db = SessionLocal()
        ensure_payment_methods(_db)
        cleanup_payment_methods(_db)
        ensure_delivery_zones(_db)
        _db.close()
    except Exception as e:
        print("[VELORA] ensure_payments/zones:", e)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "receipts").mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "avatars").mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "verification").mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "products").mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "visual_search").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="VELORA API",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        settings.cors_origins_list + ["*"]
        if settings.ENVIRONMENT == "development"
        else settings.cors_origins_list
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(cart.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(reviews.router, prefix=settings.API_V1_PREFIX)
app.include_router(favorites.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(visual_search.router, prefix=settings.API_V1_PREFIX)
app.include_router(promo.router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram_bot.router, prefix=settings.API_V1_PREFIX)


@app.get("/api/v1/media/{media_id}")
def serve_media(media_id: int, db: Session = Depends(get_db)):
    from app.models.media import MediaBlob
    from fastapi.responses import Response
    blob = db.query(MediaBlob).filter(MediaBlob.id == media_id).first()
    if not blob:
        raise HTTPException(404, "Файл не найден")
    return Response(content=blob.data, media_type=blob.content_type or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=86400"})


upload_path = Path(settings.UPLOAD_DIR)
if upload_path.exists():
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok", "service": "VELORA", "version": settings.VERSION}




def _setup_telegram_webhook():
    """Register Telegram webhook so /start and buttons work."""
    try:
        token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not token:
            print("[VELORA] TELEGRAM_BOT_TOKEN empty — bot offline until token is set")
            return
        base = (getattr(settings, "PUBLIC_BASE_URL", None) or "https://velora-tj.up.railway.app").rstrip("/")
        url = f"{base}/api/v1/telegram/webhook"
        import httpx
        with httpx.Client(timeout=20) as client:
            info = client.get(f"https://api.telegram.org/bot{token}/getMe")
            print("[VELORA] bot getMe:", info.status_code, info.text[:180])
            r = client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={
                    "url": url,
                    "allowed_updates": ["message", "callback_query", "edited_message"],
                    "drop_pending_updates": True,
                },
            )
            print("[VELORA] Telegram webhook set:", url, r.status_code, r.text[:250])
            w = client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
            print("[VELORA] webhook info:", w.text[:300])
    except Exception as e:
        print("[VELORA] webhook setup failed:", e)


@app.on_event("startup")
def _tg_webhook_startup():
    _setup_telegram_webhook()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/.well-known/assetlinks.json")
async def assetlinks():
    """For Android TWA / PWABuilder — hide URL bar when fingerprint matches."""
    path = STATIC_DIR / ".well-known" / "assetlinks.json"
    if path.is_file():
        from fastapi.responses import FileResponse
        return FileResponse(path, media_type="application/json")
    return JSONResponse([])

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path == "health":
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = STATIC_DIR / "index.html"
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(index)
