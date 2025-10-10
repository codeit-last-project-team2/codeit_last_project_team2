# backend/auth.py
import os, jwt, traceback
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request as StarletteRequest
from jwt.exceptions import InvalidTokenError
from datetime import datetime
from dotenv import load_dotenv

# ========================
# NEW: 최소 변경 추가 import
# ========================
from datetime import timedelta, timezone   # NEW
from fastapi.responses import PlainTextResponse  # NEW

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

# ==========================
# NEW: (옵션) 다른 프로바이더 키
# ==========================
NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")          # NEW
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")      # NEW
NAVER_REDIRECT_URI  = os.getenv("NAVER_REDIRECT_URI")       # NEW
KAKAO_CLIENT_ID     = os.getenv("KAKAO_CLIENT_ID")          # NEW
KAKAO_REDIRECT_URI  = os.getenv("KAKAO_REDIRECT_URI")       # NEW

# NEW: 사용 가능 여부 플래그
HAS_NAVER  = bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET and NAVER_REDIRECT_URI)   # NEW
HAS_KAKAO  = bool(KAKAO_CLIENT_ID and KAKAO_REDIRECT_URI)                            # NEW

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수를 설정하세요.")

router = APIRouter(tags=["Auth"])

# --- JWT ---
security = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            leeway=10  # NEW: 시계 오차 여유
        )
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

# --- OAuth ---
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# =========================
# NEW: Naver OAuth 등록
# =========================
if HAS_NAVER:  # NEW
    oauth.register(
        name="naver",
        client_id=NAVER_CLIENT_ID,
        client_secret=NAVER_CLIENT_SECRET,
        authorize_url="https://nid.naver.com/oauth2.0/authorize",
        access_token_url="https://nid.naver.com/oauth2.0/token",
        api_base_url="https://openapi.naver.com/v1/",
        client_kwargs={
            "token_endpoint_auth_method": "client_secret_post",
        },
    )

if HAS_KAKAO:
    oauth.register(
        name="kakao",
        client_id=KAKAO_CLIENT_ID,
        client_secret=os.getenv("KAKAO_CLIENT_SECRET"),  # 시크릿 ON이면 주석 해제
        authorize_url="https://kauth.kakao.com/oauth/authorize",
        access_token_url="https://kauth.kakao.com/oauth/token",
        api_base_url="https://kapi.kakao.com/",
        client_kwargs={"token_endpoint_auth_method": "client_secret_post"},
    )

# =========================
# NEW: 가용 여부 엔드포인트
# =========================
@router.get("/auth/enabled")
async def auth_enabled():
    return {"google": True, "naver": HAS_NAVER, "kakao": HAS_KAKAO}

@router.get("/auth/google/login")
async def login(request: StarletteRequest):
    redirect_uri = request.url_for("auth_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

# NEW: 프리플라이트 체크용 HEAD (버튼 표시 판단용)
@router.head("/auth/google/login")
async def login_head():
    return PlainTextResponse("", status_code=200)

@router.get("/auth/google/callback")
async def auth_google_callback(request: StarletteRequest):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(status_code=400, detail="Google OAuth failed")

        sub = user_info["sub"]
        email = user_info["email"]
        name = user_info.get("name", "")
        # ======================================
        # CHANGED: 만료/발급시간을 UTC + timedelta
        # ======================================
        now = datetime.now(timezone.utc)                 # NEW
        exp = now + timedelta(hours=2)                   # NEW

        payload = {
            "sub": sub,
            "email": email,
            "name": name,
            "iss": "adgen-api",
            "iat": int(now.timestamp()),                 # CHANGED
            "exp": int(exp.timestamp()),                 # CHANGED
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "OAuth callback failed"}, status_code=500)

# ===========================
# CHANGED: 네이버 로그인 실제 구현
# ===========================
@router.get("/auth/naver/login")
async def naver_login(request: StarletteRequest):
    if not HAS_NAVER:
        raise HTTPException(status_code=501, detail="Naver OAuth is not configured")
    redirect_uri = NAVER_REDIRECT_URI  # ← 콘솔과 100% 동일한 값
    print("[NAVER] authorize redirect_uri:", redirect_uri)  # 디버깅용(선택)
    return await oauth.naver.authorize_redirect(request, redirect_uri)

@router.get("/auth/naver/callback")  # NEW
async def naver_callback(request: StarletteRequest):
    try:
        token = await oauth.naver.authorize_access_token(request)
        # 디버그: 토큰 응답 확인
        print("[NAVER] token:", token)

        resp = await oauth.naver.get("nid/me", token=token)
        print("[NAVER] profile status:", resp.status_code)
        print("[NAVER] profile body:", resp.text)

        data = resp.json().get("response", {}) if resp else {}

        sub   = data.get("id")
        email = data.get("email") or (f"{sub}@naver-user.local" if sub else None)
        name  = data.get("name") or data.get("nickname") or "NaverUser"

        if not sub:
            raise HTTPException(status_code=400, detail="Naver profile missing id")

        # Google과 동일한 JWT 포맷 유지
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=2)
        payload = {
            "sub": sub,
            "email": email,
            "name": name,
            "iss": "adgen-api",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "provider": "naver",  # NEW: 구분 편의를 위해 추가(프론트가 있으면 표시됨)
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email or ''}"
        return RedirectResponse(url=target)
    except Exception:
        print("NAVER CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Naver OAuth callback failed"}, status_code=500)

# ===========================
# 그대로 유지: 카카오는 자리표시자
# ===========================
@router.get("/auth/kakao/login")
async def kakao_login(request: StarletteRequest):
    if not HAS_KAKAO:
        raise HTTPException(status_code=501, detail="Kakao OAuth is not configured")
    # CHANGED: 이메일 동의 없이 닉네임만 요청
    params = {"scope": "profile_nickname"}
    return await oauth.kakao.authorize_redirect(request, KAKAO_REDIRECT_URI, **params)

@router.get("/auth/kakao/callback")
async def kakao_callback(request: StarletteRequest):
    try:
        token = await oauth.kakao.authorize_access_token(request)
        resp = await oauth.kakao.get("v2/user/me", token=token)
        info = resp.json() if resp else {}

        kid = info.get("id")
        acc = info.get("kakao_account") or {}
        profile = acc.get("profile") or {}
        name = profile.get("nickname") or "KakaoUser"

        # CHANGED: 이메일 동의가 없으므로 안전한 대체 이메일 사용
        email = acc.get("email") or (f"{kid}@kakao-user.local" if kid else "unknown@kakao-user.local")

        if not kid:
            raise HTTPException(status_code=400, detail="Kakao profile missing id")

        now = datetime.now(timezone.utc); exp = now + timedelta(hours=2)
        payload = {
            "sub": str(kid),
            "email": email,        # ← 항상 존재하게 보장
            "name": name,
            "provider": "kakao",
            "iss": "adgen-api",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("KAKAO CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Kakao OAuth callback failed"}, status_code=500)
