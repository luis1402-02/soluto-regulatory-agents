.PHONY: help install dev test lint format clean run serve docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  install      Install dependencies"
	@echo "  dev          Install dev dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linters"
	@echo "  format       Format code"
	@echo "  clean        Clean cache files"
	@echo "  run          Run CLI"
	@echo "  serve        Start API server"
	@echo "  docker-build Build Docker image"
	@echo "  docker-up    Start services with Docker Compose"
	@echo "  docker-down  Stop Docker Compose services"

install:
	poetry install

dev:
	poetry install --with dev

test:
	poetry run pytest -v

test-cov:
	poetry run pytest --cov=src --cov-report=html --cov-report=term

lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist

run:
	poetry run python main.py $(ARGS)

serve:
	poetry run python main.py serve

interactive:
	poetry run python main.py interactive

docker-build:
	docker build -t soluto-agents:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

setup-pre-commit:
	poetry run pre-commit install

migrate:
	poetry run alembic upgrade head

redis-cli:
	docker-compose exec redis redis-cli

psql:
	docker-compose exec postgres psql -U soluto soluto_agents