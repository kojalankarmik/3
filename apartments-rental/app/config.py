import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List
import pytz


class Settings(BaseSettings):
    """Конфигурация приложения из .env"""

    # Telegram
    bot_token: str
    admin_tg_ids: str  # "111,222"
    manager_tg_ids: str = ""
    channel_id: str

    # URLs
    base_public_url: str
    tg_webhook_path: str
    booking_base_url: str
    booking_tag_param: str = "tag"

    # Security
    webhook_secret: str
    admin_panel_user: str = "admin"
    admin_panel_pass: str = "password123"

    # Database
    database_url: str

    # Referral
    attribution_window_days: int = 30
    ref_payout_mode: str = "fixed"  # fixed | percent
    ref_payout_fixed: int = 500
    ref_payout_percent: float = 5.0

    # App
    timezone: str = "Europe/Moscow"
    debug: bool = False
    log_level: str = "INFO"
    port: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def admin_ids(self) -> List[int]:
        return [int(x.strip()) for x in self.admin_tg_ids.split(",") if x.strip()]

    @property
    def manager_ids(self) -> List[int]:
        if not self.manager_tg_ids:
            return []
        return [int(x.strip()) for x in self.manager_tg_ids.split(",") if x.strip()]

    @property
    def tz(self):
        return pytz.timezone(self.timezone)

    @property
    def webhook_url(self) -> str:
        return f"{self.base_public_url}{self.tg_webhook_path}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()