from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import connect_db, close_db
from app.routers.auth_router import router as auth_router
from app.routers.student_router import router as student_router
from app.routers.monitor_router import router as monitor_router, increment_request_count
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Connecting to MongoDB...")
    try:
        await connect_db()
        logger.info("MongoDB connected ✓")

        # Ensure DB indexes
        from app.core.database import get_db
        db = get_db()
        await db["users"].create_index("username", unique=True)
        await db["students"].create_index("email", unique=True)
        await db["students"].create_index("user_id")
        logger.info("DB indexes ensured ✓")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")

    yield

    # Shutdown
    await close_db()
    logger.info("MongoDB disconnected")


app = FastAPI(
    title="Student Management API",
    description="Full-stack student management system with JWT auth, MongoDB, and Redis caching",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.perf_counter()
    increment_request_count()
    try:
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"time={duration:.4f}s"
        )
        return response
    except Exception as exc:
        duration = time.perf_counter() - start
        logger.error(
            f"{request.method} {request.url.path} "
            f"error={exc} time={duration:.4f}s"
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", tags=["Root"])
def root():
    return {"message": "Student Management API is running", "docs": "/docs"}


app.include_router(auth_router)
app.include_router(student_router)
app.include_router(monitor_router)
