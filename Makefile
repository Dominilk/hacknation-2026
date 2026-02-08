.PHONY: run dev backend frontend enron-ingest enron-dry-run sync check up down build logs kill

# ── Development ──

# Single command: kill stale processes, install deps, start everything
run:
	@-lsof -ti :8002,:5174 2>/dev/null | xargs -r kill -9
	@cd frontend && npm install --silent 2>/dev/null
	@echo ""
	@echo "  Starting AI Chief of Staff..."
	@echo "  Frontend: http://localhost:5174"
	@echo ""
	@$(MAKE) -j2 backend frontend

dev:
	$(MAKE) -j2 backend frontend

backend:
	uv run uvicorn core.server:app --host 0.0.0.0 --port 8002 --reload

frontend:
	cd frontend && npx vite --port 5174

kill:
	-lsof -ti :8000,:8001,:8002,:5174 | xargs -r kill -9

# ── Docker ──

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ── Enron ingestion (default: 20 emails) ──

enron-ingest:
	uv run enron-ingest --url http://localhost:8002/ingest --limit $(or $(LIMIT),20)

enron-dry-run:
	uv run enron-ingest --dry-run --limit $(or $(LIMIT),20)

# ── Utilities ──

sync:
	uv sync --all-extras

check:
	uvx ty@latest check
