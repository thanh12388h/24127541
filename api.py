# api_mock.py - FastAPI backend stable mock (generate không cần LLM)
import sys, os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlite3 import IntegrityError, OperationalError, DatabaseError
import traceback

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from passlib.context import CryptContext

# ---------------------------
# Đảm bảo Python thấy các module cùng thư mục
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ---------------------------
# Import DB helpers
from db import init_db, create_user, get_user_by_email, save_history, get_history_for_user

# ---------------------------
# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# CONFIG
SECRET_KEY = os.environ.get("SECRET_KEY", "change_this_secret_for_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# App init
app = FastAPI()
init_db()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Pydantic models
class ItineraryRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    interests: List[str]
    pace: str

class UserCreate(BaseModel):
    email: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------------------------
# Auth helpers
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except Exception:
        return None

# ---------------------------
# Endpoints: register / login
@app.post("/register")
def register(user: UserCreate):
    try:
        existing = get_user_by_email(user.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        pw_hash = pwd_context.hash(user.password)
        uid = create_user(user.email, pw_hash)
        token = create_access_token({"sub": str(uid)})
        return {"user_id": uid, "access_token": token}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login")
def login(user: UserCreate):
    try:
        existing = get_user_by_email(user.email)
        if not existing or not pwd_context.verify(user.password, existing["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token({"sub": str(existing["id"])})
        return {"user_id": existing["id"], "access_token": token}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

# ---------------------------
# Helper: generate mock itinerary
def generate_mock_itinerary(req: ItineraryRequest):
    days = []
    # tạo 1 day = start_date, bạn có thể loop nhiều ngày nếu muốn
    days.append({
        "date": req.start_date,
        "morning": {
            "time": "08:00",
            "title": f"Morning activity in {req.origin}",
            "explain": "Enjoy local attractions."
        },
        "afternoon": {
            "time": "13:00",
            "title": f"Afternoon activity in {req.destination}",
            "explain": "Visit museums or parks."
        },
        "evening": {
            "time": "18:00",
            "title": "Evening entertainment",
            "explain": "Explore nightlife or relax."
        }
    })
    return {"days": days}

# ---------------------------
# Protected generate endpoint
@app.post("/generate")
def generate(req: ItineraryRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = parts[1]
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        itinerary = generate_mock_itinerary(req)
        save_history(user_id, req.dict(), itinerary)
        return itinerary
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generate failed: {str(e)}")

# ---------------------------
# History endpoint
@app.get("/history")
def history(authorization: Optional[str] = Header(None), limit: int = 50):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = parts[1]
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    items = get_history_for_user(user_id, limit=limit)
    return {"history": items}
