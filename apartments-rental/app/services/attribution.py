"""
Атрибуция бронирования по реферальным кодам и LeadID.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from typing import Optional

from app.db.models import ReferralCode, Booking, User, ReferralEvent
from app.config import get_settings
from app.logger import log_service

settings = get_settings()


async def attribute_booking(
    session: AsyncSession,
    booking: Booking,
    source_tag: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[ReferralCode]:
    """
    Атрибутировать бронирование к реферальному коду или пользователю.
    
    Правила:
    1. Если в source_tag содержится "partner_<code>" — привязать к коду
    2. Иначе если по телефону найден User — привязать к его коду
    3. Иначе вернуть None
    """
    
    referral_code = None
    
    # Правило 1: Extract из source_tag
    if source_tag and "partner_" in source_tag:
        code_str = source_tag.split("partner_")[-1]
        result = await session.execute(
            select(ReferralCode).where(
                ReferralCode.code == code_str,
                ReferralCode.is_active == True,
            )
        )
        referral_code = result.scalar_one_or_none()
        
        if referral_code:
            log_service.info(
                "Атрибутирована по source_tag",
                booking_id=booking.id,
                code=referral_code.code,
            )
            return referral_code
    
    # Правило 2: По телефону
    if phone:
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()
        
        if user and user.referral_code:
            log_service.info(
                "Атрибутирована по телефону",
                booking_id=booking.id,
                phone=phone,
                code=user.referral_code.code,
            )
            return user.referral_code
    
    log_service.info(
        "Бронирование не атрибутировано",
        booking_id=booking.id,
    )
    
    return None


async def check_attribution_window(
    session: AsyncSession,
    referral_code_id: int,
    user_id: int,
) -> bool:
    """
    Проверить, находится ли пользователь в окне атрибуции.
    
    Правила:
    - Пользователь должен был перейти по рефссылке за последние N дней
    - Не может быть self-ref
    """
    
    # Self-ref check
    code = await session.get(ReferralCode, referral_code_id)
    if code and code.user_id == user_id:
        log_service.warning(
            "Попытка self-ref",
            code_id=referral_code_id,
            user_id=user_id,
        )
        return False
    
    # Attribution window check
    window_start = datetime.utcnow() - timedelta(days=settings.attribution_window_days)
    
    result = await session.execute(
        select(ReferralEvent).where(
            and_(
                ReferralEvent.referral_code_id == referral_code_id,
                ReferralEvent.user_id == user_id,
                ReferralEvent.type == "start",
                ReferralEvent.created_at >= window_start,
            )
        )
    )
    
    event = result.scalar_one_or_none()
    
    if not event:
        log_service.warning(
            "User не в окне атрибуции",
            code_id=referral_code_id,
            user_id=user_id,
            window_days=settings.attribution_window_days,
        )
        return False
    
    return True