BACKEND := backend
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
FRONTEND_PORT ?= 5500
API_URL ?= http://$(API_HOST):$(API_PORT)
API_IMAGE ?= patchpoint-api:local
PROXY_IMAGE ?= patchpoint-proxy:local
IMAGE_SOURCE := https://github.com/l3x1cn/patchpoint
IMAGE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)

.PHONY: install run test lint format typecheck frontend demo security-check images dev-cert

install:
	cd $(BACKEND) && uv sync

run:
	cd $(BACKEND) && uv run uvicorn app.main:app --host $(API_HOST) --port $(API_PORT) --no-proxy-headers

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

images:
	docker build --label org.opencontainers.image.source=$(IMAGE_SOURCE) --label org.opencontainers.image.revision=$(IMAGE_REVISION) --label org.opencontainers.image.title=patchpoint-api -t $(API_IMAGE) $(BACKEND)
	docker build --label org.opencontainers.image.source=$(IMAGE_SOURCE) --label org.opencontainers.image.revision=$(IMAGE_REVISION) --label org.opencontainers.image.title=patchpoint-proxy -f deploy/proxy/Dockerfile -t $(PROXY_IMAGE) .

dev-cert:
	./scripts/dev_cert.sh deploy/proxy/dev-tls
