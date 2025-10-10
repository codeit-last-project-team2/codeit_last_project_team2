# backend/auth.py
import os
import jwt
import bcrypt
import sqlite3
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request as StarletteRequest
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth

# =====================================================
# 환경 변수 & 공통
# =====================================================
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)
def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    """
    라우터에서 Depends(get_current_user)로 쓰는 토큰 검증 헬퍼.
    payload(dict)를 반환하므로 라우터에서 사용자 정보 읽어 쓸 수 있음.
    """
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth token"
        )
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token"
        )

JWT_SECRET   = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM    = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
NAVER_CLIENT_ID      = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET  = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI   = os.getenv("NAVER_REDIRECT_URI")
KAKAO_CLIENT_ID      = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET  = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI   = os.getenv("KAKAO_REDIRECT_URI")

HAS_GOOGLE = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
HAS_NAVER  = bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET and NAVER_REDIRECT_URI)
HAS_KAKAO  = bool(KAKAO_CLIENT_ID and KAKAO_REDIRECT_URI)

# =====================================================
# DB (SQLite) - users 테이블
# =====================================================
_ROOT   = Path(__file__).resolve().parent.parent   # .../backend
_DBPATH = _ROOT / "data" / "adgen.db"
_DBPATH.parent.mkdir(parents=True, exist_ok=True)

def _db():
    con = sqlite3.connect(str(_DBPATH))
    con.row_factory = sqlite3.Row
    return con

def _init_db():
    with _db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          provider TEXT DEFAULT 'local',
          provider_id TEXT,
          username TEXT,
          email TEXT,
          name TEXT,
          password_hash TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP
        )
        """)
        c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_username
        ON users(provider, username)
        """)
_init_db()

# =====================================================
# JWT & PW
# =====================================================
def _make_token(payload: dict) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=2)
    body = {"iss":"adgen-api","iat":int(now.timestamp()),"exp":int(exp.timestamp()), **payload}
    return jwt.encode(body, JWT_SECRET, algorithm=ALGORITHM)

def _hash_pw(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _verify_pw(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# =====================================================
# 로그인 수단 노출
# =====================================================
@router.get("/enabled")
async def auth_enabled():
    return {"google": HAS_GOOGLE, "naver": HAS_NAVER, "kakao": HAS_KAKAO}

# =====================================================
# OAuth (등록된 것만 활성)
# =====================================================
oauth = OAuth()
if HAS_GOOGLE:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
if HAS_NAVER:
    oauth.register(
        name="naver",
        client_id=NAVER_CLIENT_ID,
        client_secret=NAVER_CLIENT_SECRET,
        authorize_url="https://nid.naver.com/oauth2.0/authorize",
        access_token_url="https://nid.naver.com/oauth2.0/token",
        api_base_url="https://openapi.naver.com/v1/",
        client_kwargs={"token_endpoint_auth_method": "client_secret_post"},
    )
if HAS_KAKAO:
    oauth.register(
        name="kakao",
        client_id=KAKAO_CLIENT_ID,
        client_secret=KAKAO_CLIENT_SECRET,
        authorize_url="https://kauth.kakao.com/oauth/authorize",
        access_token_url="https://kauth.kakao.com/oauth/token",
        api_base_url="https://kapi.kakao.com/",
        client_kwargs={"token_endpoint_auth_method": "client_secret_post"},
    )

# -- Google
if HAS_GOOGLE:
    @router.get("/google/login")
    async def google_login(request: StarletteRequest):
        redirect_uri = request.url_for("google_callback")
        return await oauth.google.authorize_redirect(request, redirect_uri)

    @router.head("/google/login")
    async def google_login_head():
        return PlainTextResponse("", status_code=200)

    @router.get("/google/callback")
    async def google_callback(request: StarletteRequest):
        try:
            token = await oauth.google.authorize_access_token(request)
            user_info = token.get("userinfo") or {}
            email = user_info.get("email")
            name  = user_info.get("name") or ""
            sub   = user_info.get("sub") or ""

            if not email:
                raise HTTPException(400, "Google OAuth failed")

            app_jwt = _make_token({
                "sub": sub, "email": email, "name": name, "provider": "google"
            })
            target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
            return RedirectResponse(url=target)
        except Exception:
            print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
            return JSONResponse({"error": "OAuth callback failed"}, status_code=500)

# -- Naver
if HAS_NAVER:
    @router.get("/naver/login")
    async def naver_login(request: StarletteRequest):
        return await oauth.naver.authorize_redirect(request, os.getenv("NAVER_REDIRECT_URI"))

    @router.get("/naver/callback")
    async def naver_callback(request: StarletteRequest):
        try:
            token = await oauth.naver.authorize_access_token(request)
            resp = await oauth.naver.get("nid/me", token=token)
            data = resp.json().get("response", {}) if resp else {}
            sub   = data.get("id")
            email = data.get("email") or f"{sub}@naver-user.local"
            name  = data.get("name") or data.get("nickname") or "NaverUser"

            app_jwt = _make_token({
                "sub": sub, "email": email, "name": name, "provider": "naver"
            })
            target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
            return RedirectResponse(url=target)
        except Exception:
            print("NAVER CALLBACK ERROR:\n", traceback.format_exc())
            return JSONResponse({"error": "Naver OAuth callback failed"}, status_code=500)

# -- Kakao
if HAS_KAKAO:
    @router.get("/kakao/login")
    async def kakao_login(request: StarletteRequest):
        return await oauth.kakao.authorize_redirect(request, KAKAO_REDIRECT_URI, scope="profile_nickname")

    @router.get("/kakao/callback")
    async def kakao_callback(request: StarletteRequest):
        try:
            token = await oauth.kakao.authorize_access_token(request)
            resp = await oauth.kakao.get("v2/user/me", token=token)
            info = resp.json() if resp else {}
            kid  = info.get("id")
            acc  = info.get("kakao_account") or {}
            prof = acc.get("profile") or {}
            name = prof.get("nickname") or "KakaoUser"
            email = acc.get("email") or f"{kid}@kakao-user.local"

            app_jwt = _make_token({
                "sub": str(kid), "email": email, "name": name, "provider": "kakao"
            })
            target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
            return RedirectResponse(url=target)
        except Exception:
            print("KAKAO CALLBACK ERROR:\n", traceback.format_exc())
            return JSONResponse({"error": "Kakao OAuth callback failed"}, status_code=500)

# =====================================================
# Local: 아이디/비밀번호
# =====================================================
@router.post("/signup")
async def local_signup(payload: dict):
    """
    username(필수) + password(>=6)
    이메일 형태면 email 필드도 채워줌
    """
    username = (payload.get("username") or payload.get("email") or "").strip()
    password = (payload.get("password") or "").strip()
    name     = (payload.get("name") or username).strip()

    if not username or not password:
        raise HTTPException(400, "username/password required")
    if len(password) < 6:
        raise HTTPException(400, "password too short (>=6)")

    # email 필드 자동 추정(선택)
    email = payload.get("email")
    if not email and "@" in username:
        email = username

    with _db() as c:
        if c.execute("SELECT 1 FROM users WHERE provider='local' AND username=?", (username,)).fetchone():
            raise HTTPException(409, "username already exists")
        c.execute("""
            INSERT INTO users(provider, username, email, name, password_hash, updated_at)
            VALUES('local', ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (username, email, name, _hash_pw(password)))
        uid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    token = _make_token({"uid": uid, "username": username, "name": name, "provider": "local"})
    return {"token": token, "user": {"id": uid, "username": username, "name": name}}

@router.post("/login")
async def local_login(payload: dict):
    """
    identifier = username 또는 email(둘 다 허용)
    """
    identifier = (payload.get("username") or payload.get("email") or "").strip()
    password   = (payload.get("password") or "").strip()

    if not identifier or not password:
        raise HTTPException(400, "username/password required")

    with _db() as c:
        row = c.execute("""
            SELECT id, username, name, password_hash
            FROM users
            WHERE provider='local' AND (username=? OR email=?)
            LIMIT 1
        """, (identifier, identifier)).fetchone()

    if not row or not row["password_hash"] or not _verify_pw(password, row["password_hash"]):
        raise HTTPException(401, "invalid credentials")

    token = _make_token({"uid": row["id"], "username": row["username"], "name": row["name"], "provider": "local"})
    return {"token": token, "user": {"id": row["id"], "username": row["username"], "name": row["name"]}}

@router.get("/userinfo/{identifier}")
async def userinfo(identifier: str):
    with _db() as c:
        row = c.execute("""
            SELECT id, username, name, email
            FROM users WHERE username=? OR email=? LIMIT 1
        """, (identifier, identifier)).fetchone()
    if not row:
        return {"message": "not found"}
    return {"id": row["id"], "username": row["username"], "name": row["name"], "email": row["email"]}

@router.get("/me")
async def auth_me(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        return JSONResponse({"detail": "Missing token"}, status_code=status.HTTP_401_UNAUTHORIZED)
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return {
            "email": payload.get("email"),
            "username": payload.get("username"),
            "name": payload.get("name"),
            "provider": payload.get("provider", "local"),
        }
    except Exception:
        return JSONResponse({"detail": "Invalid token"}, status_code=status.HTTP_401_UNAUTHORIZED)
