"""Simple i18n strings API (ru / tg / en)."""
from fastapi import APIRouter, Query

router = APIRouter()

STRINGS = {
    "ru": {
        "app_name": "VELORA",
        "tagline": "Женская одежда",
        "catalog": "Каталог",
        "cart": "Корзина",
        "profile": "Профиль",
        "favorites": "Избранное",
        "login": "Войти",
        "register": "Регистрация",
        "checkout": "Оформить заказ",
        "balance": "Баланс",
        "orders": "Заказы",
        "add_to_cart": "В корзину",
        "empty_cart": "Корзина пуста",
        "delivery": "Доставка",
        "pickup": "Самовывоз",
    },
    "tg": {
        "app_name": "VELORA",
        "tagline": "Либоси занона",
        "catalog": "Каталог",
        "cart": "Сабад",
        "profile": "Профил",
        "favorites": "Дӯстдошта",
        "login": "Вуруд",
        "register": "Сабти ном",
        "checkout": "Фармоиш додан",
        "balance": "Баланс",
        "orders": "Фармоишҳо",
        "add_to_cart": "Ба сабад",
        "empty_cart": "Сабад холӣ аст",
        "delivery": "Расондан",
        "pickup": "Гирифтан",
    },
    "en": {
        "app_name": "VELORA",
        "tagline": "Women's Fashion",
        "catalog": "Catalog",
        "cart": "Cart",
        "profile": "Profile",
        "favorites": "Favorites",
        "login": "Sign in",
        "register": "Register",
        "checkout": "Checkout",
        "balance": "Balance",
        "orders": "Orders",
        "add_to_cart": "Add to cart",
        "empty_cart": "Cart is empty",
        "delivery": "Delivery",
        "pickup": "Pickup",
    },
}


@router.get("/{lang}")
async def get_strings(lang: str = "ru"):
    lang = lang if lang in STRINGS else "ru"
    return {"lang": lang, "strings": STRINGS[lang]}
