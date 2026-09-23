"""Seed roles, permissions and initial admin/owner."""
import logging
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.config import get_settings
from app.models.user import User, Role, Permission
from app.models.finance import Balance
from app.models.system import StoreSettings, SocialLink

logger = logging.getLogger(__name__)
settings = get_settings()

PERMISSIONS = [
    ("products.read", "Просмотр товаров"),
    ("products.write", "Управление товарами"),
    ("orders.read", "Просмотр заказов"),
    ("orders.write", "Управление заказами"),
    ("payments.read", "Просмотр платежей"),
    ("payments.approve", "Подтверждение платежей"),
    ("refunds.approve", "Подтверждение возвратов"),
    ("customers.read", "Просмотр клиентов"),
    ("couriers.manage", "Управление курьерами"),
    ("delivery.manage", "Управление доставкой"),
    ("analytics.read", "Аналитика"),
    ("settings.write", "Настройки магазина"),
    ("admins.manage", "Управление администраторами"),
    ("owner.full_access", "Полный доступ владельца"),
    ("chat.manage", "Управление чатом"),
    ("crm.manage", "CRM"),
    ("vip.manage", "VIP уровни"),
    ("promotions.manage", "Акции и промокоды"),
]

ROLES = {
    "OWNER": [p[0] for p in PERMISSIONS],
    "ADMIN": [
        "products.read", "products.write",
        "orders.read", "orders.write",
        "payments.read", "payments.approve",
        "refunds.approve",
        "customers.read",
        "couriers.manage", "delivery.manage",
        "analytics.read",
        "settings.write",
        "chat.manage", "crm.manage",
        "vip.manage", "promotions.manage",
    ],
    "COURIER": [
        "orders.read",
        "delivery.manage",
    ],
    "CLIENT": [],
}


async def seed_database(db: AsyncSession) -> None:
    """Create roles, permissions, admin and basic settings if not exist."""
    # Permissions
    perm_map: dict[str, Permission] = {}
    for code, desc in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(code=code, description=desc)
            db.add(perm)
            await db.flush()
        perm_map[code] = perm

    # Roles
    role_map: dict[str, Role] = {}
    for role_name, perm_codes in ROLES.items():
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Role {role_name}")
            db.add(role)
            await db.flush()
        # Attach permissions
        role.permissions = [perm_map[c] for c in perm_codes if c in perm_map]
        role_map[role_name] = role

    await db.flush()

    # Owner / Admin user
    result = await db.execute(select(User).where(User.phone == settings.admin_phone))
    admin = result.scalar_one_or_none()
    if not admin:
        admin = User(
            first_name="Owner",
            last_name="VELORA",
            phone=settings.admin_phone,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
            is_phone_verified=True,
        )
        db.add(admin)
        await db.flush()
        admin.roles = [role_map["OWNER"], role_map["ADMIN"]]
        balance = Balance(user_id=admin.id, amount=Decimal("0.00"))
        db.add(balance)
        logger.info("Created OWNER user: %s", settings.admin_phone)

    # Default store settings
    defaults = {
        "store_name": "VELORA",
        "currency": "TJS",
        "default_delivery_fee": settings.default_delivery_fee,
        "pickup_reservation_days": str(settings.pickup_reservation_days),
        "payment_card": "",
        "payment_phone": "",
        "payment_name": "",
    }
    for key, value in defaults.items():
        result = await db.execute(select(StoreSettings).where(StoreSettings.key == key))
        if not result.scalar_one_or_none():
            db.add(StoreSettings(key=key, value=str(value)))

    # Social links placeholders
    for platform in ("instagram", "tiktok", "telegram", "whatsapp"):
        result = await db.execute(select(SocialLink).where(SocialLink.platform == platform))
        if not result.scalar_one_or_none():
            db.add(SocialLink(platform=platform, url="", is_active=False))

    await db.commit()
    logger.info("Database seed completed")
