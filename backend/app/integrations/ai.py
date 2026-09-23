"""VELORA AI — product advisor using real catalog only."""
from __future__ import annotations
import json
import logging
import re
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.product import Product, ProductVariant, Category

logger = logging.getLogger(__name__)
settings = get_settings()


class AIProvider(ABC):
    @abstractmethod
    async def advise(self, message: str, products_context: list[dict]) -> str:
        """Given user message and real products, return advice text."""
        ...


class NoneAIProvider(AIProvider):
    async def advise(self, message: str, products_context: list[dict]) -> str:
        if not products_context:
            return "К сожалению, сейчас нет подходящих товаров по вашему запросу."
        lines = ["Вот что нашлось в каталоге VELORA:"]
        for p in products_context[:8]:
            price = p.get("price", "—")
            lines.append(f"• {p['name']} — {price} TJS (SKU: {p.get('sku', '—')})")
        lines.append("\nУточните цвет, размер или бюджет — подберу точнее.")
        return "\n".join(lines)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"

    async def advise(self, message: str, products_context: list[dict]) -> str:
        system = (
            "Ты консультант магазина женской одежды VELORA. "
            "Отвечай только на основе переданного списка товаров. "
            "Не выдумывай товары, цены, размеры или наличие. "
            "Если подходящего нет — честно скажи. "
            "Отвечай на языке пользователя (русский/таджикский/английский). "
            "Будь вежливой, элегантной, кратко."
        )
        catalog = json.dumps(products_context, ensure_ascii=False, default=str)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Каталог (реальные товары):\n{catalog}\n\nВопрос клиента: {message}",
                },
            ],
            "temperature": 0.4,
            "max_tokens": 800,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            if r.status_code != 200:
                logger.error("OpenAI error: %s", r.text)
                return await NoneAIProvider().advise(message, products_context)
            data = r.json()
            return data["choices"][0]["message"]["content"]


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.api_key = api_key
        self.model = model or "claude-3-5-haiku-latest"

    async def advise(self, message: str, products_context: list[dict]) -> str:
        system = (
            "Ты консультант магазина женской одежды VELORA. "
            "Отвечай только на основе переданного списка товаров. "
            "Не выдумывай товары, цены, размеры или наличие."
        )
        catalog = json.dumps(products_context, ensure_ascii=False, default=str)
        payload = {
            "model": self.model,
            "max_tokens": 800,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": f"Каталог:\n{catalog}\n\nВопрос: {message}",
                }
            ],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            if r.status_code != 200:
                logger.error("Anthropic error: %s", r.text)
                return await NoneAIProvider().advise(message, products_context)
            data = r.json()
            return data["content"][0]["text"]


def get_ai_provider() -> AIProvider:
    provider = (settings.ai_provider or "none").lower()
    key = settings.ai_api_key or ""
    model = settings.ai_model or ""
    if provider == "openai" and key:
        return OpenAIProvider(key, model)
    if provider == "anthropic" and key:
        return AnthropicProvider(key, model)
    return NoneAIProvider()


def _extract_price_limit(message: str) -> Decimal | None:
    # "до 500", "до 500 сомони", "under 500", "max 500"
    m = re.search(r"(?:до|under|max|до\s*\$?)\s*(\d+(?:[.,]\d+)?)", message, re.I)
    if m:
        return Decimal(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:сомони|tjs|смн)", message, re.I)
    if m:
        return Decimal(m.group(1).replace(",", "."))
    return None


async def search_products_for_ai(db: AsyncSession, message: str, limit: int = 15) -> list[dict]:
    """Search real products matching user query heuristics."""
    q = select(Product).where(Product.is_active == True)  # noqa: E712
    price_limit = _extract_price_limit(message)
    if price_limit:
        q = q.where(Product.base_price <= price_limit)

    # Simple keyword filter
    keywords = re.findall(r"[a-zA-Zа-яА-ЯёЁ]{3,}", message.lower())
    stop = {"мне", "нужно", "покажи", "хочу", "есть", "для", "или", "the", "and", "for", "show", "need"}
    keywords = [k for k in keywords if k not in stop][:5]
    if keywords:
        conditions = []
        for kw in keywords:
            like = f"%{kw}%"
            conditions.append(Product.name_ru.ilike(like))
            conditions.append(Product.description_ru.ilike(like))
        q = q.where(or_(*conditions))

    q = q.options(selectinload(Product.images)).order_by(Product.created_at.desc()).limit(limit)
    result = await db.execute(q)
    products = result.scalars().all()

    out = []
    for p in products:
        out.append({
            "id": p.id,
            "name": p.name_ru,
            "sku": p.sku,
            "price": str(p.base_price),
            "old_price": str(p.old_price) if p.old_price else None,
            "description": (p.description_ru or "")[:200],
            "is_new": p.is_new,
            "is_featured": p.is_featured,
        })
    return out


async def velora_ai_reply(db: AsyncSession, message: str) -> dict[str, Any]:
    products = await search_products_for_ai(db, message)
    provider = get_ai_provider()
    text = await provider.advise(message, products)
    return {
        "reply": text,
        "products_used": len(products),
        "provider": settings.ai_provider or "none",
        "product_ids": [p["id"] for p in products],
    }
