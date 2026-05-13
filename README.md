# 🎓 Student Management Pro

A full-stack Student Management System built with **FastAPI + MongoDB + Redis + JWT Auth**.

---

## 📁 Project Structure

```
StudentManagementPro/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py            # Settings via pydantic-settings + .env
│   │   │   ├── database.py          # Async MongoDB (Motor) connection
│   │   │   ├── redis_client.py      # Redis client (optional, graceful fallback)
│   │   │   ├── auth_handler.py      # JWT encode/decode, bcrypt hashing
│   │   │   └── auth_dependencies.py # FastAPI Depends: get_current_user, require_admin
│   │   ├── models/
│   │   │   └── models.py            # MongoDB document serializers
│   │   ├── schemas/
│   │   │   ├── user_schema.py       # Pydantic: UserCreate, UserOut, TokenResponse
│   │   │   └── student_schema.py    # Pydantic: StudentCreate, StudentUpdate, StudentOut
│   │   ├── routers/
│   │   │   ├── auth_router.py       # /auth/register, /login, /me, /users
│   │   │   ├── student_router.py    # /students CRUD + filter + pagination
│   │   │   └── monitor_router.py    # /monitor/health, /stats, /logs
│   │   ├── services/
│   │   │   └── gpa_service.py       # GPA calculation logic (0–100 → 0.0–4.0)
│   │   ├── utils/
│   │   │   └── logger.py            # Structured logging to console + app.log
│   │   ├── tests/
│   │   │   ├── conftest.py          # Async test client + MongoDB mock fixtures
│   │   │   ├── test_auth.py         # Auth endpoint tests
│   │   │   └── test_student.py      # Student endpoint + GPA tests
│   │   └── main.py                  # FastAPI app, CORS, middleware, lifespan
│   ├── .env                         # Your local config (not committed)
│   ├── .env.example                 # Template for env vars
│   ├── requirements.txt
│   └── pytest.ini
└── frontend/
    └── index.html                   # Single-file SPA (no build step needed)
```

---

## ⚙️ Prerequisites

- Python 3.11+
- MongoDB running locally (`mongodb://localhost:27017`)
- Redis (optional — app works without it, caching is skipped gracefully)

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy env file
copy .env.example .env          # Windows
# cp .env.example .env          # Mac/Linux

# Run the server
uvicorn app.main:app --reload
```

API is live at: **http://127.0.0.1:8000**  
Swagger docs: **http://127.0.0.1:8000/docs**

### 2. Frontend

Just open in your browser — no build step needed:

```
frontend/index.html  →  double-click or open with Live Server in VS Code
```

Make sure the backend is running first.

---

## 🔐 Authentication

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/auth/register` | POST | ❌ | Register new student |
| `/auth/login` | POST | ❌ | Login, returns JWT |
| `/auth/me` | GET | ✅ | Get current user info |
| `/auth/admin` | GET | Admin | Admin-only test route |
| `/auth/users` | GET | Admin | List all users |
| `/auth/users/{id}` | DELETE | Admin | Delete user + student profile |

### Creating an Admin

MongoDB doesn't have a registration route for admins (by design). Create one via the shell:

```bash
# In MongoDB shell / Compass
db.users.updateOne({ username: "yourusername" }, { $set: { role: "admin" } })
```

Or use the provided seed script concept in conftest.

---

## 🎓 Students API

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/students/` | GET | Any | List students (filter + paginate) |
| `/students/me` | GET | Student | Get own profile |
| `/students/{id}` | GET | Any | Get single student |
| `/students/` | POST | Admin | Create student |
| `/students/{id}` | PUT | Any* | Update student |
| `/students/{id}` | DELETE | Admin | Delete student |

*Students can only update their own profile.

### Filtering & Pagination

```
GET /students/?page=1&page_size=10&search=ahmed&department=CS&min_gpa=3
```

---

## 📊 GPA Scale

| Average Score | GPA |
|---|---|
| 90–100 | 4.0 |
| 80–89  | 3.0 |
| 70–79  | 2.0 |
| 60–69  | 1.0 |
| < 60   | 0.0 |

---

## 🧪 Running Tests

```bash
cd backend
pytest -v
```

Tests use mocked MongoDB — **no real database needed**.

---

## 🔍 Monitoring

| Endpoint | Description |
|---|---|
| `GET /monitor/health` | Health check |
| `GET /monitor/stats` | Request count + Redis status |
| `GET /monitor/logs` | Last 50 log lines |

---

## 🐳 Docker

Run the full stack (API + MongoDB + Redis) with one command:

```bash
docker-compose up --build
```

| Service | Port |
|---|---|
| FastAPI API | http://localhost:8000 |
| MongoDB | localhost:27017 |
| Redis | localhost:6379 |

To run only the dependencies (and the API locally):

```bash
docker-compose up mongo redis
cd backend && uvicorn app.main:app --reload
```

---

## 🐛 Bugs Fixed

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `database.py` | Used MySQL/SQLAlchemy instead of MongoDB | Replaced with Motor (async MongoDB) |
| 2 | `student_router.py` | `from fastapi import logger` (doesn't exist) | Removed, uses `app.utils.logger` |
| 3 | `student_router.py` | `GET /me` route after `GET /{id}` — "me" matched as integer → 422 | Moved `/me` above `/{student_id}` |
| 4 | `student_router.py` | `POST /` created Student without `user_id` (NOT NULL) | Fixed — uses admin's ID |
| 5 | `core/config.py` | Hardcoded secrets, no `.env` support | pydantic-settings with `.env` |
| 6 | `monitor_router.py` | Module-level counter mutated across import boundary | Isolated counter + Redis-backed |
| 7 | `tests/` | Near-empty tests, no fixtures, no assertions | Full async tests with mocked DB |
| 8 | Missing | No `requirements.txt` | Generated with pinned versions |
| 9 | `frontend/` | No error handling, no loading states, no token expiry | Full UX: toasts, spinners, expiry |
| 10 | `student_router.py` | `_try_cache_delete("students:*")` passed literal `*` to Redis `DEL` (no-op) | Replaced with `SCAN` + `DEL` pattern deletion |
| 11 | `student_router.py` | Admin-created students had no linked user account (couldn't log in) | Auto-creates a user account; returns temp credentials to admin |
| 12 | Missing | No Docker support | Added `Dockerfile` + `docker-compose.yml` (api + mongo + redis) |

---

## 📦 Dependencies

```
fastapi, uvicorn        # Web framework
motor, pymongo          # Async MongoDB
python-jose             # JWT
passlib[bcrypt]         # Password hashing
pydantic, pydantic-settings  # Validation + config
redis                   # Caching (optional)
python-multipart        # Form data (OAuth2 login)
httpx, pytest, pytest-asyncio  # Testing
```
