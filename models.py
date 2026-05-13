from bson import ObjectId
from typing import Optional


def user_from_doc(doc: dict) -> dict:
    """Serialize a MongoDB user document to a clean dict."""
    if not doc:
        return {}
    return {
        "id": str(doc["_id"]),
        "username": doc["username"],
        "password": doc["password"],
        "role": doc.get("role", "student"),
    }


def student_from_doc(doc: dict) -> dict:
    """Serialize a MongoDB student document to a clean dict."""
    if not doc:
        return {}
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "department": doc.get("department"),
        "math": doc.get("math"),
        "programming": doc.get("programming"),
        "database": doc.get("database"),
        "gpa": doc.get("gpa"),
        "user_id": str(doc["user_id"]),
    }


def to_object_id(id_str: str) -> Optional[ObjectId]:
    try:
        return ObjectId(id_str)
    except Exception:
        return None
