"""
CRUD операции для часто используемых сущностей.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, func, and_
from datetime import datetime, timedelta
from typing import Optional, List

from app.db.models import (
    User, Apartment, Lead, Booking, ReferralCode, ReferralEvent,
    WebhookEvent, Payout, ChannelPost,
)
from app.config import get_settings

settings = get_settings()


# ============= USER =============

async def get_or_create_user(session: AsyncSession, telegram_id: int, **kwargs) -> User:
    """Получить или создать пользователя"""
    user = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user.scalar_one_or_none()
    
    if not user:
        user = User(telegram_id=telegram_id, **kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ============= APARTMENT =============

async def list_apartments(session: AsyncSession, active_only: bool = True) -> List[Apartment]:
    """Список квартир"""
    query = select(Apartment).options(selectinload(Apartment.media), selectinload(Apartment.tags))
    if active_only:
        query = query.where(Apartment.is_active == True)
    query = query.order_by(Apartment.sort_order, Apartment.id)
    
    result = await session.execute(query)
    return result.unique().scalars().all()


async def get_apartment(session: AsyncSession, apartment_id: int) -> Optional[Apartment]:
    result = await session.execute(
        select(Apartment).options(selectinload(Apartment.media), selectinload(Apartment.tags))
        .where(Apartment.id == apartment_id)
    )
    return result.unique().scalar_one_or_none()


# ============= LEAD =============

async def create_lead(session: AsyncSession, **kwargs) -> Lead:
    """Создать лид"""
    lead = Lead(**kwargs)
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


async def get_new_leads(session: AsyncSession, limit: int = 10) -> List[Lead]:
    """Получить новые лиды"""
    from app.db.models import LeadStatus
    result = await session.execute(
        select(Lead)
        .where(Lead.status == LeadStatus.NEW)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ============= BOOKING =============

async def get_or_create_booking(session: AsyncSession, external_id: str, **kwargs) -> tuple[Booking, bool]:
    """
    Получить или создать бронь (идемпотентно).
    Возвращает (booking, created: bool)
    """
    booking = await session.execute(
        select(Booking).where(Booking.external_id == external_id)
    )
    booking = booking.scalar_one_or_none()
    
    if booking:
        return booking, False
    
    booking = Booking(external_id=external_id, **kwargs)
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking, True


async def update_booking_status(session: AsyncSession, booking_id: int, status: str):
    """Обновить статус брони"""
    await session.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(status=status, updated_at=datetime.utcnow())
    )
    await session.commit()


# ============= REFERRAL =============

async def get_referral_code(session: AsyncSession, code: str) -> Optional[ReferralCode]:
    """Получить реферальный код"""
    result = await session.execute(
        select(ReferralCode).options(selectinload(ReferralCode.user))
        .where(ReferralCode.code == code, ReferralCode.is_active == True)
    )
    return result.unique().scalar_one_or_none()


async def get_or_create_referral_code(session: AsyncSession, user_id: int) -> ReferralCode:
    """Получить или создать реферальный код"""
    code = await session.execute(
        select(ReferralCode).where(ReferralCode.user_id == user_id)
    )
    code = code.scalar_one_or_none()
    
    if code:
        return code
    
    # Генерируем уникальный код
    import secrets
    base_code = f"ref_{user_id}_{secrets.token_hex(4)}"
    
    code = ReferralCode(user_id=user_id, code=base_code)
    session.add(code)
    await session.commit()
    await session.refresh(code)
    return code


async def log_referral_event(session: AsyncSession, referral_code_id: int, event_type: str, **kwargs):
    """Логировать событие реферальной программы"""
    event = ReferralEvent(referral_code_id=referral_code_id, type=event_type, **kwargs)
    session.add(event)
    await session.commit()


async def get_attributed_referral_code(
    session: AsyncSession, user_id: int
) -> Optional[ReferralCode]:
    """
    Получить реферальный код, который привел этого пользователя,
    в окне attribution_window_days
    """
    window_start = datetime.utcnow() - timedelta(days=settings.attribution_window_days)
    
    result = await session.execute(
        select(ReferralCode)
        .where(
            and_(
                ReferralEvent.user_id == user_id,
                ReferralCode.id == ReferralEvent.referral_code_id,
                ReferralEvent.type == "start",
                ReferralEvent.created_at >= window_start,
            )
        )
    )
    return result.scalar_one_or_none()


# ============= WEBHOOK =============

async def save_webhook_event(session: AsyncSession, **kwargs) -> WebhookEvent:
    """Сохранить сырое событие вебхука"""
    event = WebhookEvent(**kwargs)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def get_webhook_event_by_hash(
    session: AsyncSession, provider: str, payload_hash: str
) -> Optional[WebhookEvent]:
    """Проверить, обработано ли это событие"""
    result = await session.execute(
        select(WebhookEvent).where(
            and_(
                WebhookEvent.provider == provider,
                WebhookEvent.payload_hash == payload_hash,
            )
        )
    )
    return result.scalar_one_or_none()


async def mark_webhook_processed(session: AsyncSession, webhook_event_id: int):
    """Отметить событие как обработанное"""
    await session.execute(
        update(WebhookEvent)
        .where(WebhookEvent.id == webhook_event_id)
        .values(processed_at=datetime.utcnow())
    )
    await session.commit()