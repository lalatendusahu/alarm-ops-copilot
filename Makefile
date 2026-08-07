.PHONY: setup seed ingest test lint up down logs build coverage

setup:
	python -m venv .venv
	. .venv/bin/activate; pip install -r requirements.txt

seed:
	python scripts/seed_alarm_db.py
	python scripts/seed_work_order_db.py

ingest:
	python rag/ingestion/ingest.py

test:
	cd alarm-simulator && python -m pytest tests/ -q
	cd work-order-service && python -m pytest tests/ -q
	python -m pytest tests/ rag/tests/ -q

coverage:
	cd alarm-simulator && python -m pytest tests/ --cov=app --cov-report=term-missing -q
	cd work-order-service && python -m pytest tests/ --cov=app --cov-report=term-missing -q
	python -m pytest tests/ rag/tests/ --cov=apps --cov=connectors --cov=rag --cov-report=term-missing --cov-report=html -q

lint:
	python -m ruff check alarm-simulator work-order-service connectors mcp-servers apps rag scripts tests

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f
