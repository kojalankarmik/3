"""
Тесты утилит.
"""

import pytest
from app.bot.utils import build_booking_url, parse_date_input, get_today_tomorrow
from urllib.parse import urlparse, parse_qs


def test_build_booking_url():
    """Тест построения URL бронирования"""
    url = build_booking_url(apartment_id=123, source="tg_bot", medium="bot")
    
    # Проверяем, что URL содержит правильные параметры
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    assert "tag" in params
    assert params["tag"][0] == "tg_bot"
    assert "utm_medium" in params
    assert params["utm_medium"][0] == "bot"
    assert "utm_campaign" in params
    assert "apartment_123" in params["utm_campaign"][0]


def test_build_booking_url_channel():
    """Тест URL для канала"""
    url = build_booking_url(apartment_id=456, source="tg_channel", medium="channel")
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    assert params["tag"][0] == "tg_channel"
    assert params["utm_medium"][0] == "channel"


def test_parse_date_input_valid():
    """Тест парсинга валидных дат"""
    check_in, check_out = parse_date_input("15.02-17.02")
    
    assert check_in == "2024-02-15"  # Предполагаем текущий год
    assert check_out == "2024-02-17"


def test_parse_date_input_invalid():
    """Тест парсинга невалидных дат"""
    result = parse_date_input("invalid")
    assert result is None


def test_get_today_tomorrow():
    """Тест получения сегодня и завтра"""
    today, tomorrow = get_today_tomorrow()
    
    # Проверяем формат YYYY-MM-DD
    assert len(today) == 10
    assert len(tomorrow) == 10
    assert today.count("-") == 2
    assert tomorrow.count("-") == 2