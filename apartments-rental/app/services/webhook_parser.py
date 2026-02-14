"""
Универсальный парсер вебхуков для разных модулей бронирования.
Конфигурируемое маппинг полей.
"""

from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime

from app.logger import log_webhook


class WebhookConfig:
    """Конфигурация маппинга полей для конкретного провайдера"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.mappings = {
            "homereserve": {
                "event_id": "booking_id",
                "event_type": "status",  # Маппим значение статуса
                "apartment_id": "apartment_id",
                "check_in": "check_in_date",
                "check_out": "check_out_date",
                "total_amount": "price",
                "currency": "currency",
                "phone": "guest_phone",
                "email": "guest_email",
                "status_values": {
                    "confirmed": "confirmed",
                    "paid": "paid",
                    "cancelled": "canceled",
                },
            },
            "booking_com": {
                "event_id": "reservation_id",
                "event_type": "event_type",
                "apartment_id": "property_id",
                "check_in": "arrival_date",
                "check_out": "departure_date",
                "total_amount": "total_price",
                "currency": "currency_code",
                "phone": "guest_phone",
                "email": "guest_email",
                "status_values": {
                    "RESERVATION_ACCEPTED": "confirmed",
                    "RESERVATION_CONFIRMED": "confirmed",
                    "RESERVATION_CANCELLED": "canceled",
                    "PAYMENT_RECEIVED": "paid",
                },
            },
        }
    
    def get_mapping(self) -> Dict[str, str]:
        """Получить маппинг для провайдера"""
        return self.mappings.get(self.provider, {})


class WebhookParser:
    """Универсальный парсер вебхуков"""
    
    def __init__(self, provider: str, payload: Dict[str, Any]):
        self.provider = provider
        self.payload = payload
        self.config = WebhookConfig(provider)
        self.mapping = self.config.get_mapping()
    
    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Распарсить вебхук и вернуть нормализованные поля.
        """
        try:
            mapping = self.mapping
            
            if not mapping:
                log_webhook.warning(
                    "Неизвестный провайдер",
                    provider=self.provider,
                )
                return None
            
            result = {
                "provider": self.provider,
                "event_id": self._get_value(mapping.get("event_id")),
                "event_type": self._normalize_event_type(
                    self._get_value(mapping.get("event_type")),
                    mapping.get("status_values", {}),
                ),
                "apartment_id": self._safe_int(self._get_value(mapping.get("apartment_id"))),
                "check_in": self._get_value(mapping.get("check_in")),
                "check_out": self._get_value(mapping.get("check_out")),
                "total_amount": self._safe_int(self._get_value(mapping.get("total_amount"))),
                "currency": self._get_value(mapping.get("currency"), "RUB"),
                "phone": self._get_value(mapping.get("phone")),
                "email": self._get_value(mapping.get("email")),
            }
            
            log_webhook.info(
                "Вебхук распарсен",
                provider=self.provider,
                event_id=result["event_id"],
                event_type=result["event_type"],
            )
            
            return result
        
        except Exception as e:
            log_webhook.error(
                "Ошибка парсинга вебхука",
                provider=self.provider,
                error=str(e),
            )
            return None
    
    def _get_value(self, key: str, default: Any = None) -> Any:
        """Получить значение из payload по ключу (поддерживаем nested)"""
        if not key:
            return default
        
        keys = key.split(".")
        value = self.payload
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Безопасно конвертировать в int"""
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    def _normalize_event_type(
        self, event_type: str, status_values: Dict[str, str]
    ) -> str:
        """Нормализовать тип события"""
        if not event_type:
            return "unknown"
        
        return status_values.get(event_type, event_type.lower())


def calculate_payload_hash(payload: bytes) -> str:
    """Вычислить хеш payload для идемпотентности"""
    return hashlib.sha256(payload).hexdigest()