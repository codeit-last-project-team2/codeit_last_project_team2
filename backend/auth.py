import os
import jwt
import bcrypt
import sqlite3
import secrets
import traceback
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request as StarletteRequest
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth

# =====================================================
# ✅ 환경 변수 로드
# =====================================================
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])

# -----------------------------------------------------
# 기본 설정
# -----------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI  = os.getenv("NAVER_REDIRECT_URI")

KAKAO_CLIENT_ID     = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI  = os.getenv("KAKAO_REDIRECT_URI")

# 사용 가능 여부 플래그
HAS_NAVER  = bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET and NAVER_REDIRECT_URI)
HAS_KAKAO  = bool(KAKAO_CLIENT_ID and KAKAO_REDIRECT_URI)

# -----------------------------------------------------
# JWT 및 보안 의존성
# -----------------------------------------------------
security = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI Depends 인증용"""
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

# -----------------------------------------------------
# OAuth 클라이언트 등록
# -----------------------------------------------------
oauth = OAuth()

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("⚠️ GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수를 설정하세요.")

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

# =====================================================
# ✅ 사용 가능 OAuth 목록
# =====================================================
@router.get("/enabled")
async def auth_enabled():
    return {"google": True, "naver": HAS_NAVER, "kakao": HAS_KAKAO}

# =====================================================
# ✅ GOOGLE 로그인
# =====================================================
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
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(status_code=400, detail="Google OAuth failed")

        email = user_info["email"]
        name = user_info.get("name", "")
        sub = user_info.get("sub", "")

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=2)

        payload = {
            "sub": sub,
            "email": email,
            "name": name,
            "provider": "google",
            "iss": "adgen-api",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "OAuth callback failed"}, status_code=500)

# =====================================================
# ✅ NAVER 로그인
# =====================================================
@router.get("/naver/login")
async def naver_login(request: StarletteRequest):
    if not HAS_NAVER:
        raise HTTPException(status_code=501, detail="Naver OAuth not configured")
    redirect_uri = NAVER_REDIRECT_URI
    return await oauth.naver.authorize_redirect(request, redirect_uri)

@router.get("/naver/callback")
async def naver_callback(request: StarletteRequest):
    try:
        token = await oauth.naver.authorize_access_token(request)
        resp = await oauth.naver.get("nid/me", token=token)
        data = resp.json().get("response", {}) if resp else {}

        sub = data.get("id")
        email = data.get("email") or f"{sub}@naver-user.local"
        name = data.get("name") or data.get("nickname") or "NaverUser"

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=2)
        payload = {
            "sub": sub,
            "email": email,
            "name": name,
            "provider": "naver",
            "iss": "adgen-api",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("NAVER CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Naver OAuth callback failed"}, status_code=500)

# =====================================================
# ✅ KAKAO 로그인
# =====================================================
@router.get("/kakao/login")
async def kakao_login(request: StarletteRequest):
    if not HAS_KAKAO:
        raise HTTPException(status_code=501, detail="Kakao OAuth not configured")
    params = {"scope": "profile_nickname"}
    return await oauth.kakao.authorize_redirect(request, KAKAO_REDIRECT_URI, **params)

@router.get("/kakao/callback")
async def kakao_callback(request: StarletteRequest):
    try:
        token = await oauth.kakao.authorize_access_token(request)
        resp = await oauth.kakao.get("v2/user/me", token=token)
        info = resp.json() if resp else {}

        kid = info.get("id")
        acc = info.get("kakao_account") or {}
        profile = acc.get("profile") or {}
        name = profile.get("nickname") or "KakaoUser"
        email = acc.get("email") or f"{kid}@kakao-user.local"

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=2)
        payload = {
            "sub": str(kid),
            "email": email,
            "name": name,
            "provider": "kakao",
            "iss": "adgen-api",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("KAKAO CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Kakao OAuth callback failed"}, status_code=500)

# =====================================================
# ✅ 세션 검증용 /auth/me (Home.py 호환)
# =====================================================
@router.get("/me")
async def auth_me(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        return JSONResponse({"detail": "Missing token"}, status_code=status.HTTP_401_UNAUTHORIZED)
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return {
            "email": payload.get("email"),
            "name": payload.get("name"),
            "provider": payload.get("provider", "google"),
        }
    except Exception:
        return JSONResponse({"detail": "Invalid token"}, status_code=status.HTTP_401_UNAUTHORIZED)
