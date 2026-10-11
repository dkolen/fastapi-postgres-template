from app.app_config import config
from app.clients.postgres_client import PostgresClient


class HomeService:
    def __init__(self, postgres_client: PostgresClient) -> None:
        self.postgres_client = postgres_client

    async def healthcheck(self) -> dict:
        try:
            await self.postgres_client.ping()
            database = "ok"
        except Exception:
            database = "unavailable"

        return {
            "status": "ok" if database == "ok" else "degraded",
            "app": config.APP_NAME,
            "environment": config.ENVIRONMENT,
            "database": database,
        }
