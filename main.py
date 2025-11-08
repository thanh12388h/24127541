import os
from db import get_conn
from datetime import datetime, timedelta
from typing import Optional, List
import json
from sqlite3 import IntegrityError, OperationalError

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from passlib.context import CryptContext

# ---------------------------
# DB helpers
from db import init_db, create_user, get_user_by_email, get_user_by_id, save_history, get_history_for_user

# ---------------------------
# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Config
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
class UserCreate(BaseModel):
    email: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ItineraryRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    interests: List[str]
    pace: str

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
        return int(payload.get("sub"))
    except Exception:
        return None

# ---------------------------
# Register / Login
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
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login")
def login(user: UserCreate):
    existing = get_user_by_email(user.email)
    if not existing or not pwd_context.verify(user.password, existing["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(existing["id"])})
    return {"user_id": existing["id"], "access_token": token}

# ---------------------------
# Generate itinerary (mock)
@app.post("/generate")
def generate(req: ItineraryRequest, authorization: Optional[str] = Header(None)):
    # --- Xác thực token ---
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split()[1]
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # --- Parse dates ---
    try:
        start = datetime.fromisoformat(req.start_date).date()
        end = datetime.fromisoformat(req.end_date).date()
        if end < start:
            raise HTTPException(status_code=400, detail="end_date must be after start_date")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    # --- Tạo itinerary cho từng ngày ---
    days = []
    delta_days = (end - start).days + 1  # số ngày cần generate
    for i in range(delta_days):
        current_date = start + timedelta(days=i)
        day = {
            "date": current_date.isoformat(),
            "morning": {"time":"08:00","title":"Morning walk","explain":"Explore local streets."},
            "afternoon": {"time":"13:00","title":"Museum visit","explain":"Enjoy history and culture."},
            "evening": {"time":"18:00","title":"Dinner & Nightlife","explain":"Try local cuisine."}
        }
        days.append(day)

    result = {"days": days}

    # --- Lưu lịch sử ---
    save_history(user_id, req.dict(), result)
    return result
# ---------------------------
# History endpoint
@app.get("/history")
def history(authorization: Optional[str] = Header(None), limit: int = 50):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split()[1]
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    items = get_history_for_user(user_id, limit=limit)
    return {"history": items}
