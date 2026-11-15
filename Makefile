BACKEND := backend
API_HOST ?= 127.0.0.1
API_PORT ?= 8000

.PHONY: install run test lint format typecheck

install:
	cd $(BACKEND) && uv sync

run:
	cd $(BACKEND) && uv run uvicorn app.main:app --host $(API_HOST) --port $(API_PORT)

test:
	cd $(BACKEND) && uv run pytest

lint:
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

format:
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

typecheck:
	cd $(BACKEND) && uv run mypy app tests
