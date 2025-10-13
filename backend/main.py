# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from urllib.parse import urlparse
import os, sqlite3
from dotenv import load_dotenv

# --- 환경 변수 로드 ---
load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

app = FastAPI(title="AdGen API", version="2.1")

# --- CORS ---
_front = urlparse(FRONTEND_URL)
ALLOWED_ORIGINS = [f"{_front.scheme}://{_front.netloc}"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 세션 (OAuth용) ---
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET, same_site="lax")

# --- DB 초기화 ---
DB_PATH = os.path.join("data", "images", "adgen.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        text TEXT,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
init_db()

# --- Static 파일 제공 (data/images) ---
IMAGES_DIR = os.path.join("data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# --- 라우터 등록 ---
from backend.routers import poster, mascot, homepage, cardnews, userinfo, adcopy
from backend import auth
app.include_router(auth.router)
app.include_router(poster.router)
app.include_router(mascot.router)
# app.include_router(homepage.router)
app.include_router(cardnews.router)
app.include_router(userinfo.router)
app.include_router(adcopy.router)