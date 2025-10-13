import os
import glob
import base64
import requests
import streamlit as st
from pathlib import Path

BACKEND_URL = "http://localhost:8000"

# 로그인 전 사이드바 접기
st.set_page_config(initial_sidebar_state="collapsed")

# ---------------- 로고 탐색 ----------------
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

LOGO_PATH = _find_logo_path()

def _logo_html() -> str:
    p = LOGO_PATH
    if not p or not p.exists():
        return ""
    ext = p.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{ext};base64,{b64}" style="display:block;margin:0 auto;width:140px;height:auto;border-radius:12px;" />'

# ---------------- 쿼리파라미터/세션 ----------------
params = st.query_params
def _qp(k):
    v = params.get(k)
    return v[0] if isinstance(v, list) else v

for k in ["token", "user_name", "user_email", "provider"]:
    st.session_state.setdefault(k, None)

# ---------------- 서버 상태 ----------------
def _get_enabled_providers():
    try:
        r = requests.get(f"{BACKEND_URL}/auth/enabled", timeout=10)
        if r.status_code == 200:
            js = r.json()
            return {
                "google": bool(js.get("google", True)),
                "naver":  bool(js.get("naver",  True)),
                "kakao":  bool(js.get("kakao",  True)),
            }
    except Exception:
        pass
    return {"google": True, "naver": True, "kakao": True}

ENABLED = _get_enabled_providers()

def _verify_and_fill(token: str) -> bool:
    try:
        me = requests.get(
            f"{BACKEND_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if me.status_code != 200:
            return False
        data = me.json()
        st.session_state.user_name  = st.session_state.user_name  or data.get("name")  or ""
        st.session_state.user_email = st.session_state.user_email or data.get("email") or ""
        st.session_state.provider   = data.get("provider") or st.session_state.get("provider")
        return True
    except Exception:
        return False

# ------------ 콜백 처리(같은 탭/팝업 모두 대응) ------------
tok = _qp("token")
if tok:
    st.session_state.token      = tok
    st.session_state.user_name  = _qp("name")  or st.session_state.user_name  or ""
    st.session_state.user_email = _qp("email") or st.session_state.user_email or ""
    _verify_and_fill(tok)
    try:
        st.query_params.clear()
    except Exception:
        pass

def _logout():
    for k in ["token", "user_name", "user_email", "provider"]:
        st.session_state[k] = None
    st.rerun()

if st.session_state.get("token") and not st.session_state.get("user_email"):
    if not _verify_and_fill(st.session_state["token"]):
        st.warning("세션이 만료되었거나 토큰 검증에 실패했어요. 다시 로그인해주세요.")
        _logout()

# ---------------- 로그인 영역 ----------------
if st.session_state.get("token"):
    colA, colB = st.columns([3, 1], gap="small")
    with colA:
        via = f" via {st.session_state.provider}" if st.session_state.get("provider") else ""
        st.success(f"✅ 로그인됨: {st.session_state.user_name} ({st.session_state.user_email}){via}")
    with colB:
        if st.button("로그아웃", use_container_width=True):
            _logout()
else:
    # 사이드바 숨김
    st.markdown('<style>[data-testid="stSidebar"]{display:none !important;}</style>', unsafe_allow_html=True)

    # 로고 & 제목
    _l, _c, _r = st.columns([1, 3, 1])
    with _c:
        html = _logo_html()
        if html:
            st.markdown(html, unsafe_allow_html=True)

    # 제목 옆 앵커(🔗) 숨기기 + 여백
    st.markdown("""
    <style>
      .hero h2 a { display: none !important; }
      .hero h2 { margin-top: 8px !important; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='hero'><h2 style='text-align:center;font-weight:800;'>광고 제작 서비스</h2></div>", unsafe_allow_html=True)

    # ✅ 전역: Streamlit 버튼(로그인)만 통일
    st.markdown("""
    <style>
      div.stButton > button {
        width: 100%;
        height: 48px;
        padding: 0 16px;
        border-radius: 10px;
        border: 1px solid rgba(49,51,63,.18);
        background: #ffffff;
        color: rgba(49,51,63,.82);
        font-size: 15px;
        font-weight: 500;
        letter-spacing: .1px;
        cursor: pointer;
        display: inline-flex; align-items: center; justify-content: center;
        transition: background .15s, border-color .15s, transform .02s, box-shadow .15s;
        box-shadow: none !important;
      }
      div.stButton > button:hover { background:#f7f8fb; border-color: rgba(49,51,63,.28); }
      div.stButton > button:active { transform: translateY(1px); }
      div.stButton > button:focus-visible { outline:none; box-shadow:0 0 0 2px rgba(48,115,240,.14) !important; }
    </style>
    """, unsafe_allow_html=True)

    # 로그인 폼
    _l2, _c2, _r2 = st.columns([1, 3, 1])
    with _c2:
        email = st.text_input("아이디", key="login_id", placeholder="아이디")
        pw = st.text_input("비밀번호", key="login_pw", placeholder="비밀번호", type="password")
        if st.button("로그인", use_container_width=True, key="btn_login"):
            if not email or not pw:
                st.warning("아이디와 비밀번호를 입력해주세요.")
            else:
                try:
                    r = requests.post(
                        f"{BACKEND_URL}/auth/login",
                        json={"email": email.strip(), "password": pw},  # 서버에선 email 필드로 받지만 문자열이면 OK
                        timeout=8,
                    )
                    r.raise_for_status()
                    js = r.json()
                    st.session_state.token = js["token"]
                    st.session_state.user_email = js["user"]["email"]
                    st.session_state.user_name = js["user"].get("name") or ""
                    st.session_state.provider = "local"
                    st.success("로그인 성공!")
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 실패: {e}")

        # --- 회원가입: 팝업(iFrame 내부 CSS로 스타일 동일화) ---
        signup_html = f"""
        <style>
          .btn-like {{
            width: 100%; height: 48px; padding: 0 16px;
            border-radius: 10px; border: 1px solid rgba(49,51,63,.18);
            background: #ffffff; color: rgba(49,51,63,.82);
            font-size: 15px; font-weight: 500; letter-spacing: .1px;
            cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
            transition: background .15s, border-color .15s, transform .02s, box-shadow .15s;
            margin-top: 12px; margin-bottom: 18px;
          }}
          .btn-like:hover {{ background:#f7f8fb; border-color: rgba(49,51,63,.28); }}
          .btn-like:active {{ transform: translateY(1px); }}
          .btn-like:focus-visible {{ outline:none; box-shadow:0 0 0 2px rgba(48,115,240,.14); }}
        </style>
        <button id="btn-signup" class="btn-like">회원가입</button>
        <script>
        (function() {{
          function openSignup() {{
            const W = window.top || window;
            const w = 520, h = 640;
            const y = (W.outerHeight/2 + W.screenY) - (h/2);
            const x = (W.outerWidth/2  + W.screenX) - (w/2);
            const feat = "popup=yes,width="+w+",height="+h+",left="+x+",top="+y+",noopener=no,noreferrer=no";
            const pop = W.open("{BACKEND_URL}/auth/signup_page", "signup_popup", feat);
            if (!pop) alert("팝업이 차단되었습니다. 브라우저에서 팝업을 허용해주세요.");
          }}
          document.getElementById("btn-signup")?.addEventListener("click", openSignup);
        }})();
        </script>
        """
        st.components.v1.html(signup_html, height=76)

        # 굵은 구분선
        st.markdown(
            """
            <style>.sep{margin:26px 0 22px;border:0;border-top:1px solid rgba(49,51,63,.16);}</style>
            <hr class="sep"/>
            """,
            unsafe_allow_html=True
        )

        # --- 소셜 로그인: iFrame 내부 CSS 포함(로그인 버튼과 동일 규격) ---
        popup_html = f"""
        <style>
          .oauth-wrap {{ display: grid; gap: 14px; }}
          .oauth-btn {{
            width: 100%; height: 48px; padding: 0 16px;
            border-radius: 10px; border: 1px solid rgba(49,51,63,.18);
            background: #ffffff; color: rgba(49,51,63,.82);
            font-size: 15px; font-weight: 500; letter-spacing: .1px;
            cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
            transition: background .15s, border-color .15s, transform .02s, box-shadow .15s;
          }}
          .oauth-btn:hover {{ background:#f7f8fb; border-color: rgba(49,51,63,.28); }}
          .oauth-btn:active {{ transform: translateY(1px); }}
          .oauth-btn:focus-visible {{ outline:none; box-shadow:0 0 0 2px rgba(48,115,240,.14); }}
        </style>
        <div class="oauth-wrap">
          <button id="btn-google" class="oauth-btn">Google로 로그인</button>
          {"<button id='btn-naver' class='oauth-btn'>네이버로 로그인</button>" if ENABLED.get("naver") else ""}
          {"<button id='btn-kakao' class='oauth-btn'>카카오로 로그인</button>" if ENABLED.get("kakao") else ""}
        </div>
        <script>
          function openOAuth(url) {{
            const W = window.top || window;
            const w = 520, h = 680;
            const y = (W.outerHeight/2 + W.screenY) - (h/2);
            const x = (W.outerWidth/2  + W.screenX) - (w/2);
            const feat = "popup=yes,width="+w+",height="+h+",left="+x+",top="+y+",noopener=no,noreferrer=no";
            const pop = W.open(url, "oauth_login", feat);
            if (!pop) {{ alert("팝업이 차단되었습니다. 브라우저에서 팝업을 허용해주세요."); return; }}
            const t = setInterval(function() {{
              if (pop.closed) {{
                clearInterval(t);
                try {{ W.location.reload(); }} catch(e) {{}}
              }}
            }}, 700);
          }}
          document.getElementById("btn-google")?.addEventListener("click", () => openOAuth("{BACKEND_URL}/auth/google/login"));
          document.getElementById("btn-naver") ?.addEventListener("click", () => openOAuth("{BACKEND_URL}/auth/naver/login"));
          document.getElementById("btn-kakao") ?.addEventListener("click", () => openOAuth("{BACKEND_URL}/auth/kakao/login"));
        </script>
        """
        st.components.v1.html(popup_html, height=210)

st.divider()

# ---------------- 기능 미리보기 ----------------
st.header("✨ 광고 기능 미리보기")

base_dir = "data/sample"

def _imgs(folder):
    return sorted(glob.glob(os.path.join(folder, "*.jpg")) + glob.glob(os.path.join(folder, "*.png")))

poster_images  = _imgs(os.path.join(base_dir, "poster_sample"))
cardnews_images= _imgs(os.path.join(base_dir, "cardnews_sample"))
homepage_images= _imgs(os.path.join(base_dir, "homepage_img_sample"))
mascot_images  = _imgs(os.path.join(base_dir, "mascot_sample"))

features = [
    {"title":"🖼️ 포스터 광고 생성","desc":"상품명, 이벤트, 날짜 등을 입력하면 AI가 자동으로 포스터 이미지를 생성합니다.","image":poster_images,"page":"pages/1_포스터_광고_생성.py"},
    {"title":"🎨 카드 섹션 광고 생성","desc":"업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.","image":cardnews_images,"page":"pages/2_카드뉴스_copy.py"},
    {"title":"📝 홈페이지 생성","desc":"가게명, 상품명, 이벤트 등을 입력하면 블로그 홍보 글을 만들어줍니다.","image":homepage_images,"page":"pages/3_홈페이지.py"},
    {"title":"🎨 마스코트 생성","desc":"업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.","image":mascot_images,"page":"pages/4_마스코트.py"},
]

def _to_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return f"data:image/{path.split('.')[-1]};base64,{base64.b64encode(data).decode()}"

for i in range(0, len(features), 2):
    cols = st.columns(2)
    for j, f in enumerate(features[i:i+2]):
        with cols[j]:
            st.page_link(f["page"], label=f["title"])
            st.caption(f["desc"])
            if f["image"]:
                uris = [_to_uri(p) for p in f["image"] if os.path.exists(p)]
                if uris:
                    cls = f"swiper-{abs(hash(f['title']))}"
                    st.components.v1.html(
                        f"""
                        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css"/>
                        <div class="{cls} swiper"><div class="swiper-wrapper">
                          {''.join(f'<div class="swiper-slide"><img src="{u}"/></div>' for u in uris)}
                        </div></div>
                        <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
                        <script>new Swiper('.{cls}', {{loop:true,slidesPerView:'auto',spaceBetween:0,freeMode:true,speed:4000,autoplay:{{delay:0,disableOnInteraction:false,pauseOnMouseEnter:false,stopOnLastSlide:false}}}});</script>
                        <style>.swiper{{width:100%;height:200px;border-radius:8px;overflow:hidden;background:#000}}.swiper-slide{{width:auto!important}}.swiper-slide img{{height:100%;width:auto;object-fit:contain}}</style>
                        """,
                        height=220, scrolling=False,
                    )

st.divider()

# ---------------- 광고 히스토리 ----------------
st.header("📜 내 광고 히스토리")
if not st.session_state.token:
    st.warning("로그인 후 이용할 수 있습니다.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}
if st.button("히스토리 불러오기"):
    try:
        res = requests.get(f"{BACKEND_URL}/poster/history", headers=headers, timeout=30)
        js = res.json()
        ads = js.get("history", [])
        if not ads:
            st.info("아직 생성된 광고가 없습니다 😅")
        else:
            for ad in ads:
                with st.container(border=True):
                    st.write(f"🕒 {ad['created_at']}")
                    st.write(f"💬 문구: {ad['text']}")
                    if ad.get("image_url"):
                        url = f"{BACKEND_URL}{ad['image_url']}"
                        st.image(url, caption="저장된 광고 이미지", use_container_width=True)
                        st.download_button(
                            "📥 이미지 다운로드",
                            data=requests.get(url).content,
                            file_name=f"poster_{ad['id']}.png",
                            mime="image/png",
                        )
    except Exception as e:
        st.error(f"히스토리 불러오기 실패: {e}")
