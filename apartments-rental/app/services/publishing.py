"""
Публикация контента в Telegram канал.
БЕЗ циклических импортов!
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import hashlib

from app.config import get_settings
from app.db.models import Apartment, ChannelPost, ChannelPostKind
from app.db.session import SessionLocal
from app.bot.utils import build_booking_url, format_apartment_card
from app.logger import log_service

settings = get_settings()


async def get_bot():
    """Получить бота (ленивая загрузка, чтобы избежать циклического импорта)"""
    from app.bot.main import bot
    return bot


async def publish_channel_menu():
    """
    Опубликовать главное меню в канал и закрепить.
    """
    bot = await get_bot()
    
    booking_url = build_booking_url(0, source="tg_channel", medium="channel")
    
    menu_text = """
🏠 **Добро пожаловать в квартиры посуточно Краснодар!**

Выберите что вам нужно:

👇 Забронировать прямо сейчас
🏠 Смотреть каталог
🔥 Горящие предложения
❓ Вопросы и ответы
💬 Связаться с менеджером
🤖 Воспользоваться подбором в боте
    """.strip()
    
    # Inline кнопки
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", url=booking_url)],
        [InlineKeyboardButton(text="🏠 Каталог", url="https://t.me/my_apartments_bot?start=catalog")],
        [InlineKeyboardButton(text="🔥 Горящие", url="https://t.me/my_apartments_bot?start=hot")],
        [InlineKeyboardButton(text="❓ FAQ", url="https://t.me/my_apartments_bot?start=faq")],
        [InlineKeyboardButton(text="💬 Менеджер", url="https://t.me/ivan_support")],
        [InlineKeyboardButton(text="🤖 Подбор", url="https://t.me/my_apartments_bot")],
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Публикуем
    msg = await bot.send_message(
        chat_id=settings.channel_id,
        text=menu_text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    
    # Закрепляем
    await bot.pin_chat_message(
        chat_id=settings.channel_id,
        message_id=msg.message_id,
    )
    
    # Сохраняем в БД
    async with SessionLocal() as session:
        # Ищем старый меню
        existing = await session.execute(
            select(ChannelPost).where(ChannelPost.kind == ChannelPostKind.MENU)
        )
        old_post = existing.scalar_one_or_none()
        
        if old_post:
            old_post.message_id = msg.message_id
            old_post.last_published_at = None
        else:
            post = ChannelPost(
                kind=ChannelPostKind.MENU,
                channel_id=settings.channel_id,
                message_id=msg.message_id,
            )
            session.add(post)
        
        await session.commit()
    
    log_service.info("Меню опубликовано", message_id=msg.message_id)
    
    return msg.message_id


async def publish_all_apartments():
    """
    Опубликовать все активные квартиры отдельными постами.
    """
    bot = await get_bot()
    
    async with SessionLocal() as session:
        result = await session.execute(
            select(Apartment).where(Apartment.is_active == True)
            .order_by(Apartment.sort_order)
        )
        apartments = result.scalars().all()
    
    count = 0
    
    for apt in apartments:
        booking_url = build_booking_url(apt.id, source="tg_channel", medium="channel")
        
        # Текст карточки
        features = apt.features_json or []
        features_text = "\n".join([f"✨ {f}" for f in features[:5]])
        
        text = f"""
🏠 **{apt.title}** — {apt.district}

{features_text}

👥 Вместимость: {apt.guests_max} гостей
🛏️ {apt.beds_text}

💰 Точная цена и свободные даты — по кнопке
        """.strip()
        
        # Inline кнопки
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = [
            [InlineKeyboardButton(text="✅ Забронировать", url=booking_url)],
        ]
        
        if apt.map_url:
            buttons.append([InlineKeyboardButton(text="📍 На карте", url=apt.map_url)])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Публикуем
        msg = await bot.send_message(
            chat_id=settings.channel_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        
        # Сохраняем в БД
        async with SessionLocal() as session:
            existing = await session.execute(
                select(ChannelPost).where(
                    ChannelPost.apartment_id == apt.id,
                    ChannelPost.kind == ChannelPostKind.APARTMENT,
                )
            )
            post = existing.scalar_one_or_none()
            
            if post:
                post.message_id = msg.message_id
            else:
                post = ChannelPost(
                    apartment_id=apt.id,
                    kind=ChannelPostKind.APARTMENT,
                    channel_id=settings.channel_id,
                    message_id=msg.message_id,
                )
                session.add(post)
            
            await session.commit()
        
        count += 1
        log_service.info("Квартира опубликована", apartment_id=apt.id, message_id=msg.message_id)
    
    return count


async def publish_catalog():
    """
    Опубликовать каталог всех квартир в один пост.
    """
    bot = await get_bot()
    
    async with SessionLocal() as session:
        result = await session.execute(
            select(Apartment).where(Apartment.is_active == True)
        )
        apartments = result.scalars().all()
        
        # Ищем пост каталога
        catalog_post = await session.execute(
            select(ChannelPost).where(ChannelPost.kind == ChannelPostKind.CATALOG)
        )
        catalog_post = catalog_post.scalar_one_or_none()
    
    # Строим текст каталога
    catalog_text = "📚 **Полный каталог квартир:**\n\n"
    
    for apt in apartments:
        catalog_text += f"🏠 {apt.title}\n"
        catalog_text += f"   📍 {apt.district} | 👥 {apt.guests_max} гостей\n\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    booking_url = build_booking_url(0, source="tg_channel", medium="channel")
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", url=booking_url)],
        [InlineKeyboardButton(text="🤖 Подбор в боте", url="https://t.me/my_apartments_bot")],
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if catalog_post and catalog_post.message_id:
        # Обновляем
        await bot.edit_message_text(
            chat_id=settings.channel_id,
            message_id=catalog_post.message_id,
            text=catalog_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        log_service.info("Каталог обновлен")
    else:
        # Создаем
        msg = await bot.send_message(
            chat_id=settings.channel_id,
            text=catalog_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        
        async with SessionLocal() as session:
            post = ChannelPost(
                kind=ChannelPostKind.CATALOG,
                channel_id=settings.channel_id,
                message_id=msg.message_id,
            )
            session.add(post)
            await session.commit()
        
        log_service.info("Каталог опубликован", message_id=msg.message_id)