.PHONY: dev dev-api dev-web install lint test compose-up compose-down

install:
	uv sync --project apps/api --all-groups
	npm install

dev:
	docker compose up --build

dev-api:
	uv run --project apps/api uvicorn tracewell_api.main:app --reload --port 8000

dev-web:
	npm run dev:web

lint:
	uv run --project apps/api ruff check apps/api
	uv run --project apps/api ruff format --check apps/api
	npm run lint:web
	npm run typecheck:web

test:
	uv run --project apps/api pytest apps/api/tests
	npm run test:web

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

