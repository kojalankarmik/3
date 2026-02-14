"""
Тесты парсера вебхуков.
"""

import pytest
from app.services.webhook_parser import WebhookParser, calculate_payload_hash
import hashlib


def test_webhook_parser_homereserve():
    """Тест парсинга HomeReserve вебхука"""
    payload = {
        "booking_id": "BK-12345",
        "status": "paid",
        "apartment_id": 42,
        "check_in_date": "2024-02-15",
        "check_out_date": "2024-02-17",
        "price": 5000,
        "currency": "RUB",
        "guest_phone": "+79001234567",
        "guest_email": "guest@example.com",
    }
    
    parser = WebhookParser(provider="homereserve", payload=payload)
    result = parser.parse()
    
    assert result is not None
    assert result["event_id"] == "BK-12345"
    assert result["event_type"] == "paid"
    assert result["apartment_id"] == 42
    assert result["check_in"] == "2024-02-15"
    assert result["check_out"] == "2024-02-17"
    assert result["total_amount"] == 5000
    assert result["phone"] == "+79001234567"


def test_webhook_parser_unknown_provider():
    """Тест на неизвестный провайдер"""
    payload = {"some_field": "value"}
    
    parser = WebhookParser(provider="unknown_provider", payload=payload)
    result = parser.parse()
    
    # Должен вернуть None или выставить значения по умолчанию
    assert result is None or result.get("event_type") == "unknown"


def test_webhook_parser_nested_fields():
    """Тест на nested поля"""
    payload = {
        "booking": {
            "id": "BK-999",
            "status": "confirmed",
        },
        "property": {
            "id": 100,
        },
    }
    
    # Переопределяем маппинг для теста
    parser = WebhookParser(provider="homereserve", payload=payload)
    
    # Проверяем _get_value с nested keys
    assert parser._get_value("booking.id") == "BK-999"
    assert parser._get_value("property.id") == 100
    assert parser._get_value("nonexistent.field") is None


def test_calculate_payload_hash():
    """Тест вычисления хеша"""
    payload = b'{"booking_id": "BK-123"}'
    
    hash1 = calculate_payload_hash(payload)
    hash2 = calculate_payload_hash(payload)
    
    # Один и тот же payload должен дать одинаковый хеш
    assert hash1 == hash2
    
    # Разный payload — разный хеш
    payload2 = b'{"booking_id": "BK-124"}'
    hash3 = calculate_payload_hash(payload2)
    
    assert hash1 != hash3
    
    # Хеш должен быть hex string длиной 64 (SHA256)
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)