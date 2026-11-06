"""Ensure payment methods: DC, Eskhata (card), Alif. Deactivate TG stars."""
from sqlalchemy.orm import Session
from app.models.payment import PaymentMethod


REQUIRED = [
    {
        "code": "dc",
        "name": "DC (Душанбе Сити)",
        "recipient_name": "VELORA",
        "account_number": "Укажите номер карты DC в админке",
        "instructions": "Переведите точную сумму на карту Душанбе Сити и загрузите скриншот чека.",
        "sort_order": 1,
    },
    {
        "code": "eskhata",
        "name": "Эсхата (карта)",
        "recipient_name": "VELORA",
        "account_number": "Укажите номер карты Эсхата в админке",
        "instructions": "Переведите точную сумму на карту Эсхата и загрузите скриншот перевода.",
        "sort_order": 2,
    },
    {
        "code": "alif",
        "name": "Алиф",
        "recipient_name": "VELORA",
        "account_number": "Укажите реквизиты Алиф в админке",
        "instructions": "Оплата через Алиф. Переведите точную сумму и загрузите скриншот.",
        "sort_order": 3,
    },
]


def ensure_payment_methods(db: Session):
    # deactivate TG stars if present
    for old in db.query(PaymentMethod).filter(PaymentMethod.code == "tg_stars").all():
        old.is_active = False
        if "звезд" in (old.name or "").lower() or "tg" in (old.name or "").lower():
            old.name = old.name or "TG (отключено)"

    for data in REQUIRED:
        existing = db.query(PaymentMethod).filter(PaymentMethod.code == data["code"]).first()
        if existing:
            existing.is_active = True
            # update display name for eskhata (remove Visa)
            if data["code"] == "eskhata":
                existing.name = data["name"]
                if existing.instructions and "Visa" in existing.instructions:
                    existing.instructions = data["instructions"]
            if not existing.name:
                existing.name = data["name"]
            continue

        by_name = None
        if data["code"] == "dc":
            by_name = db.query(PaymentMethod).filter(
                PaymentMethod.name.ilike("%DC%") | PaymentMethod.name.ilike("%Душанбе%")
            ).first()
        elif data["code"] == "eskhata":
            by_name = db.query(PaymentMethod).filter(
                PaymentMethod.name.ilike("%Эсхата%") | PaymentMethod.name.ilike("%Visa%")
            ).first()
        elif data["code"] == "alif":
            by_name = db.query(PaymentMethod).filter(PaymentMethod.name.ilike("%Алиф%") | PaymentMethod.name.ilike("%Alif%")).first()

        if by_name:
            by_name.code = data["code"]
            by_name.name = data["name"]
            by_name.is_active = True
            continue

        pm = PaymentMethod(
            code=data["code"],
            name=data["name"],
            recipient_name=data["recipient_name"],
            account_number=data.get("account_number"),
            instructions=data.get("instructions"),
            is_active=True,
            sort_order=data["sort_order"],
        )
        db.add(pm)
    db.commit()
