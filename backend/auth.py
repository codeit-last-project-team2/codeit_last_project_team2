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

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

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
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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

@router.get("/auth/google/login")
async def login(request: StarletteRequest):
    redirect_uri = request.url_for("auth_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

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

        payload = {
            "sub": sub,
            "email": email,
            "name": name,
            "iss": "adgen-api",
            "iat": int(datetime.now().timestamp()),
            "exp": int(datetime.now().timestamp()) + 7200,
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        target = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return RedirectResponse(url=target)
    except Exception:
        print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "OAuth callback failed"}, status_code=500)

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user

@router.post("/auth/logout")
async def logout(response: Response):
    return {"ok": True}