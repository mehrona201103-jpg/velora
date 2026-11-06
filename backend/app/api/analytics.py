from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.core.database import get_db
from app.models.user import User, Role
from app.models.product import Product
from app.models.order import Order, OrderItem, PaymentStatus, OrderStatus
from app.models.payment import PaymentMethod
from app.models.settings import AppSetting
from app.api.deps import require_roles

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])


def _stats_since(db: Session) -> datetime | None:
    """If admin cleared stats, only count from this moment."""
    row = db.query(AppSetting).filter(AppSetting.key == "analytics_reset_at").first()
    if not row or not row.value:
        return None
    try:
        s = row.value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    # Products always show (catalog size is not financial stats)
    total_products = db.query(func.count(Product.id)).scalar() or 0
    published = db.query(func.count(Product.id)).filter(Product.is_published == True).scalar() or 0

    reset_at = _stats_since(db)

    # Customers: only after reset (so clear → 0 until new signups)
    cust_q = db.query(func.count(User.id)).filter(User.role == Role.customer)
    if reset_at is not None:
        cust_q = cust_q.filter(User.created_at >= reset_at)
    total_customers = cust_q.scalar() or 0

    paid_q = db.query(Order).filter(Order.payment_status == PaymentStatus.paid)
    if reset_at is not None:
        paid_q = paid_q.filter(Order.created_at >= reset_at)
    paid_orders = paid_q.all()

    # Product sales (subtotal) — without delivery; delivery tracked separately
    revenue = sum((float(o.subtotal or 0) for o in paid_orders), 0.0)
    delivery_revenue = sum((float(o.delivery_cost or 0) for o in paid_orders), 0.0)
    revenue_with_delivery = sum((float(o.total or 0) for o in paid_orders), 0.0)
    orders_paid_count = len(paid_orders)

    orders_all_q = db.query(func.count(Order.id))
    if reset_at is not None:
        orders_all_q = orders_all_q.filter(Order.created_at >= reset_at)
    orders_all = orders_all_q.scalar() or 0

    awaiting_q = db.query(func.count(Order.id)).filter(
        Order.payment_status == PaymentStatus.awaiting_review
    )
    if reset_at is not None:
        awaiting_q = awaiting_q.filter(Order.created_at >= reset_at)
    awaiting = awaiting_q.scalar() or 0

    # Cost only from the same paid orders window — if no paid orders, force 0
    if orders_paid_count == 0:
        cost = 0.0
        revenue = 0.0
        delivery_revenue = 0.0
        revenue_with_delivery = 0.0
        profit = 0.0
        top_products = []
    else:
        cost_q = (
            db.query(func.coalesce(func.sum(Product.purchase_price * OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .filter(Order.payment_status == PaymentStatus.paid)
        )
        if reset_at is not None:
            cost_q = cost_q.filter(Order.created_at >= reset_at)
        cost = float(cost_q.scalar() or 0)
        # Наценка = продажи товаров (без доставки) − закупка
        profit = revenue - cost

        top_q = (
            db.query(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.total_price).label("sum"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.payment_status == PaymentStatus.paid)
        )
        if reset_at is not None:
            top_q = top_q.filter(Order.created_at >= reset_at)
        top = (
            top_q.group_by(OrderItem.product_name)
            .order_by(desc("qty"))
            .limit(8)
            .all()
        )
        top_products = [
            {"name": r[0] or "—", "qty": int(r[1] or 0), "revenue": float(r[2] or 0)}
            for r in top
        ]

    st_q = db.query(Order.status, func.count(Order.id))
    if reset_at is not None:
        st_q = st_q.filter(Order.created_at >= reset_at)
    status_counts = st_q.group_by(Order.status).all()
    orders_by_status = {}
    for s, c in status_counts:
        key = s.value if hasattr(s, "value") else str(s)
        orders_by_status[key] = int(c)

    pay_q = db.query(Order.payment_status, func.count(Order.id))
    if reset_at is not None:
        pay_q = pay_q.filter(Order.created_at >= reset_at)
    pay_counts = pay_q.group_by(Order.payment_status).all()
    orders_by_payment = [
        {"name": (p.value if hasattr(p, "value") else str(p)), "count": int(c)}
        for p, c in pay_counts
    ]

    # online users (do NOT reuse reset_at variable)
    online_since = datetime.now(timezone.utc) - timedelta(minutes=2)
    try:
        online = db.query(func.count(User.id)).filter(User.is_active == True, User.updated_at >= online_since).scalar() or 0
    except Exception:
        online = 0

    # registrations last 7 days (respect reset)
    day_bars = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        rq = db.query(func.count(User.id)).filter(User.created_at >= start, User.created_at < end)
        if reset_at is not None:
            # zero out days fully before reset
            if end <= reset_at:
                day_bars.append({"day": day.strftime("%d.%m"), "count": 0})
                continue
            if start < reset_at:
                rq = rq.filter(User.created_at >= reset_at)
        cnt = rq.scalar() or 0
        day_bars.append({"day": day.strftime("%d.%m"), "count": int(cnt)})

    # Month period: from max(month_start, reset_at)
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    period_start = month_start
    if reset_at is not None and reset_at > period_start:
        period_start = reset_at

    month_paid = [
        o for o in paid_orders
        if o.created_at and _aware(o.created_at) >= period_start
    ]
    month_revenue = sum((float(o.subtotal or 0) for o in month_paid), 0.0)
    month_delivery = sum((float(o.delivery_cost or 0) for o in month_paid), 0.0)

    if len(month_paid) == 0:
        month_cost = 0.0
        month_profit = 0.0
        month_delivery = 0.0
    else:
        month_cost = float(
            db.query(func.coalesce(func.sum(Product.purchase_price * OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .filter(
                Order.payment_status == PaymentStatus.paid,
                Order.created_at >= period_start,
            )
            .scalar()
            or 0
        )
        month_profit = month_revenue - month_cost

    return {
        "total_products": total_products,
        "published_products": published,
        "total_customers": total_customers,
        "orders_total": orders_all,
        "orders_paid": orders_paid_count,
        "orders_awaiting_review": awaiting,
        "revenue_tjs": revenue,
        "delivery_tjs": delivery_revenue,
        "revenue_with_delivery_tjs": revenue_with_delivery,
        "cost_tjs": cost,
        "profit_tjs": profit,
        "month_label": now.strftime("%m.%Y"),
        "month_revenue_tjs": month_revenue,
        "month_delivery_tjs": month_delivery,
        "month_cost_tjs": month_cost,
        "month_profit_tjs": month_profit,
        "month_orders_paid": len(month_paid),
        "top_products": top_products,
        "orders_by_status": orders_by_status,
        "orders_by_payment": orders_by_payment,
        "online_users": online,
        "registrations_7d": day_bars,
        "stats_reset_at": reset_at.isoformat() if reset_at else None,
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

    reset = _stats_since(db)
    if reset is not None and reset > start:
        start = reset

    paid = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(
            Order.payment_status == PaymentStatus.paid,
            Order.created_at >= start,
            Order.created_at < end,
        )
        .all()
    )
    revenue = sum((float(o.subtotal or 0) for o in paid), 0.0)
    delivery = sum((float(o.delivery_cost or 0) for o in paid), 0.0)
    if not paid:
        cost = 0.0
        delivery = 0.0
    else:
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
    orders_out = []
    for o in paid:
        orders_out.append({
            "order_number": o.order_number,
            "total": float(o.subtotal or 0),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": [
                {
                    "name": it.product_name,
                    "variant": it.variant_name,
                    "qty": it.quantity,
                }
                for it in (o.items or [])
            ],
        })

    return {
        "year": y,
        "month": m,
        "period": f"{m:02d}.{y}",
        "orders_paid": len(paid),
        "revenue_tjs": revenue,
        "delivery_tjs": delivery,
        "cost_tjs": cost,
        "profit_tjs": revenue - cost,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "orders": orders_out,
    }
