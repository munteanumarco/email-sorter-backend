.PHONY: build run stop clean clean-all migrate migrate-down logs test help

# Variables
DC=docker-compose

help:
	@echo "Available commands:"
	@echo "  make build      - Build all containers"
	@echo "  make run        - Start all containers and apply migrations"
	@echo "  make stop       - Stop all containers (preserves data)"
	@echo "  make clean      - Stop containers (preserves data)"
	@echo "  make clean-all  - Stop containers and remove all data (DANGEROUS!)"
	@echo "  make migrate    - Apply database migrations"
	@echo "  make migrate-down - Rollback last migration"
	@echo "  make logs       - Show logs from all containers"
	@echo "  make test       - Run tests"

build:
	$(DC) build --no-cache

migrate:
	$(DC) exec api alembic upgrade head

migrate-down:
	$(DC) exec api alembic downgrade -1

# New safer run that doesn't clean data
run: build
	$(DC) up -d
	@echo "Waiting for database to be ready..."
	@sleep 5
	@make migrate
	@echo "Application is running!"
	@echo "API is available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"
	@make logs

stop:
	$(DC) stop

# Safe clean that preserves volumes
clean:
	$(DC) down

# Dangerous clean that removes all data
clean-all:
	$(DC) down -v

logs:
	$(DC) logs -f

test:
	$(DC) exec api pytest

# Default target
.DEFAULT_GOAL := help