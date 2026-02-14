.PHONY: help install migrate run test lint format clean deploy

help:
	@echo "Доступные команды:"
	@echo "  make install     - установить зависимости"
	@echo "  make migrate     - применить миграции"
	@echo "  make run         - запустить приложение локально"
	@echo "  make test        - запустить тесты"
	@echo "  make lint        - проверить код (flake8)"
	@echo "  make format      - форматировать код (black)"
	@echo "  make clean       - удалить .pyc и __pycache__"
	@echo "  make deploy      - создать zip для Deploy-F"

install:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

migrate:
	alembic upgrade head

run:
	python app/main.py

test:
	pytest tests/ -v --tb=short

lint:
	flake8 app/ tests/ --max-line-length=120

format:
	black app/ tests/ --line-length=120

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

deploy:
	@echo "Создание архива для Deploy-F..."
	mkdir -p deploy-package
	cp -r app/ deploy-package/
	cp requirements.txt deploy-package/
	cp .env.example deploy-package/.env
	cp alembic.ini deploy-package/
	cp -r app/db/migrations deploy-package/
	cd deploy-package && zip -r ../apartments-rental.zip . -x "*.pyc" "__pycache__/*" ".git/*" && cd ..
	@echo "✅ Архив создан: apartments-rental.zip"
	@echo "📤 Загрузи на https://deploy-f.com"