"""
Маршруты пользовательского бота.
Обработка user-сценариев через Aiogram 3.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import UserStates
from app.bot import texts, keyboards, utils
from app.db.crud import (
    get_or_create_user, list_apartments, get_apartment,
    create_lead, get_or_create_referral_code, get_referral_code, log_referral_event,
)
from app.db.session import SessionLocal
from app.logger import log_bot

router = Router()


# ============= START & MAIN MENU =============

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка /start с опциональными параметрами"""
    async with SessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
    
    # Парсим параметр start
    args = message.text.split()
    referral_code = None
    if len(args) > 1:
        param = args[1]
        if param.startswith("r_"):
            referral_code = param[2:]
            async with SessionLocal() as session:
                ref = await get_referral_code(session, referral_code)
                if ref:
                    # Логируем старт по рефссылке
                    await log_referral_event(
                        session, ref.id, "start", user_id=user.id
                    )
                    await message.answer(
                        texts.Welcome.intro + "\n\n" + texts.Welcome.with_referral,
                        reply_markup=keyboards.main_menu_keyboard(),
                    )
                    await state.set_state(UserStates.main_menu)
                    return
    
    await message.answer(
        texts.Welcome.intro,
        reply_markup=keyboards.main_menu_keyboard(),
    )
    await state.set_state(UserStates.main_menu)


@router.message(StateFilter(UserStates.main_menu), F.text == "🏠 Подобрать квартиру")
async def wizard_start(message: Message, state: FSMContext):
    """Начало wizard подбора"""
    await message.answer(
        texts.Wizard.dates_help,
        reply_markup=keyboards.wizard_dates_keyboard(),
    )
    await state.set_state(UserStates.wizard_dates)


@router.message(UserStates.wizard_dates)
async def wizard_dates(message: Message, state: FSMContext):
    """Обработка выбора дат"""
    data = await state.get_data()
    
    if message.text == texts.Buttons.back:
        await message.answer(texts.Welcome.intro, reply_markup=keyboards.main_menu_keyboard())
        await state.set_state(UserStates.main_menu)
        return
    elif message.text == texts.Buttons.menu:
        await message.answer(texts.Welcome.intro, reply_markup=keyboards.main_menu_keyboard())
        await state.set_state(UserStates.main_menu)
        return
    elif message.text == texts.Buttons.cancel:
        await message.answer("❌ Отменено", reply_markup=keyboards.main_menu_keyboard())
        await state.set_state(UserStates.main_menu)
        return
    
    # Обработка дат
    if message.text == texts.Buttons.today:
        today, tomorrow = utils.get_today_tomorrow()
        check_in, check_out = today, tomorrow
    elif message.text == texts.Buttons.tomorrow:
        today, tomorrow = utils.get_today_tomorrow()
        tomorrow2 = (datetime.fromisoformat(tomorrow) + timedelta(days=1)).strftime("%Y-%m-%d")
        check_in, check_out = tomorrow, tomorrow2
    else:
        # Парсим ввод
        result = utils.parse_date_input(message.text)
        if not result:
            await message.answer(texts.Errors.invalid_dates)
            return
        check_in, check_out = result
    
    await state.update_data(check_in=check_in, check_out=check_out)
    
    await message.answer(
        texts.Wizard.guests_help,
        reply_markup=keyboards.wizard_guests_keyboard(),
    )
    await state.set_state(UserStates.wizard_guests)


@router.message(UserStates.wizard_guests)
async def wizard_guests(message: Message, state: FSMContext):
    """Обработка выбора количества гостей"""
    guests_map = {
        texts.Buttons.guests_1: 1,
        texts.Buttons.guests_2: 2,
        texts.Buttons.guests_3: 3,
        texts.Buttons.guests_4: 4,
        texts.Buttons.guests_5: 5,
        texts.Buttons.guests_6_plus: 6,
    }
    
    if message.text == texts.Buttons.back:
        await message.answer(texts.Wizard.dates_help, reply_markup=keyboards.wizard_dates_keyboard())
        await state.set_state(UserStates.wizard_dates)
        return
    
    guests = guests_map.get(message.text)
    if not guests:
        await message.answer(texts.Errors.invalid_input)
        return
    
    await state.update_data(guests=guests)
    
    # Получить районы
    async with SessionLocal() as session:
        apartments = await list_apartments(session)
        districts = sorted(set(apt.district for apt in apartments if apt.district))
    
    await message.answer(
        texts.Wizard.district_help,
        reply_markup=keyboards.wizard_district_keyboard(districts),
    )
    await state.set_state(UserStates.wizard_district)


@router.message(UserStates.wizard_district)
async def wizard_district(message: Message, state: FSMContext):
    """Обработка выбора района"""
    if message.text == texts.Buttons.back:
        await message.answer(texts.Wizard.guests_help, reply_markup=keyboards.wizard_guests_keyboard())
        await state.set_state(UserStates.wizard_guests)
        return
    
    district = None if message.text == texts.Buttons.district_any else message.text.replace("📍 ", "")
    
    await state.update_data(district=district)
    
    await message.answer(
        texts.Wizard.budget_help,
        reply_markup=keyboards.wizard_budget_keyboard(),
    )
    await state.set_state(UserStates.wizard_budget)


@router.message(UserStates.wizard_budget)
async def wizard_budget(message: Message, state: FSMContext):
    """Обработка выбора бюджета"""
    budget_map = {
        texts.Buttons.budget_2500: (0, 2500),
        texts.Buttons.budget_3500: (0, 3500),
        texts.Buttons.budget_4500: (0, 4500),
        texts.Buttons.budget_any: (0, 999999),
    }
    
    if message.text == texts.Buttons.back:
        data = await state.get_data()
        districts = [data.get("district")] if data.get("district") else []
        await message.answer(
            texts.Wizard.district_help,
            reply_markup=keyboards.wizard_district_keyboard(districts or ["Центр"]),
        )
        await state.set_state(UserStates.wizard_district)
        return
    
    budget = budget_map.get(message.text)
    if not budget:
        await message.answer(texts.Errors.invalid_input)
        return
    
    await state.update_data(budget_min=budget[0], budget_max=budget[1])
    
    # Показываем результаты
    data = await state.get_data()
    
    async with SessionLocal() as session:
        apartments = await list_apartments(session)
        
        # Фильтруем по критериям
        filtered = [
            apt for apt in apartments
            if (data.get("district") is None or apt.district == data.get("district"))
            and apt.guests_max >= data.get("guests", 1)
        ]
    
    if not filtered:
        await message.answer(
            texts.Wizard.no_results + "\n\n" + texts.Wizard.contact_us,
            reply_markup=keyboards.back_menu_cancel_keyboard(),
        )
        await state.set_state(UserStates.main_menu)
        return
    
    # Показываем результаты по одному
    await state.update_data(results=filtered, result_index=0)
    await show_result(message, state, filtered)


async def show_result(message: Message, state: FSMContext, results: list):
    """Показать одну карточку квартиры"""
    data = await state.get_data()
    index = data.get("result_index", 0)
    
    if index >= len(results):
        await message.answer(
            "✅ Это все варианты!",
            reply_markup=keyboards.main_menu_keyboard(),
        )
        await state.set_state(UserStates.main_menu)
        return
    
    apt = results[index]
    booking_url = utils.build_booking_url(apt.id, source="tg_bot", medium="bot")
    
    card_text = utils.format_apartment_card(apt, booking_url)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Проверить цену", url=booking_url)
    if apt.map_url:
        kb.button(text="📍 На карте", url=apt.map_url)
    kb.button(text="💬 Вопрос", callback_data=f"ask_apt_{apt.id}")
    
    # Навигация по результатам
    if index < len(results) - 1:
        kb.button(text="➡️ Дальше", callback_data=f"next_apt_{index + 1}")
    if index > 0:
        kb.button(text="⬅️ Назад", callback_data=f"prev_apt_{index - 1}")
    
    kb.adjust(2, 1, 2)
    
    await message.answer(card_text, reply_markup=kb.as_markup(), parse_mode="Markdown")


# ============= CATALOG & HOT OFFERS =============

@router.message(StateFilter(UserStates.main_menu), F.text == "📚 Каталог")
async def catalog_menu(message: Message, state: FSMContext):
    """Каталог по категориям"""
    async with SessionLocal() as session:
        apartments = await list_apartments(session)
        
        # Группируем по тегам
        tags_dict = {}
        for apt in apartments:
            for tag in apt.tags:
                if tag.tag not in tags_dict:
                    tags_dict[tag.tag] = []
                tags_dict[tag.tag].append(apt)
    
    kb = ReplyKeyboardBuilder()
    for tag in tags_dict.keys():
        kb.button(text=f"📍 {tag}")
    kb.button(text="🏠 В меню")
    kb.adjust(2)
    
    await message.answer(
        "📚 **Каталог по категориям:**",
        reply_markup=kb.as_markup(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "🔥 Горящие даты")
async def hot_offers(message: Message, state: FSMContext):
    """Горящие предложения"""
    # TODO: Получить из БД таблица HotOffers
    await message.answer(
        "🔥 **Специальные предложения на этой неделе:**\n\n"
        "📝 Скоро появятся лучшие предложения!\n\n"
        "Следите за обновлениями или напишите менеджеру 👇",
        reply_markup=keyboards.main_menu_keyboard(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "❓ Правила / FAQ")
async def faq_menu(message: Message, state: FSMContext):
    """Меню FAQ"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔑 Заезд/выезд")
    kb.button(text="💳 Залог и платежи")
    kb.button(text="❌ Отмена")
    kb.button(text="🐕 Животные")
    kb.button(text="🚭 Курение")
    kb.button(text="📞 Правила")
    kb.button(text="🏠 В меню")
    kb.adjust(2, 2, 2, 1)
    
    await message.answer(
        "❓ **Часто задаваемые вопросы:**",
        reply_markup=kb.as_markup(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "🔑 Заезд/выезд")
async def faq_checkin(message: Message):
    await message.answer(
        texts.FAQ.checkin_checkout,
        reply_markup=keyboards.back_menu_cancel_keyboard(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "💳 Залог и платежи")
async def faq_deposit(message: Message):
    await message.answer(
        texts.FAQ.deposit,
        reply_markup=keyboards.back_menu_cancel_keyboard(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "❌ Отмена")
async def faq_cancellation(message: Message):
    await message.answer(
        texts.FAQ.cancellation,
        reply_markup=keyboards.back_menu_cancel_keyboard(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "🐕 Животные")
async def faq_pets(message: Message):
    await message.answer(
        texts.FAQ.pets,
        reply_markup=keyboards.back_menu_cancel_keyboard(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "🚭 Курение")
async def faq_smoking(message: Message):
    await message.answer(
        texts.FAQ.smoking,
        reply_markup=keyboards.back_menu_cancel_keyboard(),
    )


# ============= CONTACT & LEADS =============

@router.message(StateFilter(UserStates.main_menu), F.text == "💬 Связаться")
async def contact_menu(message: Message, state: FSMContext):
    """Меню контактов"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📞 Менеджер")
    kb.button(text="📝 Оставить заявку")
    kb.button(text="🏠 В меню")
    kb.adjust(2, 1)
    
    await message.answer(
        "💬 **Как мы можем помочь?**",
        reply_markup=kb.as_markup(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "📞 Менеджер")
async def contact_manager(message: Message):
    """Ссылка на менеджера"""
    # TODO: Получить из конфига
    manager_username = "your_manager"
    
    await message.answer(
        f"👤 **Напишите нашему менеджеру:**\n\n"
        f"[@{manager_username}](tg://user?id=123456789)\n\n"
        f"Он поможет с выбором, ответит на вопросы и оформит бронь.",
        reply_markup=keyboards.main_menu_keyboard(),
        parse_mode="Markdown",
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "📝 Оставить заявку")
async def contact_form_start(message: Message, state: FSMContext):
    """Начало формы обратной связи"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏠 Подобрать квартиру")
    kb.button(text="❓ Вопрос")
    kb.button(text="💬 Отзыв")
    kb.button(text="🏠 В меню")
    kb.adjust(2, 2)
    
    await message.answer(
        "📝 **О чем вы хотите написать?**",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(UserStates.contact_form_topic)


@router.message(UserStates.contact_form_topic)
async def contact_form_topic(message: Message, state: FSMContext):
    """Тема заявки"""
    topic = message.text
    
    if topic in ["🏠 В меню"]:
        await message.answer(texts.Welcome.intro, reply_markup=keyboards.main_menu_keyboard())
        await state.set_state(UserStates.main_menu)
        return
    
    await state.update_data(topic=topic)
    
    await message.answer(
        "✍️ **Расскажите подробнее** (или нажмите 'Пропустить')",
        reply_markup=ReplyKeyboardBuilder()
        .button(text="Пропустить")
        .button(text="🏠 В меню")
        .adjust(1, 1)
        .as_markup(),
    )
    await state.set_state(UserStates.contact_form_message)


@router.message(UserStates.contact_form_message)
async def contact_form_message(message: Message, state: FSMContext):
    """Сообщение заявки"""
    msg_text = message.text if message.text != "Пропустить" else ""
    await state.update_data(message=msg_text)
    
    await message.answer(
        "☎️ **Как с вами связаться?** (телефон или Telegram)",
        reply_markup=ReplyKeyboardBuilder()
        .button(text="📱 Поделиться контактом", request_contact=True)
        .button(text="🏠 В меню")
        .adjust(1, 1)
        .as_markup(),
    )
    await state.set_state(UserStates.contact_form_contact)


@router.message(UserStates.contact_form_contact)
async def contact_form_finish(message: Message, state: FSMContext):
    """Завершение формы"""
    data = await state.get_data()
    
    contact = message.contact.phone_number if message.contact else message.text
    
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        
        lead = await create_lead(
            session,
            user_id=user.id,
            contact=contact,
            status="new",
            source_tag="tg_bot_contact_form",
        )
    
    await message.answer(
        "✅ **Спасибо! Ваша заявка принята.**\n\n"
        "Менеджер свяжется с вами в течение часа.",
        reply_markup=keyboards.main_menu_keyboard(),
    )
    await state.set_state(UserStates.main_menu)
    
    # Уведомляем менеджера
    log_bot.info("Новая заявка", lead_id=lead.id, contact=contact)


# ============= REFERRAL PROGRAM =============

@router.message(StateFilter(UserStates.main_menu), F.text == "🎁 Скидка / Рефералка")
async def referral_menu(message: Message, state: FSMContext):
    """Меню реферальной программы"""
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        ref_code = await get_or_create_referral_code(session, user.id)
    
    ref_url = f"https://t.me/your_bot?start=r_{ref_code.code}"
    
    kb = ReplyKeyboardBuilder()
    kb.button(text="📋 Моя ссылка")
    kb.button(text="📊 Статистика")
    kb.button(text="💰 Мои выплаты")
    kb.button(text="🏠 В меню")
    kb.adjust(2, 2)
    
    await message.answer(
        f"🎁 **Реферальная программа**\n\n"
        f"Приглашайте друзей и получайте бонусы!\n\n"
        f"• За каждого приглашенного друга: 500₽\n"
        f"• За его первую оплаченную бронь: 5% от суммы\n\n"
        f"👇 Ваша уникальная ссылка",
        reply_markup=kb.as_markup(),
    )


@router.message(StateFilter(UserStates.main_menu), F.text == "📋 Моя ссылка")
async def referral_link(message: Message):
    """Показать реферальную ссылку"""
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        ref_code = await get_or_create_referral_code(session, user.id)
    
    ref_url = f"https://t.me/your_bot?start=r_{ref_code.code}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Скопировать", url=ref_url)
    kb.button(text="📤 Поделиться", url=f"https://t.me/share/url?url={ref_url}")
    kb.adjust(2)
    
    await message.answer(
        f"🔗 **Ваша реферальная ссылка:**\n\n"
        f"`{ref_url}`\n\n"
        f"Отправьте эту ссылку друзьям и получайте бонусы!",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown",
    )


# ============= UTILITIES =============

@router.message(F.text == "🏠 В меню")
async def back_to_menu(message: Message, state: FSMContext):
    """Вернуться в главное меню"""
    await message.answer(
        texts.Welcome.intro,
        reply_markup=keyboards.main_menu_keyboard(),
    )
    await state.set_state(UserStates.main_menu)


@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ Отменено",
        reply_markup=keyboards.main_menu_keyboard(),
    )
    await state.set_state(UserStates.main_menu)


@router.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    """Вернуться на шаг назад"""
    current_state = await state.get_state()
    
    state_transitions = {
        UserStates.wizard_guests: UserStates.wizard_dates,
        UserStates.wizard_district: UserStates.wizard_guests,
        UserStates.wizard_budget: UserStates.wizard_district,
    }
    
    previous_state = state_transitions.get(current_state)
    if previous_state:
        await state.set_state(previous_state)
        # Повторно показываем соответствующий экран
        await message.answer("⬅️ Вернулись назад")