# VELORA — магазин женской одежды

Готовое приложение (клиент + админ + PostgreSQL) для Instagram-магазина **@_velora_shop.tj**.

## Возможности
- Каталог товаров, категории, фото, скидки
- Регистрация / вход, профиль, PIN / биометрия
- Корзина, заказ, оплата по чеку (карта / перевод)
- Статусы заказа + Telegram-уведомления
- Доставка по районам, сумма доставки от админа
- Админ-панель: товары, заказы, статистика, рассылка, баннеры
- PWA / APK через PWABuilder

## Контакты магазина (по умолчанию)
- Instagram: https://instagram.com/_velora_shop.tj
- WhatsApp: 918 78 10 09 → https://wa.me/992918781009
- Адрес: Саховат 35, солаги A18

## Деплой на Railway
1. Создайте проект + PostgreSQL
2. Загрузите этот репозиторий
3. Variables:
   - `DATABASE_URL` = из Postgres
   - `SECRET_KEY` = любой длинный секрет
   - `TELEGRAM_BOT_TOKEN` = токен бота (опционально)
   - `PUBLIC_BASE_URL` = https://ваш-домен.up.railway.app
   - `OWNER_EMAIL` / `OWNER_PASSWORD` (или FIRST_OWNER_*) — логин админа
4. Owner создаётся и **синхронизирует пароль** при каждом старте из env
   (по умолчанию: owner@velora.tj / ChangeThisStrongPassword123!).

## Локально
```bash
# backend
cd backend && pip install -r requirements.txt
export DATABASE_URL=sqlite:///./velora.db
uvicorn app.main:app --reload

# frontend
cd frontend && npm i && npm run build
```
