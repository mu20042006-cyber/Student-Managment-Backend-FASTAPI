from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.database import get_db
from app.core.auth_handler import hash_password, verify_password, create_access_token
from app.core.auth_dependencies import get_current_user, require_admin
from app.schemas.user_schema import UserCreate, UserOut, TokenResponse
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    db = get_db()

    if await db["users"].find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    if await db["students"].find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user document
    user_doc = {
        "username": payload.username,
        "password": hash_password(payload.password),
        "role": "student",
    }
    result = await db["users"].insert_one(user_doc)
    user_id = result.inserted_id

    # Create linked student profile
    student_doc = {
        "name": payload.name,
        "email": payload.email,
        "department": payload.department,
        "math": None,
        "programming": None,
        "database": None,
        "gpa": None,
        "user_id": user_id,
    }
    await db["students"].insert_one(student_doc)

    logger.info(f"New student registered: {payload.username}")
    return {"message": "Student registered successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()

    logger.info(f"Login attempt: {form_data.username}")

    # Get user first
    user = await db["users"].find_one({
        "username": form_data.username
    })

    # User not found
    if not user:
        logger.warning(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not exist"
        )

    # Account deleted
    if user.get("is_deleted") == True:
        logger.warning(f"Deleted account login attempt: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deleted by admin"
        )

    # Wrong password
    if not verify_password(form_data.password, user["password"]):
        logger.warning(f"Failed login: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    token = create_access_token({
        "sub": user["username"],
        "role": user.get("role", "student")
    })

    logger.info(f"Successful login: {form_data.username}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.get("role", "student"),
        "username": user["username"],
    }


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/admin")
async def admin_only(admin: dict = Depends(require_admin)):
    return {"message": f"Welcome Admin, {admin['username']}"}


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users():
    db = get_db()
    cursor = db["users"].find({}, {"password": 0})
    users = []
    async for doc in cursor:
        users.append({"id": str(doc["_id"]), "username": doc["username"], "role": doc.get("role", "student")})
    return users


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: str):
    from app.models.models import to_object_id
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await db["users"].find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db["students"].delete_one({"user_id": oid})
    await db["users"].delete_one({"_id": oid})

    logger.info(f"User {user_id} deleted")
    return {"message": "User and linked student profile deleted"}
