# --- 백엔드 전용 main.py (Streamlit 없음) ---
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Response, Query, Request as FastapiRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request as StarletteRequest
from starlette.middleware.sessions import SessionMiddleware

from pydantic import BaseModel, EmailStr

import os, jwt, secrets, hashlib, base64, json, pathlib, time, re, logging
import requests as pyrequests
from jwt import PyJWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse, urlencode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from openai import OpenAI

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from passlib.hash import bcrypt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adgen")

# --- env ---
load_dotenv()
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET           = os.getenv("JWT_SECRET", "dev-secret")
SESSION_SECRET       = os.getenv("SESSION_SECRET", "dev-session-secret")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:8501")
BACKEND_URL          = os.getenv("BACKEND_URL", "http://localhost:8000")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")
OPENAI_TEXT_MODEL    = os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini")
OPENAI_IMAGE_MODEL   = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
DATABASE_URL         = os.getenv("DATABASE_URL", "sqlite:///./adgen.db")
AUTH_TOKEN_DELIVERY  = os.getenv("AUTH_TOKEN_DELIVERY", "query").lower().strip()  # query | cookie

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 를 .env에 설정하세요.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 를 .env에 설정하세요.")

# --- app ---
app = FastAPI(title="AdGen OpenAI Backend", version="3.4")

_front = urlparse(FRONTEND_URL)
ALLOWED_ORIGINS = {
    f"{_front.scheme}://{_front.netloc}",
    "http://localhost:8501", "http://127.0.0.1:8501",
    "http://localhost:3000", "http://127.0.0.1:3000",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 8,
)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

security = HTTPBearer(auto_error=False)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --- DB ---
_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if _is_sqlite else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AdRecord(Base):
    __tablename__ = "ad_records"
    id         = Column(Integer, primary_key=True, index=True)
    user_sub   = Column(String(128), index=True, nullable=False)
    user_email = Column(String(256), index=True, nullable=False)
    kind       = Column(String(32), nullable=False)
    ad_text    = Column(Text, nullable=False)
    size       = Column(String(32), default="1024x1024")
    quality    = Column(String(16), default="standard")
    style      = Column(String(16), default="vivid")
    file_path  = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class LocalUser(Base):
    __tablename__ = "local_users"
    __table_args__ = (UniqueConstraint("email", name="uq_local_users_email"),)
    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(256), nullable=False, index=True)
    name       = Column(String(128), default="")
    password   = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    pathlib.Path("./data").mkdir(exist_ok=True)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- JWT ---
def create_jwt(payload: dict, minutes: int = 120) -> str:
    to_encode = payload.copy()
    to_encode["iat"] = int(datetime.utcnow().timestamp())
    to_encode["exp"] = int((datetime.utcnow() + timedelta(minutes=minutes)).timestamp())
    to_encode["iss"] = "adgen-api"
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    request: FastapiRequest = None
):
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    if not token and AUTH_TOKEN_DELIVERY == "cookie" and request:
        token = request.cookies.get("adgen_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    payload = verify_jwt(token)
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
        "provider": payload.get("provider", "google"),
    }

# --- health ---
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z", "auth_mode": AUTH_TOKEN_DELIVERY}

# --- DALL·E helpers ---
DALLE3_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
DALLE3_QUALITIES = {"standard", "hd"}
DALLE3_STYLES = {"vivid", "natural"}

def _normalize_dalle3_size(size: str) -> str:
    s = (size or "1024x1024").lower()
    if s in DALLE3_SIZES: return s
    if s == "1536x1024": return "1792x1024"
    if s == "1024x1536": return "1024x1792"
    return "1024x1024"

def _norm_quality(q: str) -> str:
    q = (q or "standard").lower()
    return q if q in DALLE3_QUALITIES else "standard"

def _norm_style(s: str) -> str:
    s = (s or "vivid").lower()
    return s if s in DALLE3_STYLES else "vivid"

def _to_data_url_from_b64(b64_png: str) -> str:
    return f"data:image/png;base64,{b64_png}"

# --- OAuth (Google, PKCE) ---
@app.get("/auth/google/login")
async def google_login(request: StarletteRequest):
    # 현재 요청 호스트/스킴을 그대로 사용해 콜백 구성
    redirect_uri = str(request.url_for("google_callback"))
    logger.info(f"[OAuth] redirect_uri -> {redirect_uri}")
    logger.info(f"[OAuth] client_id   -> {GOOGLE_CLIENT_ID}")

    code_verifier  = secrets.token_urlsafe(64)
    digest         = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    request.session["pkce_code_verifier"] = code_verifier

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

@app.get("/auth/google/callback", name="google_callback")
async def google_callback(request: StarletteRequest):
    try:
        code_verifier = request.session.get("pkce_code_verifier")
        if not code_verifier:
            return RedirectResponse(url=f"{BACKEND_URL}/auth/google/login")
        token = await oauth.google.authorize_access_token(request, code_verifier=code_verifier)
        request.session.pop("pkce_code_verifier", None)

        userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)
        if not userinfo or "email" not in userinfo:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        sub     = userinfo.get("sub")
        email   = userinfo.get("email")
        name    = userinfo.get("name") or ""
        picture = userinfo.get("picture") or ""

        app_jwt = create_jwt({
            "sub": sub, "email": email, "name": name, "picture": picture,
            "provider": "google", "type": "access",
        }, minutes=720)

        if AUTH_TOKEN_DELIVERY == "cookie":
            target = f"{FRONTEND_URL}/welcome"
            resp = RedirectResponse(url=target)
            resp.set_cookie(key="adgen_token", value=app_jwt, httponly=True, secure=False, samesite="lax", max_age=60*60*12)
            return resp
        else:
            query  = urlencode({"token": app_jwt, "name": name, "email": email})
            target = f"{FRONTEND_URL}/?{query}"
            return RedirectResponse(url=target)

    except Exception as e:
        import traceback as tb
        logger.exception("OAuth callback failed: %s", e)
        return JSONResponse({"error":"OAuth callback failed","type":type(e).__name__,"message":str(e),"trace":tb.format_exc()}, status_code=500)

# --- Local Auth ---
class SignupBody(BaseModel):
    email: EmailStr
    password: str
    name: str | None = ""

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@app.post("/auth/signup")
def signup(body: SignupBody, db: Session = Depends(get_db)):
    exists = db.query(LocalUser).filter(LocalUser.email == body.email).first()
    if exists: raise HTTPException(status_code=400, detail="Email already registered")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 chars")
    hashed = bcrypt.hash(body.password)
    user = LocalUser(email=body.email, name=(body.name or "").strip(), password=hashed)
    db.add(user); db.commit(); db.refresh(user)
    token = create_jwt({"sub": f"local:{user.id}","email": user.email,"name": user.name or "","provider": "local","type": "access"}, minutes=720)
    return {"ok": True, "token": token, "email": user.email, "name": user.name, "provider": "local"}

@app.post("/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(LocalUser).filter(LocalUser.email == body.email).first()
    if not user or not bcrypt.verify(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_jwt({"sub": f"local:{user.id}","email": user.email,"name": user.name or "","provider": "local","type": "access"}, minutes=720)
    return {"ok": True, "token": token, "email": user.email, "name": user.name, "provider": "local"}

@app.post("/auth/logout")
def logout(response: Response):
    if AUTH_TOKEN_DELIVERY == "cookie":
        response.delete_cookie("adgen_token")
    return {"ok": True}

@app.get("/auth/providers")
def providers():
    return {"providers": ["google", "local"], "delivery": AUTH_TOKEN_DELIVERY}

# --- OpenAI: Text ---
@app.post("/generate_text_suggestions")
async def generate_text_suggestions(
    base_line: str = Form(...), n: int = Form(6), user=Depends(get_current_user),
):
    base = base_line.strip()
    n = max(1, min(int(n), 10))
    try:
        prompt = (
            "You are an expert Korean advertising copywriter.\n"
            f"Given the input line below, produce {n} short, punchy variations in Korean.\n"
            "- Keep each variant between 7 and 30 Korean characters.\n"
            "- Avoid emojis and punctuation overload.\n"
            "- No duplicates or near-duplicates.\n"
            '- Output ONLY valid JSON in the exact schema: { \"variants\": [\"...\", \"...\"] }\n\n'
            f"INPUT: {base}"
        )
        resp = openai_client.chat.completions.create(
            model=OPENAI_TEXT_MODEL,
            messages=[{"role":"system","content":"Respond only with valid JSON. Do not add any extra text."},
                      {"role":"user","content":prompt}],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        try:
            data = json.loads(content)
            texts = data.get("variants", [])
        except Exception:
            texts = [base]
        if not isinstance(texts, list) or not texts: texts = [base]
        return {"texts": texts[:n]}
    except Exception as e:
        return JSONResponse({"error": f"OpenAI text error: {e}"}, status_code=500)

# --- file utils ---
def _fs_safe(s: str) -> str:
    s = (s or "anon").replace(":", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:64]

def _ensure_user_dir(sub: str) -> pathlib.Path:
    safe = _fs_safe(sub)
    p = pathlib.Path("./data") / safe
    p.mkdir(parents=True, exist_ok=True)
    return p

def _save_data_url_png(data_url: str, user_sub: str, prefix: str) -> str:
    if not data_url.startswith("data:image"):
        raise ValueError("not a data URL")
    b64 = data_url.split(",", 1)[1]
    raw = base64.b64decode(b64)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = _ensure_user_dir(user_sub)
    path = out_dir / f"{prefix}_{ts}.png"
    with open(path, "wb") as f:
        f.write(raw)
    return str(path.resolve())

def _persist_ad(db: Session, user: dict, *, kind: str, ad_text: str,
                data_url_png: str, size: str = "1024x1024",
                quality: str = "standard", style: str = "vivid") -> int:
    file_path = _save_data_url_png(data_url_png, user["sub"], kind)
    rec = AdRecord(user_sub=user["sub"], user_email=user["email"], kind=kind,
                   ad_text=ad_text, size=size, quality=quality, style=style, file_path=file_path)
    db.add(rec); db.commit(); db.refresh(rec)
    return rec.id

# --- OpenAI: Image ---
@app.post("/generate_ai_image")
async def generate_ai_image(
    ad_text: str = Form(...), size: str = Form("1024x1024"), quality: str = Form("standard"),
    style: str = Form("vivid"), user=Depends(get_current_user),
):
    try:
        size = _normalize_dalle3_size(size); quality = _norm_quality(quality); style = _norm_style(style)
        img = openai_client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=("A clean, modern advertising visual for the Korean copy below.\n"
                    "Soft gradient background, minimal composition, high readability.\n"
                    f"Copy (in Korean): {ad_text}"),
            size=size, n=1, quality=quality, style=style, response_format="b64_json",
        )
        b64 = img.data[0].b64_json
        data_url = _to_data_url_from_b64(b64)
        try:
            with SessionLocal() as db:
                _persist_ad(db, user, kind="ai_image", ad_text=ad_text,
                            data_url_png=data_url, size=size, quality=quality, style=style)
        except Exception:
            pass
        return {"image_url": data_url, "size": size}
    except Exception as e:
        return JSONResponse({"error": f"DALL·E 3 image error: {e}"}, status_code=500)

@app.post("/generate_poster_from_text")
async def generate_poster_from_text(
    ad_text: str = Form(...), size: str = Form("1024x1024"),
    quality: str = Form("standard"), style: str = Form("vivid"),
    user=Depends(get_current_user),
):
    try:
        size = _normalize_dalle3_size(size); quality = _norm_quality(quality); style = _norm_style(style)
        img = openai_client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=("Design a clean Korean poster with the given copy centered on a rounded white card, "
                    "soft gradient background, minimal layout, high legibility Korean typography. "
                    f"Copy: {ad_text}"),
            size=size, n=1, quality=quality, style=style, response_format="b64_json",
        )
        b64 = img.data[0].b64_json
        data_url = _to_data_url_from_b64(b64)
        try:
            with SessionLocal() as db:
                _persist_ad(db, user, kind="poster", ad_text=ad_text,
                            data_url_png=data_url, size=size, quality=quality, style=style)
        except Exception:
            pass
        return {"result_url": data_url, "size": size}
    except Exception as e:
        return JSONResponse({"error": f"DALL·E 3 poster error: {e}"}, status_code=500)

# --- compose (upload/url) ---
def _load_font(font_size: int):
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/NanumGothic.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, font_size)
            except Exception: pass
    return ImageFont.load_default()

def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int):
    words = list(text); lines, line = [], ""
    for ch in words:
        test = line + ch
        w, _ = draw.textsize(test, font=font)
        if w <= max_w: line = test
        else: lines.append(line); line = ch
    if line: lines.append(line)
    return lines

def _compose_with_canvas(bg: Image.Image, ad_text: str):
    w, h = bg.size
    draw = ImageDraw.Draw(bg)
    font = _load_font(int(min(w, h) * 0.06))
    max_w = int(w * 0.9)
    lines = _wrap_text(draw, ad_text, font, max_w)
    y = int(h * 0.1)
    for line in lines[:10]:
        tw, th = draw.textsize(line, font=font)
        x = (w - tw) // 2
        draw.text((x, y), line, fill=(20, 30, 40), font=font)
        y += int(th * 1.15)
    buf = BytesIO(); bg.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

class ComposeUrlBody(BaseModel):
    image_url: str
    ad_text: str

@app.post("/compose_with_image_url")
async def compose_with_image_url(
    body: ComposeUrlBody | None = None, image_url: str | None = Form(None),
    ad_text: str | None = Form(None), user=Depends(get_current_user),
):
    try:
        if body: image_url, ad_text = body.image_url, body.ad_text
        if not image_url or not ad_text:
            return JSONResponse({"error": "image_url and ad_text are required"}, status_code=400)
        if image_url.startswith("data:image/"):
            header, b64 = image_url.split(",", 1)
            bg = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
        else:
            r = pyrequests.get(image_url, timeout=10); r.raise_for_status()
            bg = Image.open(BytesIO(r.content)).convert("RGB")
        result = _compose_with_canvas(bg, ad_text)
        try:
            with SessionLocal() as db:
                _persist_ad(db, user, kind="compose_url", ad_text=ad_text, data_url_png=result)
        except Exception: pass
        return {"result_url": result}
    except Exception as e:
        return JSONResponse({"error": f"compose error: {e}"}, status_code=400)

MAX_UPLOAD_MB = 8
ALLOWED_UPLOAD_MIME = {"image/png", "image/jpeg", "image/webp"}

@app.post("/compose_with_upload")
async def compose_with_upload(
    request: StarletteRequest, file: UploadFile = File(...), ad_text: str = Form(...),
    user=Depends(get_current_user),
):
    try:
        clen = int(request.headers.get("Content-Length", "0"))
        if clen > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"File too large (>{MAX_UPLOAD_MB}MB)")
    except ValueError:
        pass

    if file.content_type not in ALLOWED_UPLOAD_MIME:
        raise HTTPException(400, "Only PNG/JPEG/WEBP allowed")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large (>{MAX_UPLOAD_MB}MB)")

    try:
        bg = Image.open(BytesIO(content)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Invalid image")

    result = _compose_with_canvas(bg, ad_text)
    try:
        with SessionLocal() as db:
            _persist_ad(db, user, kind="compose_upload", ad_text=ad_text, data_url_png=result)
    except Exception: pass
    return {"result_url": result}

# --- history ---
@app.get("/ads")
def list_my_ads(
    limit: int = Query(20, ge=1, le=100),
    include_orphans: bool = Query(False, description="파일이 없는 레코드도 포함할지 여부"),
    db: Session = Depends(get_db), user=Depends(get_current_user),
):
    q = (db.query(AdRecord)
         .filter(AdRecord.user_sub == user["sub"])
         .order_by(AdRecord.created_at.desc())
         .limit(limit).all())
    items = []
    for r in q:
        data_url = None
        if r.file_path and os.path.exists(r.file_path):
            try:
                with open(r.file_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                data_url = f"data:image/png;base64,{b64}"
            except Exception:
                data_url = None
        if not include_orphans and data_url is None:
            continue
        items.append({
            "id": r.id, "created_at": r.created_at.isoformat() + "Z",
            "kind": r.kind, "ad_text": r.ad_text, "size": r.size,
            "quality": r.quality, "style": r.style, "data_url": data_url,
        })
    return {"items": items}

@app.delete("/ads/{ad_id}")
def delete_my_ad(ad_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rec = db.query(AdRecord).filter(AdRecord.id == ad_id, AdRecord.user_sub == user["sub"]).first()
    if not rec: raise HTTPException(status_code=404, detail="Not found")
    try:
        if rec.file_path and os.path.exists(rec.file_path): os.remove(rec.file_path)
    except Exception: pass
    db.delete(rec); db.commit()
    return {"ok": True}

@app.delete("/ads")
def bulk_delete_ads(ids: str = Query(..., description="comma-separated ids"),
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not id_list: raise HTTPException(status_code=400, detail="No valid ids")
    rows = (db.query(AdRecord)
              .filter(AdRecord.user_sub == user["sub"], AdRecord.id.in_(id_list))
              .all())
    count = 0
    for rec in rows:
        try:
            if rec.file_path and os.path.exists(rec.file_path): os.remove(rec.file_path)
        except Exception: pass
        db.delete(rec); count += 1
    db.commit()
    return {"ok": True, "deleted": count}

@app.get("/me")
async def me(user=Depends(get_current_user)):
    return {"user": user}
