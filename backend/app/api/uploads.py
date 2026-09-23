"""File upload endpoints (S3)."""
import io
from fastapi import APIRouter, UploadFile, File, Form, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_permissions
from app.core.exceptions import ValidationError, NotFoundError
from app.models.finance import PaymentTopUpRequest, PaymentReceipt
from app.models.product import Product, ProductImage
from app.models.user import User
from app.storage.provider import get_storage

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_RECEIPT_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}
MAX_SIZE = 5 * 1024 * 1024


class UploadResult(BaseModel):
    key: str
    url: str


@router.post("/receipt/{topup_id}", response_model=UploadResult)
async def upload_receipt(
    topup_id: int,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_RECEIPT_TYPES:
        raise ValidationError("Допустимы только JPG, PNG, WEBP, PDF")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise ValidationError("Файл слишком большой (макс. 5 МБ)")

    result = await db.execute(
        select(PaymentTopUpRequest).where(
            PaymentTopUpRequest.id == topup_id,
            PaymentTopUpRequest.user_id == user.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise NotFoundError("Заявка не найдена")

    storage = get_storage()
    key = await storage.upload(
        io.BytesIO(data),
        folder="receipts",
        filename=f"{topup_id}_{(file.filename or 'receipt').replace(' ', '_')}",
        content_type=file.content_type or "application/octet-stream",
    )
    req.receipt_storage_key = key
    receipt = PaymentReceipt(
        topup_request_id=req.id,
        storage_key=key,
        original_filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(data),
    )
    db.add(receipt)
    await db.commit()
    return UploadResult(key=key, url=storage.public_url(key))


@router.post("/product-image/{product_id}", response_model=UploadResult)
async def upload_product_image(
    product_id: int,
    db: DbSession,
    admin: User = Depends(require_permissions("products.write")),
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError("Допустимы только JPG, PNG, WEBP, GIF")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise ValidationError("Файл слишком большой (макс. 5 МБ)")

    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Товар не найден")

    storage = get_storage()
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1]
    key = await storage.upload(
        io.BytesIO(data),
        folder=f"products/{product_id}",
        filename=f"{product_id}_{ext}",
        content_type=file.content_type or "image/jpeg",
    )
    img = ProductImage(
        product_id=product_id,
        storage_key=key,
        alt_text=product.name_ru,
        is_primary=is_primary,
    )
    db.add(img)
    await db.commit()
    return UploadResult(key=key, url=storage.public_url(key))
