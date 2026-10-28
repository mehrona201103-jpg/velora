"""Run: python -m app.core.init_owner"""
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User, Role


def main():
    Base.metadata.create_all(bind=engine)
    email = (getattr(settings, "OWNER_EMAIL", None) or settings.FIRST_OWNER_EMAIL or "owner@velora.tj").strip()
    password = (getattr(settings, "OWNER_PASSWORD", None) or settings.FIRST_OWNER_PASSWORD or "ChangeThisStrongPassword123!").strip()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == Role.owner).first()
        if not existing:
            existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.email = email
            existing.role = Role.owner
            existing.is_active = True
            existing.hashed_password = hash_password(password)
            db.commit()
            print(f"Owner synced: {email}")
            return
        owner = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="VELORA Owner",
            role=Role.owner,
            is_active=True,
        )
        db.add(owner)
        db.commit()
        print(f"Owner created successfully: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
