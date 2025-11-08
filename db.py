# db.py
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict

DB_FILE = "data.db"

def get_conn() -> sqlite3.Connection:
    """Trả về kết nối DB, đảm bảo an toàn cho FastAPI/multithread."""
    # check_same_thread=False là cần thiết cho FastAPI (uvicorn workers)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Giúp truy cập kết quả bằng tên cột
    return conn

def init_db():
    """Khởi tạo các bảng Users và History."""
    print("Initializing database...")
    conn = get_conn()
    c = conn.cursor()
    
    # users table: Email phải là UNIQUE
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT
    )
    """)
    # history table
    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        request_json TEXT NOT NULL,
        response_json TEXT NOT NULL,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()
    print("Database initialization complete.")

# user helper
def create_user(email: str, password_hash: str) -> int:
    """Tạo người dùng mới và trả về ID. Có thể raise IntegrityError."""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        c.execute("INSERT INTO users (email, password_hash, created_at) VALUES (?,?,?)",
                  (email, password_hash, now))
        conn.commit()
        user_id = c.lastrowid
        return user_id
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Tìm người dùng bằng email."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    # Trả về dict từ sqlite3.Row
    return dict(row)

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Tìm người dùng bằng ID. (Bổ sung để khắc phục lỗi ImportError)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    # Trả về dict từ sqlite3.Row
    return dict(row)

# history helper
def save_history(user_id: int, request_obj: dict, response_obj: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        c.execute("INSERT INTO history (user_id, request_json, response_json, created_at) VALUES (?,?,?,?)",
                  (user_id, json.dumps(request_obj, ensure_ascii=False), json.dumps(response_obj, ensure_ascii=False), now))
        conn.commit()
        hid = c.lastrowid
        return hid
    finally:
        conn.close()

def get_history_for_user(user_id: int, limit: int = 100) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, request_json, response_json, created_at FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        item = dict(r)
        out.append({
            "id": item["id"],
            "request": json.loads(item["request_json"]),
            "response": json.loads(item["response_json"]),
            "created_at": item["created_at"]
        })
    return out