"""VELORA FastAPI application entrypoint."""
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.database import engine, AsyncSessionLocal
from app.core.seed import seed_database
from app.api import health, auth, users, products, balance, cart, orders, admin_products, ai, uploads, maps, favorites, categories, reviews, promotions, admin_orders, couriers, crm, chat, i18n

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with AsyncSessionLocal() as session:
            await seed_database(session)
    except Exception as e:
        logger.warning("Seed skipped or failed (run migrations first): %s", e)
    yield
    await engine.dispose()


app = FastAPI(
    title="VELORA API",
    description="Production-oriented women's fashion e-commerce platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(balance.router, prefix="/api/v1/balance", tags=["Balance"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(admin_products.router, prefix="/api/v1/admin/products", tags=["Admin Products"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["Uploads"])
app.include_router(maps.router, prefix="/api/v1/maps", tags=["Maps"])
app.include_router(favorites.router, prefix="/api/v1/favorites", tags=["Favorites"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["Reviews"])
app.include_router(promotions.router, prefix="/api/v1/promotions", tags=["Promotions"])
app.include_router(admin_orders.router, prefix="/api/v1/admin/orders", tags=["Admin Orders"])
app.include_router(couriers.router, prefix="/api/v1/couriers", tags=["Couriers"])
app.include_router(crm.router, prefix="/api/v1/crm", tags=["CRM"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(i18n.router, prefix="/api/v1/i18n", tags=["i18n"])


@app.get("/")
async def storefront():
    """Serve VELORA storefront UI."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html")
    return {
        "name": "VELORA API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "message": "Storefront static files not found",
    }



@app.get("/admin")
async def admin_panel():
    f = STATIC_DIR / "admin.html"
    if f.exists():
        return FileResponse(f, media_type="text/html")
    return {"error": "admin panel missing"}


@app.get("/courier")
async def courier_panel():
    f = STATIC_DIR / "courier.html"
    if f.exists():
        return FileResponse(f, media_type="text/html")
    return {"error": "courier panel missing"}


@app.get("/owner")
async def owner_panel():
    f = STATIC_DIR / "owner.html"
    if f.exists():
        return FileResponse(f, media_type="text/html")
    return {"error": "owner panel missing"}

# Static assets (if any)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
