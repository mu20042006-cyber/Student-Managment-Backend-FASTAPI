from fastapi import APIRouter
from app.core.redis_client import redis_client
import os

router = APIRouter(prefix="/monitor", tags=["Monitoring"])

# Use a module-level counter; for multi-worker deployments use Redis
_request_count = 0


def increment_request_count():
    global _request_count
    _request_count += 1
    if redis_client:
        try:
            redis_client.incr("monitor:request_count")
        except Exception:
            pass


def get_request_count() -> int:
    if redis_client:
        try:
            val = redis_client.get("monitor:request_count")
            return int(val) if val else _request_count
        except Exception:
            pass
    return _request_count


@router.get("/health")
def health():
    return {"status": "ok", "service": "Student Management API"}


@router.get("/stats")
def stats():
    redis_status = "unavailable"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "error"

    return {
        "request_count": get_request_count(),
        "redis": redis_status,
    }


@router.get("/logs")
def get_logs():
    log_file = "app.log"
    if not os.path.exists(log_file):
        return {"logs": []}
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()[-50:]
    return {"logs": [line.rstrip() for line in lines]}
