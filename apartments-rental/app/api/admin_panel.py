"""
Простая веб-админ-панель на FastAPI + Jinja2.
Без сложностей — просто CRUD с HTML.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
import os

from app.config import get_settings
from app.db.session import get_session
from app.db.models import (
    Apartment, Lead, Booking, User, ReferralCode, Payout,
    ApartmentTag, ApartmentMedia,
)
from app.logger import log_api

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

# Jinja2
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def check_admin_auth(request: Request):
    """Simple BasicAuth check"""
    auth = request.headers.get("Authorization")
    if not auth:
        return False
    
    try:
        scheme, credentials = auth.split()
        if scheme.lower() != "basic":
            return False
        
        import base64
        decoded = base64.b64decode(credentials).decode()
        username, password = decoded.split(":", 1)
        
        return (
            username == settings.admin_panel_user
            and password == settings.admin_panel_pass
        )
    except:
        return False


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """Главная панель администратора"""
    if not check_admin_auth(request):
        return """
        <html>
        <body style="text-align: center; margin-top: 50px;">
            <h1>🔐 Требуется авторизация</h1>
            <p>Используйте Basic Auth для входа</p>
        </body>
        </html>
        """, 401
    
    # Статистика за последние 30 дней
    since = datetime.utcnow() - timedelta(days=30)
    
    leads_count = await session.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= since)
    )
    leads_count = leads_count.scalar() or 0
    
    bookings_count = await session.execute(
        select(func.count(Booking.id)).where(Booking.created_at >= since)
    )
    bookings_count = bookings_count.scalar() or 0
    
    paid_amount = await session.execute(
        select(func.sum(Booking.total_amount)).where(
            Booking.status == "paid",
            Booking.created_at >= since,
        )
    )
    paid_amount = paid_amount.scalar() or 0
    
    conversion = (bookings_count / leads_count * 100) if leads_count > 0 else 0
    
    # Top apartments
    top_apts = await session.execute(
        select(Apartment).limit(5)
    )
    top_apts = top_apts.scalars().all()
    
    html = f"""
    <html>
    <head>
        <title>Админ-панель</title>
        <style>
            body {{ font-family: Arial; margin: 20px; }}
            .stat {{ display: inline-block; margin: 20px; padding: 20px; border: 1px solid #ccc; border-radius: 5px; }}
            .stat h3 {{ margin: 0; }}
            .stat .value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
            table {{ border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            a {{ color: #0066cc; text-decoration: none; margin-right: 10px; }}
        </style>
    </head>
    <body>
        <h1>📊 Админ-пан��ль</h1>
        
        <div class="stat">
            <h3>Заявки (30 дней)</h3>
            <div class="value">{leads_count}</div>
        </div>
        
        <div class="stat">
            <h3>Брони (30 дней)</h3>
            <div class="value">{bookings_count}</div>
        </div>
        
        <div class="stat">
            <h3>Оплачено (RUB)</h3>
            <div class="value">{paid_amount:,}</div>
        </div>
        
        <div class="stat">
            <h3>Конверсия</h3>
            <div class="value">{conversion:.1f}%</div>
        </div>
        
        <h2>🔗 Ссылки</h2>
        <ul>
            <li><a href="/admin/apartments">🏠 Квартиры</a></li>
            <li><a href="/admin/leads">📩 Лиды</a></li>
            <li><a href="/admin/bookings">📅 Брони</a></li>
            <li><a href="/admin/referrals">🎁 Рефералы</a></li>
            <li><a href="/admin/webhooks">🪝 Вебхуки</a></li>
        </ul>
        
        <h2>🏠 Топ квартиры</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Район</th>
                <th>Гостей</th>
                <th>Активна</th>
            </tr>
    """
    
    for apt in top_apts:
        html += f"""
            <tr>
                <td>{apt.id}</td>
                <td><a href="/admin/apartments/{apt.id}">{apt.title}</a></td>
                <td>{apt.district}</td>
                <td>{apt.guests_max}</td>
                <td>{'✅' if apt.is_active else '❌'}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html


@router.get("/apartments", response_class=HTMLResponse)
async def list_apartments_admin(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Список квартир"""
    if not check_admin_auth(request):
        return "Unauthorized", 401
    
    result = await session.execute(select(Apartment))
    apartments = result.scalars().all()
    
    html = """
    <html>
    <head>
        <title>Квартиры</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background-color: #f2f2f2; }
            a { color: #0066cc; text-decoration: none; }
            .action-btn { padding: 5px 10px; margin: 2px; background: #0066cc; color: white; border: none; border-radius: 3px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>🏠 Квартиры</h1>
        <a href="/admin/dashboard" class="action-btn">⬅️ Назад</a>
        <a href="/admin/apartments/new" class="action-btn">➕ Добавить</a>
        
        <table>
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Район</th>
                <th>Гостей</th>
                <th>Активна</th>
                <th>Действия</th>
            </tr>
    """
    
    for apt in apartments:
        html += f"""
            <tr>
                <td>{apt.id}</td>
                <td>{apt.title}</td>
                <td>{apt.district}</td>
                <td>{apt.guests_max}</td>
                <td>{'✅' if apt.is_active else '❌'}</td>
                <td>
                    <a href="/admin/apartments/{apt.id}" style="color: blue;">✏️ Редактировать</a>
                    <a href="/admin/apartments/{apt.id}/delete" style="color: red;">🗑 Удалить</a>
                </td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html


@router.get("/leads", response_class=HTMLResponse)
async def list_leads_admin(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Список лидов"""
    if not check_admin_auth(request):
        return "Unauthorized", 401
    
    result = await session.execute(
        select(Lead).order_by(Lead.created_at.desc()).limit(50)
    )
    leads = result.scalars().all()
    
    html = """
    <html>
    <head>
        <title>Лиды</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background-color: #f2f2f2; }
            .status-new { color: red; }
            .status-in_progress { color: orange; }
            .status-closed { color: green; }
        </style>
    </head>
    <body>
        <h1>📩 Лиды</h1>
        <a href="/admin/dashboard" class="action-btn">⬅️ Назад</a>
        
        <table>
            <tr>
                <th>ID</th>
                <th>Контакт</th>
                <th>Даты</th>
                <th>Гостей</th>
                <th>Статус</th>
                <th>Источник</th>
                <th>Дата</th>
            </tr>
    """
    
    for lead in leads:
        status_class = f"status-{lead.status}"
        html += f"""
            <tr>
                <td>{lead.id}</td>
                <td>{lead.contact}</td>
                <td>{lead.date_from} – {lead.date_to}</td>
                <td>{lead.guests}</td>
                <td class="{status_class}"><strong>{lead.status}</strong></td>
                <td>{lead.source_tag}</td>
                <td>{lead.created_at.strftime('%d.%m.%Y %H:%M')}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html


@router.get("/bookings", response_class=HTMLResponse)
async def list_bookings_admin(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Список бронирований"""
    if not check_admin_auth(request):
        return "Unauthorized", 401
    
    result = await session.execute(
        select(Booking).order_by(Booking.created_at.desc()).limit(50)
    )
    bookings = result.scalars().all()
    
    html = """
    <html>
    <head>
        <title>Брони</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background-color: #f2f2f2; }
            .status-paid { color: green; }
            .status-canceled { color: red; }
        </style>
    </head>
    <body>
        <h1>📅 Брони</h1>
        <a href="/admin/dashboard" class="action-btn">⬅️ Назад</a>
        
        <table>
            <tr>
                <th>ID</th>
                <th>Внешний ID</th>
                <th>Даты</th>
                <th>Сумма</th>
                <th>Статус</th>
                <th>Дата</th>
            </tr>
    """
    
    for booking in bookings:
        status_class = f"status-{booking.status}"
        html += f"""
            <tr>
                <td>{booking.id}</td>
                <td>{booking.external_id}</td>
                <td>{booking.check_in} – {booking.check_out}</td>
                <td>{booking.total_amount or '—'} {booking.currency}</td>
                <td class="{status_class}"><strong>{booking.status}</strong></td>
                <td>{booking.created_at.strftime('%d.%m.%Y %H:%M')}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html