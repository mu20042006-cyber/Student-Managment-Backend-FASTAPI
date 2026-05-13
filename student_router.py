from fastapi import APIRouter, HTTPException, Depends, Query, status
import json
import secrets
from bson import ObjectId
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.core.auth_dependencies import get_current_user, require_admin
from app.core.auth_handler import hash_password
from app.schemas.student_schema import StudentCreate, StudentUpdate, StudentOut, StudentListResponse
from app.models.models import student_from_doc, to_object_id
from app.services.gpa_service import calculate_gpa
from app.utils.logger import logger
from redis.exceptions import ConnectionError as RedisConnectionError

router = APIRouter(prefix="/students", tags=["Students"])

CACHE_TTL = 60  # seconds


def _try_cache_get(key: str):
    if redis_client is None:
        return None
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except (RedisConnectionError, Exception):
        return None


def _try_cache_set(key: str, value, ttl: int = CACHE_TTL):
    if redis_client is None:
        return
    try:
        redis_client.set(key, json.dumps(value), ex=ttl)
    except (RedisConnectionError, Exception):
        pass


def _try_cache_delete(*keys: str):
    """Delete exact keys or glob patterns (e.g. 'students:*') from Redis.

    Redis DEL does not accept wildcards, so pattern keys are expanded with
    SCAN before deletion.
    """
    if redis_client is None:
        return
    try:
        exact, patterns = [], []
        for k in keys:
            (patterns if "*" in k or "?" in k or "[" in k else exact).append(k)

        if exact:
            redis_client.delete(*exact)

        for pattern in patterns:
            cursor = 0
            while True:
                cursor, matched = redis_client.scan(cursor, match=pattern, count=100)
                if matched:
                    redis_client.delete(*matched)
                if cursor == 0:
                    break
    except (RedisConnectionError, Exception):
        pass


# ────────────────────────────────────────────────
# IMPORTANT: /me MUST come before /{student_id}
# Otherwise FastAPI treats "me" as an integer → 422
# ────────────────────────────────────────────────

@router.get("/me", response_model=StudentOut)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = to_object_id(current_user["id"])
    student = await db["students"].find_one({"user_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student_from_doc(student)


@router.get("/", response_model=StudentListResponse)
async def list_students(
    department: str | None = Query(None),
    min_gpa: float | None = Query(None, ge=0, le=4),
    search: str | None = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    cache_key = f"students:dept={department}:gpa={min_gpa}:q={search}:p={page}:ps={page_size}"
    cached = _try_cache_get(cache_key)
    if cached:
        return cached

    db = get_db()
    query: dict = {}

    if department:
        query["department"] = {"$regex": department, "$options": "i"}
    if min_gpa is not None:
        query["gpa"] = {"$gte": min_gpa}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = await db["students"].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db["students"].find(query).skip(skip).limit(page_size)

    students = [student_from_doc(doc) async for doc in cursor]

    result = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "students": students,
    }
    _try_cache_set(cache_key, result)
    return result


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: str, current_user: dict = Depends(get_current_user)):
    cached = _try_cache_get(f"student:{student_id}")
    if cached:
        return cached

    db = get_db()
    oid = to_object_id(student_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid student ID")

    student = await db["students"].find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = student_from_doc(student)
    _try_cache_set(f"student:{student_id}", result)
    return result


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    admin: dict = Depends(require_admin),
):
    db = get_db()

    if await db["students"].find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    # Auto-create a linked user account so the student can log in.
    # A username is derived from the email; a random temporary password is generated.
    base_username = data.email.split("@")[0]
    username = base_username
    suffix = 1
    while await db["users"].find_one({"username": username}):
        username = f"{base_username}{suffix}"
        suffix += 1

    temp_password = secrets.token_urlsafe(12)
    user_doc = {
        "username": username,
        "password": hash_password(temp_password),
        "role": "student",
    }
    user_result = await db["users"].insert_one(user_doc)
    user_oid = user_result.inserted_id

    gpa = calculate_gpa(data.math, data.programming, data.database)
    doc = {
        **data.model_dump(),
        "gpa": gpa,
        "user_id": user_oid,
    }
    result = await db["students"].insert_one(doc)
    created = await db["students"].find_one({"_id": result.inserted_id})

    _try_cache_delete("students:*")
    logger.info(
        f"Student created: {data.email} (username={username}) by admin {admin['username']}"
    )
    # Return temp credentials so the admin can share them with the student.
    student_out = student_from_doc(created)
    student_out["temp_username"] = username
    student_out["temp_password"] = temp_password
    return student_out


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: str,
    data: StudentUpdate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = to_object_id(student_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid student ID")

    student = await db["students"].find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Students can only edit their own profile; admins can edit any
    if current_user["role"] == "student":
        user_oid = to_object_id(current_user["id"])
        if student.get("user_id") != user_oid:
            raise HTTPException(status_code=403, detail="Cannot edit another student's profile")

    updates = data.model_dump(exclude_unset=True)

    # Recalculate GPA using merged values
    merged = {**student, **updates}
    updates["gpa"] = calculate_gpa(
        merged.get("math"), merged.get("programming"), merged.get("database")
    )

    await db["students"].update_one({"_id": oid}, {"$set": updates})
    updated = await db["students"].find_one({"_id": oid})

    _try_cache_delete(f"student:{student_id}")
    logger.info(f"Student {student_id} updated by {current_user['username']}")
    return student_from_doc(updated)


@router.delete("/{student_id}", status_code=status.HTTP_200_OK)
async def delete_student(
    student_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_db()
    oid = to_object_id(student_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid student ID")

    student = await db["students"].find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await db["students"].delete_one({"_id": oid})
    _try_cache_delete(f"student:{student_id}")
    logger.info(f"Student {student_id} deleted by admin {admin['username']}")
    return {"message": "Student deleted successfully"}
