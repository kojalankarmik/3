"""
Бизнес-логика реферальной программы.
Создание выплат, расчеты, уведомления.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.models import (
    ReferralCode, Booking, Payout, PayoutStatus, ReferralEvent,
)
from app.config import get_settings
from app.logger import log_service

settings = get_settings()


async def create_payout_for_booking(
    session: AsyncSession,
    referral_code: ReferralCode,
    booking: Booking,
) -> Optional[Payout]:
    """
    Создать выплату за оплаченное бронирование.
    
    Расчеты:
    - fixed: фиксированная сумма за бронь
    - percent: процент от суммы брони
    """
    
    # Проверяем, нет ли уже выплаты
    existing = await session.execute(
        select(Payout).where(Payout.booking_id == booking.id)
    )
    
    if existing.scalar_one_or_none():
        log_service.warning(
            "Выплата уже существует",
            booking_id=booking.id,
        )
        return None
    
    # Расчет суммы
    amount = 0
    
    if settings.ref_payout_mode == "fixed":
        amount = settings.ref_payout_fixed
    elif settings.ref_payout_mode == "percent":
        if booking.total_amount:
            amount = int(booking.total_amount * settings.ref_payout_percent / 100)
    
    payout = Payout(
        referral_code_id=referral_code.id,
        booking_id=booking.id,
        amount=amount,
        status=PayoutStatus.PENDING,
    )
    
    session.add(payout)
    await session.commit()
    await session.refresh(payout)
    
    log_service.info(
        "Выплата создана",
        payout_id=payout.id,
        booking_id=booking.id,
        amount=amount,
    )
    
    return payout