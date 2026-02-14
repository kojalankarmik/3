"""
Простое логирование без structlog.
Все логи идут в stdout для Deploy-F.
"""

import logging
import sys


def setup_logging():
    """Инициализация логирования"""
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Создаём обработчик для вывода в консоль
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Добавляем обработчик к root logger
    if not root_logger.handlers:
        root_logger.addHandler(handler)


# Логгеры по компонентам (создаём после setup_logging)
log_api = logging.getLogger("api")
log_bot = logging.getLogger("bot")
log_webhook = logging.getLogger("webhook")
log_db = logging.getLogger("db")
log_service = logging.getLogger("service")