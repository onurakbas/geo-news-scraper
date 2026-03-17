"""
Async MongoDB client lifecycle helpers.
Call connect_db() on startup and disconnect_db() on shutdown.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    # Lightweight ping to fail fast on bad credentials / unreachable host
    await _client.admin.command("ping")


async def disconnect_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the application database; raises if connect_db() wasn't called."""
    if _client is None:
        raise RuntimeError("Database client is not initialised. Call connect_db() first.")
    return _client[settings.MONGODB_DB_NAME]
