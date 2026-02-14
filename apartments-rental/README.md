# 🏠 Квартиры посуточно Краснодар

Production-ready приложение для управления посуточной арендой: Telegram-бот, канал, backend.

## 🚀 Быстрый старт (локально)

### Требования
- Python 3.11+
- PostgreSQL 14+
- Telegram Bot Token (от BotFather)

### 1. Клонируем и устанавливаем зависимости

```bash
git clone <repo-url>
cd apartments-rental
python -m venv venv
source venv/bin/activate  # или `venv\Scripts\activate` на Windows
pip install -r requirements.txt
```

### 2. Настраиваем .env

```bash
cp .env.example .env
# Отредактируй .env с реальными значениями:
# - BOT_TOKEN (от BotFather)
# - ADMIN_TG_IDS, MANAGER_TG_IDS (твои Telegram ID)
# - CHANNEL_ID (@channel или -100...)
# - DATABASE_URL (postgresql://user:pass@localhost:5432/apartments_db)
# - WEBHOOK_SECRET (любая строка)
# - и т.д.
```

### 3. Создаем БД и миграции

```bash
# Создаем БД вручную (или через psql):
# createdb apartments_db

# Применяем миграции Alembic:
alembic upgrade head
```

### 4. Запускаем локально

```bash
python app/main.py
```

Приложение слушает http://localhost:8000

**Проверяем:**
- Health check: http://localhost:8000/health
- Админ-панель: http://localhost:8000/admin (логин/пароль из .env)

---

## 📦 Деплой на Deploy-F

Deploy-F.com позволяет загружать zip-архив и получить https-домен за минуты.

### 1. Подготавливаем архив

```bash
# Копируем только нужные файлы в папку для архива
mkdir -p deploy-package
cp -r app/ deploy-package/
cp requirements.txt deploy-package/
cp .env.example deploy-package/.env
cp alembic.ini deploy-package/
cp -r app/db/migrations deploy-package/

# Создаем zip
cd deploy-package
zip -r ../apartments-rental.zip . -x "*.pyc" "__pycache__/*" ".git/*"
cd ..
```

### 2. Загружаем на Deploy-F

1. Перейди на https://deploy-f.com
2. Нажми "Загрузить проект"
3. Выбери `apartments-rental.zip`
4. **Очень важно:**
   - **Port:** 8000
   - **Start command:** `python app/main.py` или `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - **Python version:** 3.11+

### 3. Настраиваем переменные окружения на Deploy-F

После загрузки, в панели настроек добавь все переменные из `.env`:

```
BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
ADMIN_TG_IDS=111111,222222
MANAGER_TG_IDS=111111
CHANNEL_ID=-1001234567890
BASE_PUBLIC_URL=https://myapp.deploy-f.com  (или полученный домен)
TG_WEBHOOK_PATH=/tg/webhook/secret_suffix_12345
BOOKING_BASE_URL=https://homereserve.ru/bJOig2XsQu
WEBHOOK_SECRET=your_secret_here_change_me
ADMIN_PANEL_USER=admin
ADMIN_PANEL_PASS=password123
DATABASE_URL=postgresql+asyncpg://user:pass@deploy-f-db:5432/apartments_db
ATTRIBUTION_WINDOW_DAYS=30
REF_PAYOUT_MODE=fixed
REF_PAYOUT_FIXED=500
REF_PAYOUT_PERCENT=5
TIMEZONE=Europe/Moscow
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
```

### 4. Инициализируем БД на Deploy-F

Deploy-F предоставляет PostgreSQL. После развертывания:

```bash
# Подключись к БД через SSH или консоль Deploy-F
# Затем примени миграции:
alembic upgrade head
```

### 5. Устанавливаем Telegram webhook

Когда приложение развернуто и доступно по https://myapp.deploy-f.com:

```bash
# Вызови этот URL в браузере или через curl:
# (Бот автоматически установит webhook при старте)

curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://myapp.deploy-f.com/tg/webhook/secret_suffix_12345"}'
```

Или просто запусти приложение — бот сам установит webhook при старте в `@app.on_event("startup")`.

### 6. Добавляем бота админом в канал

1. Перейди в свой Telegram канал
2. Нажми "Управление" → "Администраторы"
3. Добавь твоего бота (@your_bot)
4. Выдай ему права: "Удалять сообщения", "Закреплять сообщения", "Редактировать сообщения"

---

## 🗂️ Структура проекта

```
apartments-rental/
├── app/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Конфигурация из .env
│   ├── logger.py                # Структурированное логирование
│   ├── bot/
│   │   ├── main.py              # Инициализация Aiogram
│   │   ├── router_user.py       # User-сценарии (wizard, FAQ, etc)
│   │   ├── router_admin.py      # Admin-команды
│   │   ├── states.py            # FSM состояния
│   │   ├── texts.py             # Все текстовые строки
│   │   ├── keyboards.py         # ReplyKeyboard и InlineKeyboard
│   │   └── utils.py             # build_booking_url, parse_dates, etc
│   ├── api/
│   │   ├── routes_webhooks.py   # POST /webhooks/booking
│   │   └── admin_panel.py       # Веб-админ-панель
│   ├── db/
│   │   ├── session.py           # AsyncSession, engine
│   │   ├── models.py            # SQLAlchemy модели
│   │   ├── crud.py              # CRUD операции
│   │   └── migrations/          # Alembic миграции
│   └── services/
│       ├── webhook_parser.py    # Парсер вебхуков (конфигурируемый)
│       ├── attribution.py       # Атрибуция бронирований
│       ├── referrals.py         # Реферальная программа
│       └── publishing.py        # Публикация в канал
├── tests/
│   ├── test_utils.py
│   └── test_webhook_parser.py
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

---

## 🔧 Команды для разработки

### Запуск бота локально
```bash
python app/main.py
```

### Применить миграции
```bash
alembic upgrade head
```

### Создать новую миграцию
```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Запустить тесты
```bash
pytest tests/ -v
```

### Проверить код
```bash
flake8 app/ tests/
black app/ tests/  # Форматирование
```

---

## 📱 Использование бота

### Пользователь
1. `/start` — главное меню
2. `🏠 Подобрать квартиру` — wizard с пошаговым подбором
3. `📚 Каталог` — каталог по категориям
4. `🎁 Скидка / Рефералка` — реферальная программа

### Администратор
1. `/admin` — админ-меню
2. `📢 Публикация` — ��публиковать меню/каталог/квартиры в канал
3. `📊 Статистика` — конверсия, топ-квартиры, доход

---

## 🪝 Webhook для бронирований

### Endpoint
```
POST https://myapp.deploy-f.com/webhooks/booking
Header: X-Webhook-Secret: your_secret_here_change_me
```

### Payload (пример HomeReserve)
```json
{
  "booking_id": "BK-12345",
  "status": "paid",
  "apartment_id": 42,
  "check_in_date": "2024-02-15",
  "check_out_date": "2024-02-17",
  "price": 5000,
  "currency": "RUB",
  "guest_phone": "+79001234567",
  "source_tag": "tg_bot"
}
```

### Ответ
```json
{
  "ok": true,
  "booking_id": 123,
  "payout_created": true
}
```

---

## 💰 Реферальная программа

### Как работает
1. Каждый пользователь получает уникальный код при первом `/start`
2. Приглашает друзей по ссылке: `https://t.me/bot?start=r_ABC123`
3. Если друг забронирует в течение 30 дней — реферер получает бонус:
   - **Fixed mode:** 500₽ за каждую оплаченную бронь
   - **Percent mode:** 5% от суммы

### Конфигурация
В `.env`:
```
REF_PAYOUT_MODE=fixed        # или percent
REF_PAYOUT_FIXED=500         # если fixed
REF_PAYOUT_PERCENT=5         # если percent
ATTRIBUTION_WINDOW_DAYS=30   # окно для атрибуции
```

---

## 🔐 Безопасность

- **BasicAuth для админ-панели:** логин/пароль в `.env`
- **Webhook Secret:** обязательно измени в `.env`
- **Telegram Token:** никогда не коммитай .env, используй .env.example
- **Database:** используй надежный пароль для PostgreSQL

---

## 📞 Поддержка и вопросы

Если что-то не работает:
1. Проверь логи: `tail -f logs/app.log` (если логирование в файл)
2. Убедись, что все переменные в `.env` заполнены
3. Проверь подключение к БД: `psql postgresql://user:pass@host/db`
4. Проверь webhook на Telegram: API должен вернуть `ok: true`

---

## 📄 Лицензия

MIT

---

**Версия:** 0.1.0  
**Обновлено:** 2024-02-14