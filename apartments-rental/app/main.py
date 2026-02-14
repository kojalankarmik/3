"""
Главная FastAPI аппликация.
Интегрирует:
- Telegram bot webhook
- Booking webhooks
- Admin panel
- Health check
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.logger import setup_logging, log_api
from app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events"""
    log_api.info("=" * 50)
    log_api.info("🚀 Приложение стартует")
    log_api.info(f"PORT: {settings.port}")
    log_api.info(f"DEBUG: {settings.debug}")
    log_api.info("=" * 50)
    
    # Init database
    try:
        await init_db()
        log_api.info("✅ База данных инициализирована")
    except Exception as e:
        log_api.error(f"❌ Ошибка инициализации БД: {e}")
    
    # Регистрируем роутеры бота (ПОСЛЕ инициализации БД)
    try:
        from app.bot.main import register_routers
        register_routers()
        log_api.info("✅ Роутеры бота зарегистрированы")
    except Exception as e:
        log_api.error(f"❌ Ошибка регистрации роутеров: {e}")
    
    yield
    
    log_api.info("🛑 Приложение останавливается")


app = FastAPI(
    title="Квартиры посуточно Краснодар",
    version="0.1.0",
    lifespan=lifespan,
)

setup_logging()


# ============= ROUTES =============

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# Telegram webhook (Aiogram)
@app.post(settings.tg_webhook_path)
async def tg_webhook(request: Request):
    """Webhook для Telegram bot updates (Aiogram)"""
    from aiogram.types import Update
    from app.bot.main import bot, dp
    from app.logger import log_api

    try:
        update_data = await request.json()

        # Превращаем dict -> Update (aiogram v3 на pydantic v2)
        update = Update.model_validate(update_data, context={"bot": bot})

        # Передаём в диспетчер
        await dp.feed_update(bot, update)

    except Exception as e:
        # Важно: отвечаем 200, чтобы Telegram не ретраил бесконечно,
        # но логируем ошибку.
        log_api.error("Ошибка обработки Telegram webhook", error=str(e))

    return {"ok": True}



# Booking webhooks
try:
    from app.api.routes_webhooks import router as webhook_router
    app.include_router(webhook_router, prefix="/webhooks")
except Exception as e:
    log_api.error(f"Ошибка подключения webhook роутера: {e}")


# Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel_root():
    """Редирект на админ-панель"""
    return """
    <html>
    <head>
        <title>Админ-панель</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            h1 { color: #333; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🛠 Админ-панель</h1>
        <p>Быстрые ссылки:</p>
        <ul>
            <li><a href="/admin/dashboard">📊 Дашборд</a></li>
            <li><a href="/admin/apartments">🏠 Квартиры</a></li>
            <li><a href="/admin/leads">📩 Лиды</a></li>
            <li><a href="/admin/bookings">📅 Брони</a></li>
            <li><a href="/admin/referrals">🎁 Рефералы</a></li>
        </ul>
    </body>
    </html>
    """


# Root
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
    <head>
        <title>Квартиры посуточно</title>
        <style>
            body { 
                font-family: Arial; 
                text-align: center; 
                margin-top: 100px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            h1 { font-size: 3em; }
            .links { margin-top: 30px; }
            a { 
                color: white; 
                text-decoration: none; 
                margin: 0 15px;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                display: inline-block;
            }
            a:hover { background: rgba(255,255,255,0.3); }
        </style>
    </head>
    <body>
        <h1>🏠 Квартиры посуточно Краснодар</h1>
        <p style="font-size: 1.2em;">Ищи лучшие апартаменты!</p>
        <div class="links">
            <a href="https://t.me/your_bot">🤖 Telegram Бот</a>
            <a href="/health">❤️ Health Check</a>
        </div>
    </body>
    </html>
    """


@app.on_event("startup")
async def setup_bot_webhook():
    """Регистрируем Telegram webhook при старте"""
    try:
        from app.bot.main import bot
        
        await bot.set_webhook(
            url=settings.webhook_url,
            drop_pending_updates=True,
        )
        log_api.info(f"✅ Telegram webhook установлен: {settings.webhook_url}")
    except Exception as e:
        log_api.error(f"❌ Ошибка при установке webhook: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )