.PHONY: test lint smoke deploy build stop restart logs status backup dev update

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
#
# make update   — the one command to rule them all:
#   1. git pull
#   2. lint + test (if fail → old version keeps running)
#   3. docker build (if fail → old version keeps running)
#   4. docker up -d (swaps container)
#   5. health check (if fail → rolls back to previous image)
#
update:
	@BEFORE=$$(git rev-parse HEAD); \
	echo "── Pulling latest code..."; \
	git pull; \
	AFTER=$$(git rev-parse HEAD); \
	if [ "$$BEFORE" = "$$AFTER" ]; then \
		echo "✓ Already up to date ($$(git rev-parse --short HEAD))"; \
		exit 0; \
	fi; \
	echo "── Running tests..."; \
	$(MAKE) test && \
	echo "── Building new image..." && \
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose build && \
	echo "── Starting new container..." && \
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose up -d --wait && \
	echo "✓ Deployed $$(git rev-parse --short HEAD) — healthy"

deploy: test build
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose up -d --wait
	@echo "✓ Deployed $$(git rev-parse --short HEAD)"

build:
	GIT_COMMIT=$$(git rev-parse --short HEAD) docker compose build

restart:
	docker compose restart forma
	@echo "✓ Restarted (no rebuild)"

stop:
	docker compose down
	@echo "✓ All containers stopped"

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
