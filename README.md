# FastAPI + Postgres Template

A reusable starting point for FastAPI services backed by PostgreSQL.

- **FastAPI**, served by uvicorn
- **SQLAlchemy 2.0 (async)** with the `asyncpg` driver
- **Alembic** for migrations
- **pydantic-settings** for typed, validated config
- **Poetry** for dependencies
- **Docker Compose** with two modes: full stack (API + Postgres) or API only

## Project layout

```
.
├── main.py                  # Creates the FastAPI app, loads config, runs startup/shutdown
├── app/
│   ├── app_config.py        # Env-var config: `from app.app_config import config`
│   ├── startup.py           # Builds every client & service as importable globals; fails fast if Postgres is down
│   ├── clients/             # Connections to external systems (Postgres, HTTP APIs, ...)
│   │   └── postgres_client.py
│   ├── services/            # Business logic; clients/services injected via constructor
│   │   └── home_service.py  # logic for routers/home.py
│   ├── models/              # SQLAlchemy ORM models
│   │   └── base.py
│   └── routers/             # HTTP routes; any module defining `router` is auto-registered
│       └── home.py          # GET /health
├── alembic/                 # Migration environment + versions/
├── alembic.ini
├── Dockerfile
├── docker-entrypoint.sh     # Starts uvicorn (migrations are a separate step)
├── docker-compose.yml       # Mode 1: Postgres + API
├── docker-compose.api.yml   # Mode 2: API only
├── Makefile                 # Shortcuts for the commands below
├── pyproject.toml / poetry.lock
└── .env.example
```

## Getting started

Prerequisite: Docker (with Docker Compose v2).

```bash
cp .env.example .env
```

### Option 1: Full stack (Postgres + API)

```bash
docker compose up --build        # or: make up
```

This starts a `postgres:16-alpine` container (data persists in the `postgres_data` volume) and the API. The API waits for Postgres to be healthy, and `POSTGRES_HOST`/`POSTGRES_PORT` are overridden to point at the `db` container. Postgres is also exposed on `localhost:5432` (change it with `POSTGRES_HOST_PORT`).

### Option 2: API only

Use this when Postgres already runs somewhere else (on your machine, in the cloud, or in another compose project). Set `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` in `.env`, then run:

```bash
docker compose -f docker-compose.api.yml up --build    # or: make up-api
```

To reach a Postgres server running on your own machine, use `POSTGRES_HOST=host.docker.internal`.

### Check it's running

```bash
curl localhost:8000/health
# {"status":"ok","app":"fastapi-postgres-template","environment":"local","database":"ok"}
```

Interactive API docs: http://localhost:8000/docs

`/health` returns `503` with `"database": "unavailable"` if Postgres goes down while the app is running.

### Stopping

```bash
docker compose down                          # full stack (add -v to wipe the DB volume)
docker compose -f docker-compose.api.yml down
```

## Configuration

All settings live in `.env` and are loaded by `app/app_config.py`. Any module can read them:

```python
from app.app_config import config

config.POSTGRES_HOST
config.DATABASE_URL
```

If a required variable is missing (for example `POSTGRES_HOST`), the app fails at import time with a validation error. To add a setting, add a typed field to `AppConfig` and a matching line to `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `fastapi-postgres-template` | Shown in the API docs and `/health` |
| `ENVIRONMENT` | `local` | Free-form environment label |
| `LOG_LEVEL` | `INFO` | Python log level |
| `API_PORT` | `8000` | Host port mapped to the API |
| `POSTGRES_HOST` / `PORT` / `USER` / `PASSWORD` / `DB` | none (port: 5432) | Database connection |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `10` | SQLAlchemy pool sizing |
| `DB_ECHO` | `false` | Log every SQL statement |
| `DB_CONNECT_RETRIES` / `DB_CONNECT_RETRY_DELAY_SECONDS` | `5` / `2` | Startup connection attempts |
| `RELOAD` | `false` | Hot-reload on code changes (the source is mounted into the container) |

> **Note on `RELOAD`:** with reload on, uvicorn's reloader process keeps the container running even after a failed startup. Leave it `false` when you need a failed startup to stop the container.

## Startup behaviour

Every client and service is a module-level global in `app/startup.py`, built when the module is first imported. Building them does no I/O; the database engine connects lazily. Then, when the app starts, `main.py` calls `startup()`, which:

1. Runs `SELECT 1` against Postgres, retrying `DB_CONNECT_RETRIES` times.
2. If every attempt fails, raises `PostgresConnectionError`. Uvicorn logs the traceback, prints `Application startup failed. Exiting.`, and the container exits with a non-zero code.

On shutdown, `shutdown()` closes the connection pool.

## Changing the database schema

Tables are defined by the SQLAlchemy models in `app/models/` and changed through Alembic migrations in `alembic/versions/`. Migrations do **not** run when the app starts; you apply them yourself.

1. Edit or add a model in `app/models/`. New files are discovered automatically.
2. Generate a migration. Alembic compares the models with the live database and writes the difference:
   ```bash
   make migration m="add users table"
   ```
3. Open the new file in `alembic/versions/` and check it. Autogenerate can't detect everything: a renamed table or column shows up as a drop plus an add (which loses data), and it can't fill in existing rows for a new non-null column. Edit the `upgrade()` and `downgrade()` functions where needed.
4. Apply it:
   ```bash
   make migrate          # alembic upgrade head
   ```
5. Commit the migration file together with the model change.

Other commands:

```bash
make downgrade                                       # undo the last migration
docker compose run --rm api alembic current          # revision the DB is on
docker compose run --rm api alembic history          # all revisions
```

These use `docker compose run`, so they work whether or not the API is running, and they start Postgres if needed. In API-only mode, use `make migrate-api` and `make migration-api m="..."` instead.

When deploying, run `alembic upgrade head` once as its own step (a CI job, a one-off container, or a release task) before starting the new app version. Never run it from every app instance.

## Adding a new API

Each router has a matching service class that holds the logic for its requests (`routers/home.py` → `services/home_service.py`). Routes stay thin and only call services. All wiring happens in `app/startup.py`: a service never creates its own clients or other services; everything it depends on is passed into its constructor there.

Example: a `users` resource backed by Postgres.

1. **Model** in `app/models/user.py`:
   ```python
   from sqlalchemy import String
   from sqlalchemy.orm import Mapped, mapped_column
   from app.models.base import Base, TimestampMixin

   class User(TimestampMixin, Base):
       __tablename__ = "users"
       id: Mapped[int] = mapped_column(primary_key=True)
       email: Mapped[str] = mapped_column(String(255), unique=True)
   ```
   Any module in `app/models/` is picked up automatically, so Alembic sees it without further registration.

2. **Migration** (see [Changing the database schema](#changing-the-database-schema)):
   ```bash
   make migration m="add users table"   # autogenerates into alembic/versions/
   make migrate                         # applies it
   ```

3. **Service** in `app/services/user_service.py`. Its dependencies come in through the constructor:
   ```python
   from sqlalchemy import select
   from app.clients.postgres_client import PostgresClient
   from app.models.user import User

   class UserService:
       def __init__(self, postgres_client: PostgresClient) -> None:
           self.postgres_client = postgres_client

       async def list_users(self) -> list[User]:
           async with self.postgres_client.session() as session:
               return list(await session.scalars(select(User)))

       async def create_user(self, email: str) -> User:
           async with self.postgres_client.session() as session:
               user = User(email=email)
               session.add(user)
               await session.flush()   # fills in user.id; commit happens on block exit
               return user
   ```

4. **Wire it up** with one line in `app/startup.py`, under `# Services`:
   ```python
   user_service = UserService(postgres_client)
   # A service that depends on another service gets it the same way:
   # order_service = OrderService(postgres_client, user_service)
   ```
   It's now importable anywhere: `from app.startup import user_service`.

5. **Router** in `app/routers/users.py`:
   ```python
   from fastapi import APIRouter
   from app.startup import user_service

   router = APIRouter(prefix="/users", tags=["users"])

   @router.get("/")
   async def list_users():
       return await user_service.list_users()
   ```
   That's all: any module in `app/routers/` with a module-level `router` is registered automatically.

`postgres_client.session()` commits when the block finishes and rolls back if it raises.

Services must not import from `app.startup` themselves. They receive what they need through their constructor, which also avoids circular imports. Only routers, and other entry points like scripts, import from `app.startup`.

**New external clients** (Redis, HTTP APIs, etc.) follow the same pattern: add a class under `app/clients/`, create it at the top of `app/startup.py`, and pass it into the constructors of the services that need it. If it needs a connection check, `await` it in `startup()`; if it holds resources, close it in `shutdown()`.

## Dependencies

Packages are managed with Poetry (`pyproject.toml` + `poetry.lock`). After editing dependencies, regenerate the lockfile and rebuild:

```bash
make lock                 # runs `poetry lock` inside a container; no local Poetry needed
docker compose up --build
```

If Poetry is installed locally, `poetry install` and `poetry run uvicorn main:app --reload` also work outside Docker (Python 3.12+).
