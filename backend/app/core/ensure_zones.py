"""Районы: Худжанд, Гафуров, Хистеварз, Овчикалача, Сартукай, Унчи, Бустон."""
from sqlalchemy.orm import Session
from app.models.delivery import DeliveryZone
from app.models.payment import PaymentMethod

ALLOWED_ZONES = [
    {"name": "Худжанд", "city": "Худжанд"},
    {"name": "Гафуров", "city": "Гафуров"},
    {"name": "Хистеварз", "city": "Хистеварз"},
    {"name": "Овчикалача", "city": "Овчикалача"},
    {"name": "Сартукай", "city": "Сартукай"},
    {"name": "Унчи", "city": "Унчи"},
    {"name": "Бустон", "city": "Бустон"},
]


def ensure_delivery_zones(db: Session):
    names = {z["name"] for z in ALLOWED_ZONES}
    for z in db.query(DeliveryZone).all():
        if z.name not in names:
            z.is_active = False
            z.base_price = 0
        else:
            z.is_active = True
            z.base_price = 0
            z.delivery_type = "courier"
    for data in ALLOWED_ZONES:
        existing = db.query(DeliveryZone).filter(DeliveryZone.name == data["name"]).first()
        if existing:
            existing.city = data["city"]
            existing.base_price = 0
            existing.is_active = True
            existing.delivery_type = "courier"
            continue
        db.add(DeliveryZone(
            name=data["name"],
            city=data["city"],
            base_price=0,
            free_from_amount=0,
            estimated_days_min=0,
            estimated_days_max=2,
            delivery_type="courier",
            is_active=True,
        ))
    db.commit()


def cleanup_payment_methods(db: Session):
    for pm in db.query(PaymentMethod).all():
        if pm.code not in ("dc", "eskhata", "alif"):
            pm.is_active = False
    db.commit()
