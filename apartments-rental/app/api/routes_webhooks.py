"""
Webhook endpoints для приема бронирований от модуля бронирования.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.config import get_settings
from app.db.session import get_session
from app.db.crud import (
    get_or_create_booking, save_webhook_event, get_webhook_event_by_hash,
    mark_webhook_processed, log_referral_event, get_or_create_user,
)
from app.services.webhook_parser import WebhookParser, calculate_payload_hash
from app.services.attribution import attribute_booking, check_attribution_window
from app.services.referrals import create_payout_for_booking
from app.logger import log_webhook

router = APIRouter()
settings = get_settings()


@router.post("/booking")
async def webhook_booking(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Вебхук для приема бронирований.
    
    Проверяет:
    - Secret для авторизации
    - Идемпотентность по payload_hash
    - Парсит payload универсальным парсером
    - Обновляет Booking, создает Payout, логирует события
    """
    
    # 1. Проверка secret
    if x_webhook_secret != settings.webhook_secret:
        log_webhook.warning("Неверный webhook secret")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 2. Получить raw payload
    body = await request.body()
    payload_hash = calculate_payload_hash(body)
    
    # Парсим JSON
    try:
        payload = json.loads(body)
    except Exception as e:
        log_webhook.error("Ошибка парсинга JSON", error=str(e))
        return {"ok": False, "error": "Invalid JSON"}
    
    # 3. Проверка идемпотентности (по хешу)
    existing_event = await get_webhook_event_by_hash(
        session, provider="homereserve", payload_hash=payload_hash
    )
    
    if existing_event:
        log_webhook.info(
            "Вебхук уже обработан (дубликат)",
            payload_hash=payload_hash,
        )
        return {"ok": True, "duplicate": True}
    
    # 4. Парсим через универсальный парсер
    parser = WebhookParser(provider="homereserve", payload=payload)
    parsed = parser.parse()
    
    if not parsed:
        # Сохраняем even так, чтобы не обрабатывать снова
        event = await save_webhook_event(
            session,
            provider="homereserve",
            event_id=payload.get("id"),
            event_type="unknown",
            payload_hash=payload_hash,
            raw_payload_json=payload,
        )
        await mark_webhook_processed(session, event.id)
        
        return {"ok": False, "error": "Could not parse webhook"}
    
    # 5. Сохраняем сырое событие
    event = await save_webhook_event(
        session,
        provider=parsed["provider"],
        event_id=parsed["event_id"],
        event_type=parsed["event_type"],
        payload_hash=payload_hash,
        raw_payload_json=payload,
    )
    
    # 6. Upsert Booking
    external_id = parsed["event_id"]
    
    booking, created = await get_or_create_booking(
        session,
        external_id=external_id,
        status=parsed["event_type"],
        check_in=parsed["check_in"],
        check_out=parsed["check_out"],
        total_amount=parsed["total_amount"],
        currency=parsed["currency"],
        source_tag=parsed.get("source_tag"),
        raw_payload_json=payload,
    )
    
    # 7. Атрибуция
    source_tag = payload.get("source_tag") or payload.get("utm_source")
    ref_code = await attribute_booking(
        session,
        booking,
        source_tag=source_tag,
        phone=parsed.get("phone"),
    )
    
    # 8. Если статус PAID — создаем Payout
    if parsed["event_type"] == "paid" and ref_code:
        # Проверяем окно атрибуции
        # TODO: Получить user_id из phone или другого способа
        
        payout = await create_payout_for_booking(session, ref_code, booking)
        
        if payout:
            log_webhook.info(
                "Выплата создана",
                payout_id=payout.id,
                booking_id=booking.id,
            )
        
        # Логируем событие для реферала
        await log_referral_event(
            session,
            ref_code.id,
            "booking_paid",
            booking_id=booking.id,
        )
    
    # 9. Отмечаем обработанным
    await mark_webhook_processed(session, event.id)
    
    log_webhook.info(
        "Вебхук обработан",
        event_id=event.id,
        booking_id=booking.id,
        event_type=parsed["event_type"],
    )
    
    return {
        "ok": True,
        "booking_id": booking.id,
        "payout_created": parsed["event_type"] == "paid" and ref_code is not None,
    }