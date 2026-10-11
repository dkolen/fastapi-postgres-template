import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.app_config import config

logger = logging.getLogger(__name__)


class PostgresConnectionError(RuntimeError):
    pass


class PostgresClient:
    """Owns the async SQLAlchemy engine and session factory."""

    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(
            config.DATABASE_URL,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=config.DB_ECHO,
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def connect(self) -> None:
        """Verify the database is reachable. Raises PostgresConnectionError if not."""
        attempts = max(1, config.DB_CONNECT_RETRIES)
        for attempt in range(1, attempts + 1):
            try:
                await self.ping()
                logger.info(
                    "Connected to Postgres at %s:%s/%s",
                    config.POSTGRES_HOST,
                    config.POSTGRES_PORT,
                    config.POSTGRES_DB,
                )
                return
            except Exception as exc:
                logger.warning("Postgres connection attempt %d/%d failed: %s", attempt, attempts, exc)
                if attempt == attempts:
                    raise PostgresConnectionError(
                        f"Could not connect to Postgres at {config.POSTGRES_HOST}:{config.POSTGRES_PORT} "
                        f"after {attempts} attempts"
                    ) from exc
                await asyncio.sleep(config.DB_CONNECT_RETRY_DELAY_SECONDS)

    async def ping(self) -> None:
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session that commits on success and rolls back on error."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        await self.engine.dispose()
        logger.info("Postgres connection pool closed")
