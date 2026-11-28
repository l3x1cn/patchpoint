BACKEND := backend
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
FRONTEND_PORT ?= 5500
API_URL ?= http://$(API_HOST):$(API_PORT)
API_IMAGE ?= patchpoint-api:local
PROXY_IMAGE ?= patchpoint-proxy:local
IMAGE_SOURCE := https://github.com/l3x1cn/patchpoint
IMAGE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
ANSIBLE_DIR := deploy/ansible
ANSIBLE_PYTHON ?= 3.13
# Wersje ansible-core i ansible-lint: deploy/ansible/tools/pyproject.toml, zależności pośrednie: uv.lock.
# Ścieżka --project jest względna wobec katalogu deploy/ansible, z którego działają polecenia celu.
UV_ANSIBLE := uv run --locked --python $(ANSIBLE_PYTHON) --project tools

.PHONY: install run test lint format typecheck frontend demo security-check images dev-cert semgrep trivy-fs trivy-images shellcheck actionlint scan stack-up stack-down stack-smoke ansible-lint

install:
	cd $(BACKEND) && uv sync

run:
	cd $(BACKEND) && uv run uvicorn app.main:app --host $(API_HOST) --port $(API_PORT) --workers 1 --no-proxy-headers

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

semgrep:
	./scripts/scan.sh semgrep

trivy-fs:
	./scripts/scan.sh fs

trivy-images:
	./scripts/scan.sh image api $(API_IMAGE)
	./scripts/scan.sh image proxy $(PROXY_IMAGE)

shellcheck:
	./scripts/scan.sh shellcheck

actionlint:
	./scripts/scan.sh actionlint

scan: semgrep trivy-fs shellcheck actionlint images trivy-images

stack-up: dev-cert images
	PATCHPOINT_API_IMAGE=$(API_IMAGE) PATCHPOINT_PROXY_IMAGE=$(PROXY_IMAGE) docker compose up -d --wait

stack-down:
	docker compose down

stack-smoke:
	PATCHPOINT_API_IMAGE=$(API_IMAGE) PATCHPOINT_PROXY_IMAGE=$(PROXY_IMAGE) ./scripts/stack_smoke.sh

ansible-lint:
	cd $(ANSIBLE_DIR) && $(UV_ANSIBLE) ansible-lint
	cd $(ANSIBLE_DIR) && $(UV_ANSIBLE) ansible-galaxy collection install -r requirements.yml -p .ansible/collections
	cd $(ANSIBLE_DIR) && ANSIBLE_COLLECTIONS_PATH=.ansible/collections $(UV_ANSIBLE) ansible-playbook --syntax-check -i inventory.example.yml site.yml
