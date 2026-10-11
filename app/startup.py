"""Composition root: every client and service is created and wired here.

- Services never create their own clients or other services. Whatever they
  depend on is passed into their constructor here.
- Create clients first, then services in dependency order.
- Anything defined at module level here can be used anywhere in the app:

      from app.startup import user_service

Objects are built when this module is imported. Creating them does no I/O;
`startup()` then verifies connections before the app accepts requests.
"""

import logging

from app.clients.postgres_client import PostgresClient
from app.services.home_service import HomeService

logger = logging.getLogger(__name__)

# Clients
postgres_client = PostgresClient()

# Services (dependencies injected via constructor)
home_service = HomeService(postgres_client)
# user_service = UserService(postgres_client)
# order_service = OrderService(postgres_client, user_service)


async def startup() -> None:
    try:
        await postgres_client.connect()
    except Exception:
        logger.critical("Startup aborted")
        await shutdown()
        raise
    logger.info("Startup complete")


async def shutdown() -> None:
    await postgres_client.close()
    logger.info("Shutdown complete")
