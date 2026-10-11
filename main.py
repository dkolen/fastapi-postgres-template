import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.app_config import config
from app.routers import api_router
from app.startup import shutdown, startup

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(title=config.APP_NAME, lifespan=lifespan)
app.include_router(api_router)
