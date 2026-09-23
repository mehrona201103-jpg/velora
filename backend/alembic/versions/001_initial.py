"""Initial schema for VELORA

Revision ID: 001
Revises:
Create Date: 2026-09-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("language", sa.String(5), server_default="ru"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # association tables
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_ru", sa.String(150), nullable=False),
        sa.Column("name_tg", sa.String(150), nullable=True),
        sa.Column("name_en", sa.String(150), nullable=True),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    # colors & sizes
    op.create_table(
        "colors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_ru", sa.String(50), nullable=False),
        sa.Column("name_tg", sa.String(50), nullable=True),
        sa.Column("name_en", sa.String(50), nullable=True),
        sa.Column("hex_code", sa.String(7), nullable=True),
    )
    op.create_table(
        "sizes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(20), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )

    # products
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_tg", sa.String(255), nullable=True),
        sa.Column("name_en", sa.String(255), nullable=True),
        sa.Column("description_ru", sa.Text(), nullable=True),
        sa.Column("description_tg", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_featured", sa.Boolean(), server_default="false"),
        sa.Column("is_new", sa.Boolean(), server_default="false"),
        sa.Column("size_chart", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
    )
    op.create_table(
        "product_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("thumbnail_key", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("color_id", sa.Integer(), sa.ForeignKey("colors.id"), nullable=True),
        sa.Column("size_id", sa.Integer(), sa.ForeignKey("sizes.id"), nullable=True),
        sa.Column("sku", sa.String(50), nullable=False, unique=True),
        sa.Column("price_override", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.UniqueConstraint("product_id", "color_id", "size_id", name="uq_variant"),
    )

    # inventory
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),  # FK added later
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # cart
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),
    )
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "product_id", name="uq_favorite"),
    )

    # orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(30), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("delivery_type", sa.String(20), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(12, 2), server_default="0.00"),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0.00"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="TJS"),
        sa.Column("promo_code", sa.String(50), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("latitude", sa.String(30), nullable=True),
        sa.Column("longitude", sa.String(30), nullable=True),
        sa.Column("pickup_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qr_code", sa.String(100), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
    )

    # finance
    op.create_table(
        "balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("balance_id", sa.Integer(), sa.ForeignKey("balances.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_balance_transactions_user_id", "balance_transactions", ["user_id"])

    op.create_table(
        "payment_topup_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("receipt_storage_key", sa.String(500), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("processed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_topup_requests_user_id", "payment_topup_requests", ["user_id"])

    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topup_request_id", sa.Integer(), sa.ForeignKey("payment_topup_requests.id"), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="REQUESTED"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("processed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # delivery
    op.create_table(
        "couriers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(20), server_default="OFFLINE"),
        sa.Column("vehicle_type", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "courier_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("courier_id", sa.Integer(), sa.ForeignKey("couriers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("courier_id", sa.Integer(), sa.ForeignKey("couriers.id"), nullable=True),
        sa.Column("status", sa.String(30), server_default="PENDING"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("courier_earning", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # system
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("object_type", sa.String(50), nullable=True),
        sa.Column("object_id", sa.Integer(), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "store_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("image_key", sa.String(500), nullable=False),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "social_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(50), nullable=False, unique=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("type", sa.String(50), server_default="info"),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("social_links")
    op.drop_table("banners")
    op.drop_table("store_settings")
    op.drop_table("audit_logs")
    op.drop_table("deliveries")
    op.drop_table("courier_locations")
    op.drop_table("couriers")
    op.drop_table("refunds")
    op.drop_table("payment_receipts")
    op.drop_table("payment_topup_requests")
    op.drop_table("balance_transactions")
    op.drop_table("balances")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("favorites")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("inventory_reservations")
    op.drop_table("inventory")
    op.drop_table("product_variants")
    op.drop_table("product_videos")
    op.drop_table("product_images")
    op.drop_table("products")
    op.drop_table("sizes")
    op.drop_table("colors")
    op.drop_table("categories")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
