"""
Асинхронная сессия SQLAlchemy с пулом подключений.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from app.config import get_settings
import logging

log = logging.getLogger("db")
settings = get_settings()

# Создаём асинхронный движок
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    poolclass=NullPool,
)

# Фабрика сессий
SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    """Dependency для FastAPI"""
    async with SessionLocal() as session:
        yield session


async def init_db():
    """Инициализация БД и добавление тестовых данных"""
    from app.db.models import Base, User, Apartment, ApartmentTag, ApartmentMedia
    from app.logger import log_api
    
    try:
        # Создаём таблицы (если они ещё не существуют)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        log_api.info("✅ Таблицы БД созданы/обновлены")
        
        # Добавляем тестовые данные, если БД пуста
        async with SessionLocal() as session:
            # Проверяем, есть ли уже данные
            from sqlalchemy import select, func
            
            count = await session.execute(select(func.count(Apartment.id)))
            apartment_count = count.scalar() or 0
            
            if apartment_count == 0:
                log_api.info("📝 Добавляем тестовые квартиры...")
                
                # Создаём тестовые квартиры
                test_apartments = [
                    Apartment(
                        title="Квартира в центре",
                        district="Центр",
                        address_short="ул. Красная, 1",
                        guests_max=4,
                        beds_text="2 спальни, 1 гостиная",
                        features_json=["WiFi", "Кондиционер", "Кухня", "Балкон"],
                        rules_short="Без животных, без курения",
                        map_url="https://maps.google.com",
                        is_active=True,
                        sort_order=1,
                    ),
                    Apartment(
                        title="Апартаменты у парка",
                        district="Парк",
                        address_short="парк Галицкий",
                        guests_max=2,
                        beds_text="1 спальня",
                        features_json=["WiFi", "Парковка", "Уютно", "Вид на парк"],
                        rules_short="Тихие соседи приветствуются",
                        map_url="https://maps.google.com",
                        is_active=True,
                        sort_order=2,
                    ),
                    Apartment(
                        title="Бизнес апартаменты",
                        district="Бизнес центр",
                        address_short="ул. Офицерская, 45",
                        guests_max=3,
                        beds_text="1 спальня + кабинет",
                        features_json=["WiFi", "Рабочий стол", "Микроволновка", "Холодильник"],
                        rules_short="Идеально для командировок",
                        map_url="https://maps.google.com",
                        is_active=True,
                        sort_order=3,
                    ),
                ]
                
                session.add_all(test_apartments)
                await session.commit()
                
                # Добавляем теги
                await session.refresh(test_apartments[0])
                await session.refresh(test_apartments[1])
                await session.refresh(test_apartments[2])
                
                tags = [
                    ApartmentTag(apartment_id=test_apartments[0].id, tag="center"),
                    ApartmentTag(apartment_id=test_apartments[0].id, tag="business"),
                    ApartmentTag(apartment_id=test_apartments[1].id, tag="park"),
                    ApartmentTag(apartment_id=test_apartments[1].id, tag="family"),
                    ApartmentTag(apartment_id=test_apartments[2].id, tag="business"),
                ]
                
                session.add_all(tags)
                await session.commit()
                
                log_api.info(f"✅ Добавлено {len(test_apartments)} тестовых квартир")
            else:
                log_api.info(f"✅ В БД уже есть {apartment_count} квартир")
    
    except Exception as e:
        log_api.error(f"❌ Ошибка инициализации БД: {e}")
        raise