"""
Утилиты для бота
"""

from urllib.parse import urlencode
from datetime import datetime, timedelta
from app.config import get_settings

settings = get_settings()


def build_booking_url(apartment_id: int, source: str = "tg_bot", medium: str = "bot") -> str:
    """
    Построить ссылку на бронирование с атрибутацией.
    
    Пример результата:
    https://homereserve.ru/bJOig2XsQu?tag=tg_bot&utm_source=tg&utm_medium=bot&utm_campaign=apartment_123
    """
    params = {
        settings.booking_tag_param: source,
        "utm_source": "tg",
        "utm_medium": medium,
        "utm_campaign": f"apartment_{apartment_id}",
    }
    
    query_string = urlencode(params)
    return f"{settings.booking_base_url}?{query_string}"


def format_apartment_card(apartment, booking_url: str) -> str:
    """
    Форматировать карточку квартиры для вывода в чат.
    """
    features = apartment.features_json or []
    features_str = " • ".join(features[:5]) if features else "Удобства в описании"
    
    text = f"""
🏠 **{apartment.title}**

📍 {apartment.district or "Район не указан"}

✨ {features_str}

👥 Вместимость: {apartment.guests_max} гостей
🛏️ {apartment.beds_text or "Конфигурация спален в описании"}

💰 Точная цена и свободные даты:
[👉 Проверить]({booking_url})
    """.strip()
    
    return text


def format_lead_brief(lead) -> str:
    """Краткое описание лида"""
    text = f"""
📅 {lead.date_from} – {lead.date_to}
👥 {lead.guests} гостей
📍 {lead.district or "Любой"}
💰 {lead.budget_min}–{lead.budget_max}₽
📞 {lead.contact}
    """.strip()
    return text


def parse_date_input(date_str: str) -> tuple:
    """
    Парсить ввод вида "15.02-17.02" и вернуть (check_in, check_out) в формате YYYY-MM-DD.
    Возвращает текущий год.
    """
    try:
        parts = date_str.split("-")
        if len(parts) != 2:
            return None
        
        check_in_str, check_out_str = parts
        day_in, month_in = map(int, check_in_str.split("."))
        day_out, month_out = map(int, check_out_str.split("."))
        
        year = datetime.now().year
        
        check_in = f"{year}-{month_in:02d}-{day_in:02d}"
        check_out = f"{year}-{month_out:02d}-{day_out:02d}"
        
        return check_in, check_out
    except:
        return None


def get_today_tomorrow() -> tuple:
    """Вернуть сегодня и завтра в формате YYYY-MM-DD"""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return today, tomorrow