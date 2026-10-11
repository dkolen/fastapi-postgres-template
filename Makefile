.PHONY: up up-api down down-api logs migrate migration downgrade migrate-api migration-api lock

up:           ## Start Postgres + API
	docker compose up --build

up-api:       ## Start API only (uses POSTGRES_* from .env)
	docker compose -f docker-compose.api.yml up --build

down:
	docker compose down

down-api:
	docker compose -f docker-compose.api.yml down

logs:
	docker compose logs -f api

migrate:      ## Apply pending migrations (starts Postgres if needed)
	docker compose run --rm api alembic upgrade head

migration:    ## Create a migration: make migration m="add items table"
	docker compose run --rm api alembic revision --autogenerate -m "$(m)"

downgrade:    ## Roll back the most recent migration
	docker compose run --rm api alembic downgrade -1

migrate-api:  ## Apply migrations to the external Postgres from .env
	docker compose -f docker-compose.api.yml run --rm api alembic upgrade head

migration-api: ## Create a migration against the external Postgres from .env
	docker compose -f docker-compose.api.yml run --rm api alembic revision --autogenerate -m "$(m)"

lock:         ## Regenerate poetry.lock without a local Poetry install
	docker run --rm -v "$(PWD)":/app -w /app python:3.12-slim \
		sh -c "pip install -q poetry==2.1.3 && poetry lock"
