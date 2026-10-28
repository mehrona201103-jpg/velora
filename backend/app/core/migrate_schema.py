"""
Lightweight schema upgrade for Railway/Postgres.
Adds missing columns without full Alembic migration.
Safe to run on every startup (IF NOT EXISTS style checks).
"""
from sqlalchemy import text, inspect
from app.core.database import engine
from app.core.config import settings


def _column_exists(inspector, table: str, column: str) -> bool:
    try:
        cols = [c["name"] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def _table_exists(inspector, table: str) -> bool:
    try:
        return table in inspector.get_table_names()
    except Exception:
        return False


def upgrade_schema():
    """Add any missing columns/tables introduced after first deploy."""
    inspector = inspect(engine)

    # --- users table new columns ---
    user_columns = {
        "device_type": "VARCHAR(20) DEFAULT 'phone'",
        "avatar_url": "VARCHAR(500)",
        "verification_status": "VARCHAR(20) DEFAULT 'none'",
        "verification_full_name": "VARCHAR(255)",
        "verification_age_confirmed": "BOOLEAN DEFAULT FALSE",
        "verification_passport_selfie": "VARCHAR(500)",
        "verification_passport_front": "VARCHAR(500)",
        "verification_reject_reason": "TEXT",
        "is_verified": "BOOLEAN DEFAULT FALSE",
        "lock_type": "VARCHAR(20)",
        "pin_hash": "VARCHAR(255)",
        "total_orders": "INTEGER DEFAULT 0",
        "total_spent": "NUMERIC(14, 2) DEFAULT 0",
    }

    if _table_exists(inspector, "users"):
        with engine.begin() as conn:
            for col, col_type in user_columns.items():
                if not _column_exists(inspector, "users", col):
                    sql = f'ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}'
                    # SQLite doesn't support IF NOT EXISTS on ADD COLUMN the same way
                    try:
                        if settings.is_sqlite:
                            # re-check for sqlite
                            if not _column_exists(inspect(engine), "users", col):
                                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                        else:
                            conn.execute(text(sql))
                        print(f"[VELORA] Added column users.{col}")
                    except Exception as e:
                        print(f"[VELORA] Skip users.{col}: {e}")

    # --- payment_methods new columns ---
    pm_columns = {
        "code": "VARCHAR(30)",
        "tg_username": "VARCHAR(100)",
        "tg_deep_link": "VARCHAR(300)",
        "stars_per_usd": "DOUBLE PRECISION DEFAULT 100.0",
    }
    if _table_exists(inspector, "payment_methods"):
        with engine.begin() as conn:
            for col, col_type in pm_columns.items():
                if not _column_exists(inspector, "payment_methods", col):
                    try:
                        if settings.is_sqlite:
                            conn.execute(text(f"ALTER TABLE payment_methods ADD COLUMN {col} {col_type}"))
                        else:
                            conn.execute(text(f"ALTER TABLE payment_methods ADD COLUMN IF NOT EXISTS {col} {col_type}"))
                        print(f"[VELORA] Added column payment_methods.{col}")
                    except Exception as e:
                        print(f"[VELORA] Skip payment_methods.{col}: {e}")
            # unique index on code if possible
            try:
                if not settings.is_sqlite:
                    conn.execute(text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_methods_code ON payment_methods (code)"
                    ))
            except Exception:
                pass

    # --- favorites table ---
    if not _table_exists(inspector, "favorites"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """) if not settings.is_sqlite else text("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("[VELORA] Created table favorites")

    # --- product_comments table ---
    if not _table_exists(inspector, "product_comments"):
        with engine.begin() as conn:
            if settings.is_sqlite:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS product_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        image_url VARCHAR(500),
                        is_staff BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS product_comments (
                        id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        text TEXT NOT NULL,
                        image_url VARCHAR(500),
                        is_staff BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            print("[VELORA] Created table product_comments")

    # Refresh payment method codes if empty
    try:
        with engine.begin() as conn:
            if not settings.is_sqlite:
                conn.execute(text("""
                    UPDATE payment_methods SET code = 'dc' WHERE code IS NULL AND name ILIKE '%DC%' OR name ILIKE '%Душанбе%'
                """))
                conn.execute(text("""
                    UPDATE payment_methods SET code = 'eskhata' WHERE code IS NULL AND (name ILIKE '%Эсхата%' OR name ILIKE '%Visa%')
                """))
                conn.execute(text("""
                    UPDATE payment_methods SET code = 'tg_stars' WHERE code IS NULL AND (name ILIKE '%звезд%' OR name ILIKE '%TG%' OR name ILIKE '%Telegram%')
                """))
    except Exception as e:
        print(f"[VELORA] payment code backfill: {e}")

    # --- orders.delivery_quote_status ---
    if _table_exists(inspector, "orders"):
        with engine.begin() as conn:
            if not _column_exists(inspector, "orders", "delivery_quote_status"):
                try:
                    if settings.is_sqlite:
                        conn.execute(text("ALTER TABLE orders ADD COLUMN delivery_quote_status VARCHAR(20) DEFAULT 'none'"))
                    else:
                        conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_quote_status VARCHAR(20) DEFAULT 'none'"))
                    print("[VELORA] Added column orders.delivery_quote_status")
                except Exception as e:
                    print(f"[VELORA] Skip delivery_quote_status: {e}")

    # users extras
    if _table_exists(inspector, "users"):
        with engine.begin() as conn:
            for col, typ in [
                ("telegram_chat_id", "VARCHAR(64)"),
                ("loyalty_points", "INTEGER DEFAULT 0"),
                ("referral_code", "VARCHAR(16)"),
                ("referred_by", "VARCHAR(16)"),
            ]:
                if not _column_exists(inspector, "users", col):
                    try:
                        if settings.is_sqlite:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
                        else:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"))
                        print(f"[VELORA] Added users.{col}")
                    except Exception as e:
                        print(f"[VELORA] Skip {col}: {e}")
    if _table_exists(inspector, "reviews"):
        with engine.begin() as conn:
            if not _column_exists(inspector, "reviews", "image_url"):
                try:
                    if settings.is_sqlite:
                        conn.execute(text("ALTER TABLE reviews ADD COLUMN image_url TEXT"))
                    else:
                        conn.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS image_url TEXT"))
                    print("[VELORA] Added reviews.image_url")
                except Exception as e:
                    print("[VELORA] Skip reviews.image_url", e)
    if _table_exists(inspector, "orders"):
        with engine.begin() as conn:
            if not _column_exists(inspector, "orders", "promo_code"):
                try:
                    if settings.is_sqlite:
                        conn.execute(text("ALTER TABLE orders ADD COLUMN promo_code VARCHAR(32)"))
                    else:
                        conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS promo_code VARCHAR(32)"))
                    print("[VELORA] Added orders.promo_code")
                except Exception as e:
                    print("[VELORA] Skip promo_code", e)
    print("[VELORA] Schema upgrade complete")
