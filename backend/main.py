# backend/main.py
# ---------------------------------------------------------
# Google OAuth 로그인 → JWT 발급 → 프론트로 리다이렉트
# /auth/google/login : 구글 로그인 시작
# /auth/google/callback : 콜백 → JWT 발급 → FRONTEND_URL로 이동
# /me : 토큰으로 내 정보 확인
# (데모) 생성/합성 관련 엔드포인트는 스텁으로 포함
# ---------------------------------------------------------
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware


import os, jwt, traceback
from jwt import PyJWTError
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse


# --- 환경 변수 로드 (.env) ---
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")


if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수를 .env에 설정하세요.")


app = FastAPI(title="AdGen Auth Minimal", version="1.2")


# --- CORS (Streamlit 오리진만 허용 권장) ---
_front = urlparse(FRONTEND_URL)
ALLOWED_ORIGINS = [f"{_front.scheme}://{_front.netloc}"] # 예: http://localhost:8501


app.add_middleware(
CORSMiddleware,
allow_origins=ALLOWED_ORIGINS,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


# OAuth state/nonce 저장용 세션
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET, same_site="lax")


# OAuth 설정
oauth = OAuth()
oauth.register(
name="google",
client_id=GOOGLE_CLIENT_ID,
client_secret=GOOGLE_CLIENT_SECRET,
server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
client_kwargs={"scope": "openid email profile"},
)


# JWT 의존성
security = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"result_url": PLACEHOLDER_IMAGE}
    except PyJWTError:


payload = {
"sub": sub,
"email": email,
"name": name,
"iss": "adgen-api",
"iat": int(datetime.now().timestamp()),
"exp": int(datetime.now().timestamp()) + 7200, # 2시간
}
app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")


target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
return RedirectResponse(url=target)
except Exception:
print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
return JSONResponse({"error": "OAuth callback failed"}, status_code=500)


# 내 정보 보기 (토큰 검사)
@app.get("/me")
async def me(user=Depends(get_current_user)):
return user


# (선택) 로그아웃 엔드포인트 — 확장 대비
@app.post("/auth/logout")
async def logout(response: Response):
# 서버 세션/쿠키를 쓰는 구조로 확장 시 여기서 정리
return {"ok": True}


# ---------------------------------------------------------
# 아래는 프론트 데모용 스텁 엔드포인트들
# → 실제 로직으로 교체해서 사용하세요.
# 모두 인증 보호 예시로 Depends(get_current_user) 추가
# ---------------------------------------------------------


PLACEHOLDER_IMAGE = "https://via.placeholder.com/1024"


@app.post("/generate_text_suggestions")
async def generate_text_suggestions(
base_line: str = Form(...), n: int = Form(5), user=Depends(get_current_user)
):
base_line = base_line.strip()
if not base_line:
return JSONResponse({"error": "base_line required"}, status_code=400)
texts = [f"{base_line} — 변형 {i+1}" for i in range(max(1, min(n, 10)))]
return {"texts": texts}


@app.post("/generate_ai_image")
async def generate_ai_image(
ad_text: str = Form(...), size: str = Form("1024x1024"), user=Depends(get_current_user)
):
# 실제 이미지 생성 대신 플레이스홀더 URL 반환
return {"image_url": PLACEHOLDER_IMAGE, "size": size}


@app.post("/generate_poster_from_text")
async def generate_poster_from_text(
ad_text: str = Form(...), size: str = Form("1024x1024"), user=Depends(get_current_user)
):
return {"result_url": PLACEHOLDER_IMAGE, "size": size}


@app.post("/compose_with_image_url")
async def compose_with_image_url(
image_url: str = Form(...), ad_text: str = Form(...), user=Depends(get_current_user)
):
return {"result_url": image_url}


@app.post("/compose_with_upload")
async def compose_with_upload(
file: UploadFile = File(...), ad_text: str = Form(...), user=Depends(get_current_user)
):
# 업로드 파일을 실제로 저장/가공하지는 않고, 데모 응답만 반환
return {"result_url": PLACEHOLDER_IMAGE}