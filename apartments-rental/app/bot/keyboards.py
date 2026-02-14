"""
Клавиатуры для Aiogram 3 (ReplyKeyboard и InlineKeyboard)
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List
from app.bot import texts


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏠 Подобрать квартиру")
    kb.button(text="📚 Каталог")
    kb.button(text="🔥 Горящие даты")
    kb.button(text="📍 Районы")
    kb.button(text="❓ Правила / FAQ")
    kb.button(text="💬 Связаться")
    kb.button(text="🎁 Скидка / Рефералка")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=False)


def admin_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏠 Квартиры")
    kb.button(text="📢 Публикация")
    kb.button(text="📩 Лиды")
    kb.button(text="📅 Брони")
    kb.button(text="🎁 Рефералы")
    kb.button(text="📊 Статистика")
    kb.button(text="🏠 Меню")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def back_menu_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Всегда доступные кнопки"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=texts.Buttons.back)
    kb.button(text=texts.Buttons.menu)
    kb.button(text=texts.Buttons.cancel)
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=False)


def wizard_dates_keyboard() -> ReplyKeyboardMarkup:
    """Выбор дат"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=texts.Buttons.today)
    kb.button(text=texts.Buttons.tomorrow)
    kb.button(text=texts.Buttons.custom)
    kb.add(back_menu_cancel_keyboard().keyboard[0][0], back_menu_cancel_keyboard().keyboard[0][1], back_menu_cancel_keyboard().keyboard[0][2])
    kb.adjust(3, 3)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def wizard_guests_keyboard() -> ReplyKeyboardMarkup:
    """Выбор количества гостей"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=texts.Buttons.guests_1)
    kb.button(text=texts.Buttons.guests_2)
    kb.button(text=texts.Buttons.guests_3)
    kb.button(text=texts.Buttons.guests_4)
    kb.button(text=texts.Buttons.guests_5)
    kb.button(text=texts.Buttons.guests_6_plus)
    kb.adjust(3, 3)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def wizard_district_keyboard(districts: List[str]) -> ReplyKeyboardMarkup:
    """Выбор района"""
    kb = ReplyKeyboardBuilder()
    for district in districts:
        kb.button(text=f"📍 {district}")
    kb.button(text=texts.Buttons.district_any)
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def wizard_budget_keyboard() -> ReplyKeyboardMarkup:
    """Выбор бюджета"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=texts.Buttons.budget_2500)
    kb.button(text=texts.Buttons.budget_3500)
    kb.button(text=texts.Buttons.budget_4500)
    kb.button(text=texts.Buttons.budget_any)
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def apartment_card_inline_keyboard(apartment_id: int, booking_url: str, map_url: str = None) -> InlineKeyboardMarkup:
    """Inline кнопки для карточки квартиры"""
    kb = InlineKeyboardBuilder()
    kb.button(text=texts.Buttons.check_price, url=booking_url)
    if map_url:
        kb.button(text="📍 На карте", url=map_url)
    kb.button(text=texts.Buttons.ask_question, callback_data=f"ask_apt_{apartment_id}")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def channel_menu_inline_keyboard(booking_url: str) -> InlineKeyboardMarkup:
    """Inline меню в канале"""
    kb = InlineKeyboardBuilder()
    kb.button(text=texts.Buttons.check_price, url=booking_url)
    kb.button(text="🏠 Каталог", callback_data="catalog")
    kb.button(text="🔥 Горящие", callback_data="hot_offers")
    kb.button(text="❓ FAQ", callback_data="faq")
    kb.button(text="💬 Менеджер", url="https://t.me/your_manager")
    kb.button(text="🤖 Подбор", url="https://t.me/your_bot")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def confirm_keyboard(yes_text: str = "✅ Да", no_text: str = "❌ Нет") -> InlineKeyboardMarkup:
    """Подтверждение"""
    kb = InlineKeyboardBuilder()
    kb.button(text=yes_text, callback_data="confirm_yes")
    kb.button(text=no_text, callback_data="confirm_no")
    return kb.as_markup()


def pagination_inline_keyboard(page: int, total_pages: int, data_prefix: str) -> InlineKeyboardMarkup:
    """Пагинация"""
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="⬅️ Назад", callback_data=f"page_{data_prefix}_{page-1}")
    if page < total_pages - 1:
        kb.button(text="Дальше ➡️", callback_data=f"page_{data_prefix}_{page+1}")
    kb.adjust(2)
    return kb.as_markup()