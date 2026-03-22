.PHONY: test lint smoke deploy build run stop logs

# ── Local development ─────────────────────────────────────────
lint:
	uv run ruff check src/ tests/

test: lint
	uv run pytest tests/ -x -q

smoke:
	uv run pytest tests/test_smoke.py -x -q

# ── Build & deploy (run on the server after git pull) ─────────
build:
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose build

deploy: test build
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose up -d
	@echo "Deployed $$(git rev-parse --short HEAD)"

# ── Docker helpers ────────────────────────────────────────────
run:
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f forma
