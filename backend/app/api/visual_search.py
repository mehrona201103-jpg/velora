"""
Visual product search (Pinduoduo-style).
Uploads a photo; optionally uses text hint.
Without external AI API we match by optional text + return popular/relevant products.
Ready to plug real image embedding API later.
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.config import settings
from app.models.product import Product
from app.schemas.product import ProductOut
import aiofiles

router = APIRouter(prefix="/products", tags=["visual-search"])


@router.post("/visual-search")
async def visual_search(
    file: UploadFile = File(...),
    query: str | None = Form(None),
    db: Session = Depends(get_db),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Только JPEG, PNG или WEBP")

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "Файл слишком большой (макс 8 МБ)")

    upload_dir = Path(settings.UPLOAD_DIR) / "visual_search"
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"vs_{uuid.uuid4().hex[:12]}.jpg"
    path = upload_dir / name
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)

    q = db.query(Product).options(joinedload(Product.images), joinedload(Product.variants)).filter(
        Product.is_published == True
    )

    if query and query.strip():
        like = f"%{query.strip()}%"
        q = q.filter(or_(
            Product.name_ru.ilike(like),
            Product.name_tj.ilike(like),
            Product.name_en.ilike(like),
            Product.description_ru.ilike(like),
        ))

    items = q.order_by(Product.views.desc(), Product.created_at.desc()).limit(24).all()
    result = []
    for p in items:
        out = ProductOut.model_validate(p)
        out.final_price = p.final_price
        result.append(out)

    return {
        "ok": True,
        "hint": "Поиск по фото: показаны похожие/популярные товары. Добавьте текст для точности.",
        "image_saved": f"/uploads/visual_search/{name}",
        "items": result,
        "total": len(result),
    }
