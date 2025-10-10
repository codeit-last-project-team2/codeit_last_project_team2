import os
import jwt
import bcrypt
import sqlite3
import secrets
import requests as pyrequests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

# =============================
# 기본 설정
# =============================
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8501")

# DB 설정
DB_DIR = "data/user_info"
DB_PATH = os.path.join(DB_DIR, "users.db")
os.makedirs(DB_DIR, exist_ok=True)

# =============================
# DB 초기화
# =============================
def init_user_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            password TEXT,
            auth_source TEXT DEFAULT 'local', -- local | google
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_user_table()

# =============================
# JWT 관련 함수
# =============================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# =============================
# 모델 정의
# =============================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =============================
# 1️⃣ 회원가입
# =============================
@router.post("/register")
def register(req: RegisterRequest):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (req.email,))
    existing = cur.fetchone()
    if existing:
        source = existing[3] if len(existing) > 3 else "unknown"
        if source == "google":
            raise HTTPException(status_code=400, detail="이미 Google 계정으로 가입된 이메일입니다.")
        else:
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    hashed_pw = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute(
        "INSERT INTO users (email, name, password, auth_source) VALUES (?, ?, ?, 'local')",
        (req.email, req.name, hashed_pw),
    )
    conn.commit()
    conn.close()

    return {"message": "회원가입 성공"}


# =============================
# 2️⃣ 로그인
# =============================
@router.post("/login")
def login(req: LoginRequest):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, name, password, auth_source FROM users WHERE email=?", (req.email,))
    user = cur.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="존재하지 않는 계정입니다.")
    if user[3] == "google":
        raise HTTPException(status_code=400, detail="Google 로그인으로만 접속 가능한 계정입니다.")

    if not bcrypt.checkpw(req.password.encode("utf-8"), user[2].encode("utf-8")):
        raise HTTPException(status_code=400, detail="비밀번호가 올바르지 않습니다.")

    token = create_access_token({"email": user[0], "name": user[1]})
    return {"token": token, "name": user[1], "email": user[0]}


# =============================
# 3️⃣ Google 로그인 (OAuth)
# =============================
@router.get("/google/login")
def google_login():
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


# =============================
# 4️⃣ Google 콜백
# =============================
@router.get("/google/callback")
def google_callback(request: Request, code: str = None, state: str = None):
    # 1. 토큰 요청
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_resp = pyrequests.post(token_url, data=data)
    token_json = token_resp.json()
    access_token = token_json.get("access_token")

    # 2. 유저 정보 가져오기
    user_info = pyrequests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0])

    # 3. DB에 없으면 생성
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()

    if not user:
        cur.execute(
            "INSERT INTO users (email, name, auth_source) VALUES (?, ?, 'google')",
            (email, name)
        )
        conn.commit()
    conn.close()

    # 4. JWT 발급
    token = create_access_token({"email": email, "name": name})

    # 5. 프론트엔드로 리다이렉트
    redirect_url = f"{FRONTEND_URL}?token={token}&email={email}&name={name}"
    return RedirectResponse(redirect_url)


# =============================
# 5️⃣ 내 정보 확인
# =============================
@router.get("/me")
def get_me(token: str = Depends(lambda request: request.headers.get("Authorization", "").replace("Bearer ", ""))):
    payload = verify_token(token)
    return {"email": payload["email"], "name": payload.get("name")}


# =============================
# 6️⃣ 현재 로그인 사용자 확인 (Depends용)
# =============================
def get_current_user(Authorization: str = Header(None)):
    """
    FastAPI Depends()에서 사용하는 인증 함수.
    라우터에서 user=Depends(get_current_user)로 호출하면,
    JWT를 검증하고 {'email': ..., 'name': ...}을 리턴.
    """
    if not Authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = Authorization.replace("Bearer ", "")
    payload = verify_token(token)

    return {"email": payload["email"], "name": payload.get("name")}
