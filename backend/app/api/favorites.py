from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.user import User, Favorite
from app.models.product import Product
from app.api.deps import get_current_user
from app.schemas.product import ProductOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("")
def list_favorites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    favs = (
        db.query(Favorite)
        .options(joinedload(Favorite.product).joinedload(Product.images))
        .filter(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    items = []
    for f in favs:
        if f.product and f.product.is_published:
            out = ProductOut.model_validate(f.product)
            out.final_price = f.product.final_price
            items.append(out)
    return items


@router.post("/{product_id}")
def add_favorite(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id, Product.is_published == True).first()
    if not product:
        raise HTTPException(404, "Товар не найден")
    existing = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.product_id == product_id).first()
    if existing:
        return {"ok": True, "favorited": True}
    db.add(Favorite(user_id=user.id, product_id=product_id))
    db.commit()
    return {"ok": True, "favorited": True}


@router.delete("/{product_id}")
def remove_favorite(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fav = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.product_id == product_id).first()
    if fav:
        db.delete(fav)
        db.commit()
    return {"ok": True, "favorited": False}


@router.get("/{product_id}/status")
def favorite_status(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exists = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.product_id == product_id).first()
    return {"favorited": bool(exists)}
