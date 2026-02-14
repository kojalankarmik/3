"""
Простое логирование без structlog.
"""

import logging
from app.config import get_settings

settings = get_settings()


def setup_logging():
    """Инициализация логирования"""
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )


# Логгеры по компонентам
log_api = logging.getLogger("api")
log_bot = logging.getLogger("bot")
log_webhook = logging.getLogger("webhook")
log_db = logging.getLogger("db")
log_service = logging.getLogger("service")