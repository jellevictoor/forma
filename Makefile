.PHONY: test lint smoke deploy build run stop restart logs status backup dev

# ── Local development ─────────────────────────────────────────
lint:
	uv run ruff check src/ tests/

test: lint
	uv run pytest tests/ -x -q

smoke:
	uv run pytest tests/test_smoke.py -x -q

dev:
	@echo "Starting local dev server against Docker postgres..."
	DEV_ATHLETE_ID=$$(psql postgresql://forma:forma@localhost:5433/forma -t -A -c "SELECT id FROM athletes LIMIT 1") \
	DATABASE_URL=postgresql://forma:forma@localhost:5433/forma \
	uv run uvicorn forma.adapters.web.app:create_app --factory --port 8080 --reload

# ── Production lifecycle ──────────────────────────────────────
deploy: test build
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose up -d
	@echo "✓ Deployed $$(git rev-parse --short HEAD)"

build:
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose build

restart:
	docker compose restart forma
	@echo "✓ Restarted (no rebuild)"

stop:
	docker compose down
	@echo "✓ All containers stopped"

update:
	git pull
	$(MAKE) deploy

# ── Operations ────────────────────────────────────────────────
logs:
	docker compose logs -f forma

status:
	@docker compose ps
	@echo ""
	@echo "Commit: $$(docker exec forma printenv GIT_COMMIT 2>/dev/null || echo 'unknown')"

backup:
	docker exec forma_postgres pg_dump -Fc -U forma forma > backups/forma_$$(date +%Y%m%d_%H%M%S).dump
	@echo "✓ Backup saved to backups/"
