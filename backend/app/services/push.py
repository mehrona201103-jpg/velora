"""Web Push for VELORA (PWA / APK). VAPID + pywebpush."""
from __future__ import annotations
import json
import base64
import traceback
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.core.config import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _get_setting(db: Session, key: str) -> Optional[str]:
    from app.models.settings import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row and row.value else None


def _set_setting(db: Session, key: str, value: str) -> None:
    from app.models.settings import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _generate_vapid_pair() -> tuple[str, str]:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return _b64url(pub_raw), priv_pem


def reset_vapid_keys(db: Session) -> tuple[str, str, str]:
    """Force new VAPID keypair (invalidates old browser subscriptions)."""
    pub, priv = _generate_vapid_pair()
    mailto = _get_setting(db, "vapid_mailto") or "mailto:owner@velora.tj"
    _set_setting(db, "vapid_public_key", pub)
    _set_setting(db, "vapid_private_key", priv)
    _set_setting(db, "vapid_mailto", mailto)
    print("[VELORA] VAPID keys RESET, pub[0:16]=", pub[:16])
    return pub, priv, mailto


def get_or_create_vapid(db: Session) -> tuple[str, str, str]:
    pub = _get_setting(db, "vapid_public_key")
    priv = _get_setting(db, "vapid_private_key")
    mailto = _get_setting(db, "vapid_mailto") or "mailto:owner@velora.tj"
    if pub and priv and len(pub) > 40 and "BEGIN" in (priv or ""):
        return pub, priv, mailto
    return reset_vapid_keys(db)


def get_vapid_public_key(db: Session) -> str:
    pub, _, _ = get_or_create_vapid(db)
    return pub


def send_web_push(
    db: Session,
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
    url: str = "/",
    tag: str = "velora",
) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return False, "На сервере не установлен pywebpush (нужен redeploy)"

    pub, priv, mailto = get_or_create_vapid(db)
    if not pub or not priv:
        return False, "Нет VAPID ключей на сервере"

    subscription_info = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
    }
    payload = json.dumps({
        "title": title or "VELORA",
        "body": body or "",
        "url": url or "/",
        "tag": tag or "velora",
        "icon": "/icon-192.png",
        "badge": "/icon-192.png",
    }, ensure_ascii=False)

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=priv,
            vapid_claims={"sub": mailto},
            ttl=86400,
            timeout=15,
        )
        print("[VELORA] push OK", endpoint[:60])
        return True, ""
    except Exception as e:
        err = str(e)
        print("[VELORA] push FAIL:", err[:400])
        # drop invalid subscriptions
        low = err.lower()
        if any(x in low for x in ("410", "404", "gone", "unauthorized", "403", "invalid", "mismatch")):
            try:
                from app.models.push import PushSubscription
                db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).delete()
                db.commit()
            except Exception:
                db.rollback()
        return False, err[:200]


def notify_user_push(db: Session, user_id: int, title: str, body: str, url: str = "/") -> dict[str, Any]:
    from app.models.push import PushSubscription
    try:
        PushSubscription.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    rows = db.query(PushSubscription).filter(PushSubscription.user_id == int(user_id)).all()
    print(f"[VELORA] push user={user_id} devices={len(rows)}")
    if not rows:
        return {"sent": 0, "total": 0, "errors": ["no_subscription"]}

    sent = 0
    errors: list[str] = []
    for row in rows:
        ok, err = send_web_push(
            db, row.endpoint, row.p256dh, row.auth,
            title, body, url=url, tag=f"u{user_id}",
        )
        if ok:
            sent += 1
        elif err:
            errors.append(err)
    return {"sent": sent, "total": len(rows), "errors": errors[:3]}


def notify_admins_push(db: Session, title: str, body: str, url: str = "/admin") -> dict[str, Any]:
    from app.models.push import PushSubscription
    from app.models.user import User, Role
    try:
        PushSubscription.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    admin_ids = [
        r[0] for r in db.query(User.id).filter(
            User.role.in_([Role.admin, Role.owner]),
            User.is_active == True,  # noqa: E712
        ).all()
    ]
    if not admin_ids:
        return {"sent": 0, "total": 0, "errors": ["no_admins"]}
    rows = db.query(PushSubscription).filter(PushSubscription.user_id.in_(admin_ids)).all()
    sent = 0
    errors: list[str] = []
    for row in rows:
        ok, err = send_web_push(
            db, row.endpoint, row.p256dh, row.auth,
            title, body, url=url, tag="admin",
        )
        if ok:
            sent += 1
        elif err:
            errors.append(err)
    return {"sent": sent, "total": len(rows), "errors": errors[:3]}
