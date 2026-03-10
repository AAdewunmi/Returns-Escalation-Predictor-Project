SHELL := /bin/bash

DC := docker compose
WEB := $(DC) exec web
PY := $(WEB) python

.PHONY: help bootstrap up down restart logs ps shell migrate makemigrations \
	test test-cov lint format format-check check

help:
	@echo "Available targets:"
	@echo "  make bootstrap     # Copy env file, build/start services, run migrations"
	@echo "  make up            # Start services in detached mode"
	@echo "  make down          # Stop services"
	@echo "  make restart       # Restart services"
	@echo "  make logs          # Tail service logs"
	@echo "  make ps            # Show service status"
	@echo "  make shell         # Open Django shell in web container"
	@echo "  make migrate       # Apply migrations"
	@echo "  make makemigrations# Create migrations"
	@echo "  make test          # Run pytest"
	@echo "  make test-cov      # Run pytest with coverage gate"
	@echo "  make lint          # Run ruff"
	@echo "  make format        # Run black formatter"
	@echo "  make format-check  # Check black formatting"
	@echo "  make check         # Run format-check + lint + test"

bootstrap:
	@test -f .env || cp .env.example .env
	$(DC) up --build -d
	$(PY) manage.py migrate

up:
	$(DC) up --build -d

down:
	$(DC) down

restart:
	$(DC) restart

logs:
	$(DC) logs -f

ps:
	$(DC) ps

shell:
	$(PY) manage.py shell

migrate:
	$(PY) manage.py migrate

makemigrations:
	$(PY) manage.py makemigrations

test:
	$(WEB) pytest -q

test-cov:
	$(WEB) pytest -q --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=85

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m black .

format-check:
	$(PY) -m black . --check

check: format-check lint test
