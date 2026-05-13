from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    return client


def get_db():
    return client[settings.DATABASE_NAME]


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Verify connection
    await client.admin.command("ping")


async def close_db():
    global client
    if client:
        client.close()
