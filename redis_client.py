import redis
from app.core.config import settings

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=2,
    )
    redis_client.ping()
except Exception:
    redis_client = None  # Redis is optional; app still works without it
