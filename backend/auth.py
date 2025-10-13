# backend/routes/auth.py
import os
import jwt
import bcrypt
import sqlite3
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request as StarletteRequest
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# 환경
# ---------------------------------------------------------------------
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

HAS_NAVER = bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET and NAVER_REDIRECT_URI)
HAS_KAKAO = bool(KAKAO_CLIENT_ID and KAKAO_REDIRECT_URI)

# ---------------------------------------------------------------------
# 로컬 사용자 저장소
# ---------------------------------------------------------------------
DB_PATH = os.path.join("data", "images", "adgen.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_user_table():
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
_init_user_table()

# ---------------------------------------------------------------------
# JWT / 보안
# ---------------------------------------------------------------------
security = HTTPBearer(auto_error=False)

def _issue_token(sub: str, email: str, name: str, provider: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "provider": provider,
        "iss": "adgen-api",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

# ---------------------------------------------------------------------
# OAuth 클라이언트
# ---------------------------------------------------------------------
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수가 필요합니다.")

oauth = OAuth()
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

# ---------------------------------------------------------------------
# 공용: 로고 data-URI (프론트와 동일 후보 경로)
# ---------------------------------------------------------------------
def _find_logo_path() -> Path | None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in [
        here / "data/images/ai_team2_logo.png",
        repo / "data/images/ai_team2_logo.png",
        here / "data/images/logo.png",
        repo / "data/images/logo.png",
        Path("data/images/ai_team2_logo.png").resolve(),
        Path("data/images/logo.png").resolve(),
    ]:
        if p.exists():
            return p
    return None

def _logo_data_uri() -> str:
    p = _find_logo_path()
    if not p:
        return ""
    ext = p.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/{ext};base64,{b64}"

# ---------------------------------------------------------------------
# 헬퍼: 팝업 닫고 원탭(top) 갱신
# ---------------------------------------------------------------------
def _close_popup_with_token(url: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><title>Login Completed</title>
<script>
(function () {{
  var target = {url!r};
  try {{
    var op = window.opener;
    var topWin = null;
    if (op) {{
      try {{ topWin = op.top || op; }} catch(e) {{}}
    }}
    if (topWin) {{
      try {{ topWin.location.assign(target); }} catch(e) {{ topWin.location = target; }}
      window.close();
      return;
    }}
    window.location.replace(target);
  }} catch(e) {{
    window.location.href = target;
  }}
}})();
</script>
<p>로그인 완료. 창이 자동으로 닫히지 않으면 <a href="{url}">여기</a>를 클릭하세요.</p>""")

# ---------------------------------------------------------------------
# 헬스/설정
# ---------------------------------------------------------------------
@router.get("/enabled")
async def auth_enabled():
    return {"google": True, "naver": HAS_NAVER, "kakao": HAS_KAKAO}

# ---------------------------------------------------------------------
# 회원가입(팝업) — 홈과 동일 톤/레이아웃, 필드: 이름/아이디/비밀번호
# ---------------------------------------------------------------------
@router.get("/signup_page", response_class=HTMLResponse)
async def signup_page():
    logo_uri = _logo_data_uri()
    return f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>회원가입</title>
  <style>
    :root {{
      --bg: #ffffff;
      --fg: #1f1f2e;
      --muted: rgba(49,51,63,.6);
      --border: rgba(49,51,63,.2);
      --border-hover: rgba(49,51,63,.3);
      --input-bg: #f3f4f8;
    }}
    html,body {{
      margin:0; padding:0; background:var(--bg); color:var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR",
                   Helvetica, Arial, "Apple SD Gothic Neo", "Malgun Gothic", "맑은 고딕",
                   "Noto Sans", "Liberation Sans", sans-serif;
    }}
    .wrap {{ max-width:560px; margin:40px auto; padding:0 16px; }}
    .logo {{ display:block; margin:0 auto 12px; width:140px; height:auto; border-radius:12px; }}
    h2 {{ text-align:center; font-weight:800; font-size:28px; margin:8px 0 18px; }}
    label {{ display:block; font-size:14px; margin:14px 2px 6px; color:var(--muted); }}
    input {{
      width:100%; height:44px; border-radius:10px; border:1px solid var(--border);
      background:var(--input-bg); outline:none; padding:0 12px; font-size:15px;
    }}
    input:focus {{ border-color:var(--border-hover); background:#fff; box-shadow:0 0 0 2px rgba(48,115,240,.12) inset; }}
    button {{
      width:100%; height:44px; border-radius:10px; border:1px solid var(--border);
      background:#f6f6f9; font-weight:700; cursor:pointer; margin-top:18px;
      transition:background .15s, border-color .15s, transform .02s;
    }}
    button:hover {{ background:#f0f2f6; border-color:var(--border-hover); }}
    button:active {{ transform:translateY(1px); }}
    .msg {{ color:#c00; min-height:20px; margin-top:8px; font-size:14px; }}
    .footer {{ text-align:center; margin-top:8px; font-size:13px; color:var(--muted); }}
  </style>
</head>
<body>
  <div class="wrap">
    {"<img class='logo' src='"+logo_uri+"' alt='logo'/>" if logo_uri else ""}
    <h2>회원가입</h2>

    <label for="name">이름</label>
    <input id="name" placeholder="이름"/>

    <label for="uid">아이디</label>
    <input id="uid" placeholder="아이디"/>

    <label for="pw">비밀번호</label>
    <input id="pw" type="password" placeholder="비밀번호"/>

    <button id="ok">완료</button>
    <div id="msg" class="msg"></div>
    <div class="footer">완료 후 창이 닫히며 원래 탭으로 돌아갑니다.</div>
  </div>

  <script>
  const $ = (id) => document.getElementById(id);
  const nameEl = $("name"), idEl = $("uid"), pwEl = $("pw"), msg = $("msg");

  async function go() {{
    const name = (nameEl.value||"").trim();
    const uid  = (idEl.value||"").trim();      // UI: 아이디
    const pw   = pwEl.value || "";
    if (!name || !uid || !pw) {{
      msg.textContent = "모든 항목을 입력해주세요.";
      return;
    }}
    try {{
      // 백엔드는 email 키를 사용 → uid를 email로 매핑
      const r = await fetch('/auth/signup', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{name, email: uid, password: pw}})
      }});
      if (!r.ok) throw new Error("SIGNUP_FAIL");
      const js = await r.json();

      // 원탭 이동 + 팝업 닫기
      const u = new URL('{FRONTEND_URL}');
      u.searchParams.set('token', js.token);
      u.searchParams.set('name', js.user?.name || name);
      u.searchParams.set('email', js.user?.email || uid);

      try {{
        if (window.opener && !window.opener.closed) {{
          (window.opener.top || window.opener).location = u.href;
          window.close();
        }} else {{
          location = u.href;
        }}
      }} catch(e) {{
        location = u.href;
      }}
    }} catch(e) {{
      msg.textContent = "회원가입 실패";
    }}
  }}

  $("ok").addEventListener("click", go);
  [nameEl, idEl, pwEl].forEach(el => el.addEventListener("keydown", (ev) => {{
    if (ev.key === "Enter") go();
  }}));
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------
# 로컬 회원가입/로그인
# ---------------------------------------------------------------------
@router.post("/signup")
async def signup(payload: dict):
    # 아이디 또는 이메일 어떤 키로 와도 받기
    identifier = (payload.get("email") or payload.get("id") or "").strip()
    password = payload.get("password") or ""
    # 이메일처럼 보일 때만 소문자 정규화
    norm_id = identifier.lower() if "@" in identifier else identifier
    name = (payload.get("name") or "").strip() or (norm_id.split("@")[0] if "@" in norm_id else norm_id)
    if not norm_id or not password:
        raise HTTPException(400, "id/email and password required")

    with _db() as conn:
        cur = conn.execute("SELECT 1 FROM users WHERE email = ?", (norm_id,))
        if cur.fetchone():
            raise HTTPException(409, "id/email already exists")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO users(email, name, password_hash) VALUES(?,?,?)", (norm_id, name, pw_hash))

    token = _issue_token(sub=norm_id, email=norm_id, name=name, provider="local")
    return {"token": token, "user": {"email": norm_id, "name": name}}

@router.post("/login")
async def login(payload: dict):
    identifier = (payload.get("email") or payload.get("id") or "").strip()
    password = payload.get("password") or ""
    norm_id = identifier.lower() if "@" in identifier else identifier
    if not norm_id or not password:
        raise HTTPException(400, "id/email and password required")

    with _db() as conn:
        cur = conn.execute("SELECT id, name, password_hash FROM users WHERE email = ?", (norm_id,))
        row = cur.fetchone()
    if not row or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "invalid credentials")

    token = _issue_token(sub=str(row["id"]), email=norm_id, name=row["name"], provider="local")
    return {"token": token, "user": {"email": norm_id, "name": row["name"]}}

# ---------------------------------------------------------------------
# Google / Naver / Kakao OAuth — 콜백에서 팝업 닫기
# ---------------------------------------------------------------------
@router.get("/google/login")
async def google_login(request: StarletteRequest):
    return await oauth.google.authorize_redirect(request, request.url_for("google_callback"))

@router.head("/google/login")
async def google_login_head():
    return PlainTextResponse("", status_code=200)

@router.get("/google/callback")
async def google_callback(request: StarletteRequest):
    try:
        token = await oauth.google.authorize_access_token(request)
        info = token.get("userinfo") or {}
        if "email" not in info:
            raise HTTPException(400, "Google OAuth failed")
        app_jwt = _issue_token(sub=info.get("sub", ""), email=info["email"], name=info.get("name", ""), provider="google")
        url = f"{FRONTEND_URL}/?token={app_jwt}&name={info.get('name','')}&email={info['email']}"
        return _close_popup_with_token(url)
    except Exception:
        print("GOOGLE CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "OAuth callback failed"}, status_code=500)

@router.get("/naver/login")
async def naver_login(request: StarletteRequest):
    if not HAS_NAVER:
        raise HTTPException(501, "Naver OAuth not configured")
    return await oauth.naver.authorize_redirect(request, NAVER_REDIRECT_URI)

@router.get("/naver/callback")
async def naver_callback(request: StarletteRequest):
    try:
        token = await oauth.naver.authorize_access_token(request)
        resp = await oauth.naver.get("nid/me", token=token)
        data = (resp.json() if resp else {}).get("response", {})
        sub = data.get("id")
        email = data.get("email") or f"{sub}@naver-user.local"
        name = data.get("name") or data.get("nickname") or "NaverUser"
        app_jwt = _issue_token(sub=sub or email, email=email, name=name, provider="naver")
        url = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return _close_popup_with_token(url)
    except Exception:
        print("NAVER CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Naver OAuth callback failed"}, status_code=500)

@router.get("/kakao/login")
async def kakao_login(request: StarletteRequest):
    if not HAS_KAKAO:
        raise HTTPException(501, "Kakao OAuth not configured")
    return await oauth.kakao.authorize_redirect(request, KAKAO_REDIRECT_URI, scope="profile_nickname")

@router.get("/kakao/callback")
async def kakao_callback(request: StarletteRequest):
    try:
        token = await oauth.kakao.authorize_access_token(request)
        resp = await oauth.kakao.get("v2/user/me", token=token)
        info = resp.json() if resp else {}
        kid = str(info.get("id", ""))
        acc = info.get("kakao_account") or {}
        name = (acc.get("profile") or {}).get("nickname") or "KakaoUser"
        email = acc.get("email") or f"{kid}@kakao-user.local"
        app_jwt = _issue_token(sub=kid or email, email=email, name=name, provider="kakao")
        url = f"{FRONTEND_URL}/?token={app_jwt}&name={name}&email={email}"
        return _close_popup_with_token(url)
    except Exception:
        print("KAKAO CALLBACK ERROR:\n", traceback.format_exc())
        return JSONResponse({"error": "Kakao OAuth callback failed"}, status_code=500)

# ---------------------------------------------------------------------
# 토큰 검증
# ---------------------------------------------------------------------
@router.get("/me")
async def auth_me(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        return JSONResponse({"detail": "Missing token"}, status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGORITHM], leeway=10)
        return {"email": payload.get("email"), "name": payload.get("name"), "provider": payload.get("provider", "google")}
    except Exception:
        return JSONResponse({"detail": "Invalid token"}, status_code=status.HTTP_401_UNAUTHORIZED)
