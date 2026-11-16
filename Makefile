BACKEND := backend
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
FRONTEND_PORT ?= 5500
API_URL ?= http://$(API_HOST):$(API_PORT)

.PHONY: install run test lint format typecheck frontend demo security-check

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

frontend:
	python3 -m http.server $(FRONTEND_PORT) --bind 127.0.0.1 --directory frontend

demo:
	API_URL=$(API_URL) ./scripts/demo.sh

security-check:
	API_URL=$(API_URL) ./scripts/security_check.sh
