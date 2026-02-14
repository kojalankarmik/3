"""
Инициализация Aiogram 3 диспетчера и бота.
Без циклических импортов!
"""

from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings

settings = get_settings()

# Создаём бота
bot = Bot(token=settings.bot_token)

# FSM Storage (в памяти для MVP; для production → Redis)
storage = MemoryStorage()

# Диспетчер
dp = Dispatcher(storage=storage)


def register_routers():
    """Регистрируем роутеры (вызывается отдельно, чтобы избежать циклического импорта)"""
    from app.bot.router_user import router as user_router
    from app.bot.router_admin import router as admin_router
    
    dp.include_router(admin_router)  # Админ первым, чтобы имел приоритет
    dp.include_router(user_router)