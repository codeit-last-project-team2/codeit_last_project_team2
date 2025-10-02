import os
import sqlite3
from backend.models.user_information_model import UserInformationRequest, UserInformationResponse

# DB 경로
BASE_DIR = os.path.join("data", "user_info")
os.makedirs(BASE_DIR, exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, "database.db")

# 테이블 초기화
def init_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_information (
            email TEXT PRIMARY KEY,
            store_name TEXT,
            category TEXT,
            phone TEXT,
            address TEXT
        )
    """)
    conn.commit()
    conn.close()

# 저장 (있으면 업데이트, 없으면 생성)
def save_user_info(req: UserInformationRequest):
    init_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_information (email, store_name, category, phone, address)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            store_name=excluded.store_name,
            category=excluded.category,
            phone=excluded.phone,
            address=excluded.address
    """, (req.email, req.store_name, req.category, req.phone, req.address))
    conn.commit()
    conn.close()
    return {"message": "User information saved successfully"}

# 조회
def get_user_info(email: str):
    init_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, store_name, category, phone, address FROM user_information WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    if row:
        return UserInformationResponse(
            email=row[0],
            store_name=row[1],
            category=row[2],
            phone=row[3],
            address=row[4],
        )
    return {"message": "No user information found"}
