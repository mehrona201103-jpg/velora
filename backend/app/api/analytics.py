from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import get_db
from app.models.user import User, Role
from app.models.product import Product
from app.models.order import Order, OrderItem, PaymentStatus, OrderStatus
from app.models.payment import PaymentMethod
from app.api.deps import require_roles

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    total_products = db.query(func.count(Product.id)).scalar() or 0
    published = db.query(func.count(Product.id)).filter(Product.is_published == True).scalar() or 0
    total_customers = db.query(func.count(User.id)).filter(User.role == Role.customer).scalar() or 0

    paid_orders = db.query(Order).filter(Order.payment_status == PaymentStatus.paid).all()
    revenue = sum((float(o.total or 0) for o in paid_orders), 0.0)
    orders_paid_count = len(paid_orders)
    orders_all = db.query(func.count(Order.id)).scalar() or 0
    awaiting = db.query(func.count(Order.id)).filter(Order.payment_status == PaymentStatus.awaiting_review).scalar() or 0

    cost_rows = (
        db.query(func.coalesce(func.sum(Product.purchase_price * OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Order.payment_status == PaymentStatus.paid)
        .scalar()
    )
    cost = float(cost_rows or 0)
    profit = revenue - cost

    top = (
        db.query(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.total_price).label("sum"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.payment_status == PaymentStatus.paid)
        .group_by(OrderItem.product_name)
        .order_by(desc("qty"))
        .limit(8)
        .all()
    )
    top_products = [
        {"name": r[0] or "—", "qty": int(r[1] or 0), "revenue": float(r[2] or 0)}
        for r in top
    ]

    status_counts = (
        db.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )
    orders_by_status = {}
    for s, c in status_counts:
        key = s.value if hasattr(s, "value") else str(s)
        orders_by_status[key] = int(c)

    pay_counts = (
        db.query(Order.payment_status, func.count(Order.id))
        .group_by(Order.payment_status)
        .all()
    )
    orders_by_payment = [
        {"name": (p.value if hasattr(p, "value") else str(p)), "count": int(c)}
        for p, c in pay_counts
    ]

    # "online" = users updated in last 30 minutes (approx)
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    try:
        online = db.query(func.count(User.id)).filter(User.updated_at >= since).scalar() or 0
    except Exception:
        online = 0

    # registrations last 7 days for simple bar
    day_bars = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        cnt = (
            db.query(func.count(User.id))
            .filter(User.created_at >= start, User.created_at < end)
            .scalar()
            or 0
        )
        day_bars.append({"day": day.strftime("%d.%m"), "count": int(cnt)})

    # current month stats
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    month_paid = [o for o in paid_orders if o.created_at and o.created_at >= month_start]
    month_revenue = sum((float(o.total or 0) for o in month_paid), 0.0)
    month_cost_rows = (
        db.query(func.coalesce(func.sum(Product.purchase_price * OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Order.payment_status == PaymentStatus.paid, Order.created_at >= month_start)
        .scalar()
    )
    month_cost = float(month_cost_rows or 0)
    month_profit = month_revenue - month_cost

    return {
        "total_products": total_products,
        "published_products": published,
        "total_customers": total_customers,
        "orders_total": orders_all,
        "orders_paid": orders_paid_count,
        "orders_awaiting_review": awaiting,
        "revenue_tjs": revenue,
        "cost_tjs": cost,
        "profit_tjs": profit,
        "month_label": now.strftime("%m.%Y"),
        "month_revenue_tjs": month_revenue,
        "month_cost_tjs": month_cost,
        "month_profit_tjs": month_profit,
        "month_orders_paid": len(month_paid),
        "top_products": top_products,
        "orders_by_status": orders_by_status,
        "orders_by_payment": orders_by_payment,
        "online_users": online,
        "registrations_7d": day_bars,
    }


@router.get("/month-report")
def month_report(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    """JSON report for a calendar month (defaults to current)."""
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, m + 1, 1, tzinfo=timezone.utc)

    paid = (
        db.query(Order)
        .filter(
            Order.payment_status == PaymentStatus.paid,
            Order.created_at >= start,
            Order.created_at < end,
        )
        .all()
    )
    revenue = sum((float(o.total or 0) for o in paid), 0.0)
    cost = float(
        db.query(func.coalesce(func.sum(Product.purchase_price * OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(
            Order.payment_status == PaymentStatus.paid,
            Order.created_at >= start,
            Order.created_at < end,
        )
        .scalar()
        or 0
    )
    orders_list = [
        {
            "order_number": o.order_number,
            "total": float(o.total or 0),
            "subtotal": float(o.subtotal or 0),
            "delivery_cost": float(o.delivery_cost or 0),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": [
                {
                    "name": it.product_name,
                    "variant": it.variant_name,
                    "qty": it.quantity,
                    "total": float(it.total_price or 0),
                }
                for it in (o.items or [])
            ],
        }
        for o in paid
    ]
    return {
        "period": f"{m:02d}.{y}",
        "orders_paid": len(paid),
        "revenue_tjs": revenue,
        "cost_tjs": cost,
        "profit_tjs": revenue - cost,
        "orders": orders_list,
    }
