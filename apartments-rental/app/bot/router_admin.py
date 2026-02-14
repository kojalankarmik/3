"""
Маршруты администратора.
Управление квартирами, публикация в канал, статистика.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.bot.states import AdminStates
from app.bot import texts, keyboards
from app.config import get_settings
from app.db.crud import list_apartments, get_apartment
from app.db.models import Lead, Booking, BookingStatus, User, Apartment
from app.db.session import SessionLocal
from app.logger import log_bot

router = Router()
settings = get_settings()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Вход в админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    await message.answer(
        texts.Admin.main_menu,
        reply_markup=keyboards.admin_main_menu_keyboard(),
    )
    await state.set_state(AdminStates.main_menu)


@router.message(AdminStates.main_menu, F.text == "🏠 Квартиры")
async def admin_apartments_menu(message: Message, state: FSMContext):
    """Меню управления квартирами"""
    async with SessionLocal() as session:
        apartments = await list_apartments(session)
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    
    for apt in apartments:
        kb.button(text=f"🏠 {apt.title}")
    kb.button(text="➕ Добавить")
    kb.button(text="🏠 В меню")
    kb.adjust(1)
    
    await message.answer(
        texts.Admin.apartments_menu + f"\n\nВсего: {len(apartments)}",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(AdminStates.apartment_list)


@router.message(AdminStates.apartment_list)
async def admin_apartment_select(message: Message, state: FSMContext):
    """Выбор квартиры для редактирования"""
    if message.text == "🏠 В меню":
        await admin_panel(message, state)
        return
    
    if message.text == "➕ Добавить":
        await message.answer("📝 **Добавление новой квартиры** (скоро в админ-панели)")
        return
    
    # Найти квартиру по названию
    apt_title = message.text.replace("🏠 ", "")
    
    async with SessionLocal() as session:
        apt = await session.execute(
            select(Apartment).where(Apartment.title == apt_title)
        )
        apt = apt.scalar_one_or_none()
    
    if not apt:
        await message.answer("❌ Квартира не найдена")
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"edit_apt_{apt.id}")
    kb.button(text="🖼 Медиа", callback_data=f"media_apt_{apt.id}")
    kb.button(text="📤 Опубликовать", callback_data=f"publish_apt_{apt.id}")
    kb.button(text="🔄 Обновить", callback_data=f"update_apt_{apt.id}")
    kb.adjust(2, 2)
    
    await message.answer(
        f"🏠 **{apt.title}**\n\n"
        f"📍 {apt.district}\n"
        f"👥 Макс гостей: {apt.guests_max}\n"
        f"🛏️ {apt.beds_text}\n\n"
        f"Выберите действие:",
        reply_markup=kb.as_markup(),
    )


@router.message(AdminStates.main_menu, F.text == "📢 Публикация")
async def admin_publishing_menu(message: Message, state: FSMContext):
    """Меню публикации в канал"""
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="📌 Обновить меню")
    kb.button(text="🏠 Опубликовать все")
    kb.button(text="📚 Обновить каталог")
    kb.button(text="📚 Опубликовать FAQ")
    kb.button(text="🏠 В меню")
    kb.adjust(1)
    
    await message.answer(
        texts.Admin.publishing_menu,
        reply_markup=kb.as_markup(),
    )
    await state.set_state(AdminStates.publishing_menu)


@router.message(AdminStates.publishing_menu, F.text == "📌 Обновить меню")
async def publish_menu_handler(message: Message):
    """Публикация главного меню канала"""
    try:
        # Импортируем здесь, чтобы избежать циклического импорта
        from app.services.publishing import publish_channel_menu
        
        await publish_channel_menu()
        await message.answer(texts.Admin.publish_menu_done)
        log_bot.info("Меню опубликовано", admin_id=message.from_user.id)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        log_bot.error("Ошибка публикации меню", error=str(e))


@router.message(AdminStates.publishing_menu, F.text == "🏠 Опубликовать все")
async def publish_apartments_handler(message: Message):
    """Публикация всех квартир"""
    try:
        # Импортируем здесь, чтобы избежать циклического импорта
        from app.services.publishing import publish_all_apartments
        
        count = await publish_all_apartments()
        await message.answer(texts.Admin.publish_apartments_done.format(count=count))
        log_bot.info("Квартиры опубликованы", count=count, admin_id=message.from_user.id)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        log_bot.error("Ошибка публикации квартир", error=str(e))


@router.message(AdminStates.publishing_menu, F.text == "📚 Обновить каталог")
async def publish_catalog_handler(message: Message):
    """Публикация каталога"""
    try:
        # Импортируем здесь, чтобы избежать циклического импорта
        from app.services.publishing import publish_catalog
        
        await publish_catalog()
        await message.answer("✅ Каталог обновлен")
        log_bot.info("Каталог опубликован", admin_id=message.from_user.id)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        log_bot.error("Ошибка публикации каталога", error=str(e))


@router.message(AdminStates.main_menu, F.text == "📩 Лиды")
async def admin_leads_menu(message: Message, state: FSMContext):
    """Меню управления лидами"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count(Lead.id)).where(Lead.status == "new")
        )
        new_count = result.scalar() or 0
        
        result = await session.execute(
            select(Lead).where(Lead.status == "new").limit(5)
        )
        leads = result.scalars().all()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    
    for lead in leads:
        kb.button(text=f"📋 {lead.contact}", callback_data=f"lead_{lead.id}")
    kb.adjust(1)
    
    await message.answer(
        texts.Admin.leads_menu.format(new_count=new_count),
        reply_markup=kb.as_markup(),
    )


@router.message(AdminStates.main_menu, F.text == "📅 Брони")
async def admin_bookings_menu(message: Message, state: FSMContext):
    """Меню управления бронями"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count(Booking.id))
        )
        total = result.scalar() or 0
        
        result = await session.execute(
            select(Booking).order_by(Booking.created_at.desc()).limit(5)
        )
        bookings = result.scalars().all()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    
    for booking in bookings:
        status_emoji = {
            "created": "📝",
            "confirmed": "✅",
            "paid": "💰",
            "canceled": "❌",
        }.get(booking.status, "❓")
        
        kb.button(
            text=f"{status_emoji} {booking.external_id}",
            callback_data=f"booking_{booking.id}"
        )
    kb.adjust(1)
    
    await message.answer(
        f"📅 **Брони**\n\nВсего: {total}\n\nПоследние:",
        reply_markup=kb.as_markup(),
    )


@router.message(AdminStates.main_menu, F.text == "🎁 Рефералы")
async def admin_referrals_menu(message: Message, state: FSMContext):
    """Меню рефералов"""
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="📋 Мои рефералы")
    kb.button(text="💰 Выплаты")
    kb.button(text="🏠 В меню")
    kb.adjust(1)
    
    await message.answer(
        "🎁 **Реферальная программа**",
        reply_markup=kb.as_markup(),
    )


@router.message(AdminStates.main_menu, F.text == "📊 Статистика")
async def admin_stats_menu(message: Message, state: FSMContext):
    """Статистика"""
    async with SessionLocal() as session:
        # Последние 30 дней
        since = datetime.utcnow() - timedelta(days=30)
        
        leads_count = await session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= since)
        )
        leads_count = leads_count.scalar() or 0
        
        bookings_result = await session.execute(
            select(func.count(Booking.id)).where(Booking.created_at >= since)
        )
        bookings_count = bookings_result.scalar() or 0
        
        paid_result = await session.execute(
            select(func.sum(Booking.total_amount)).where(
                Booking.status == "paid",
                Booking.created_at >= since,
            )
        )
        paid_amount = paid_result.scalar() or 0
    
    conversion = (bookings_count / leads_count * 100) if leads_count > 0 else 0
    
    await message.answer(
        texts.Admin.stats_menu.format(
            period=30,
            leads_count=leads_count,
            bookings_count=bookings_count,
            paid_amount=paid_amount,
            conversion=f"{conversion:.1f}",
        ),
    )