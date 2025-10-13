import streamlit as st
import requests
import os
import glob
import base64

BACKEND_URL = "http://localhost:8000"

# -----------------------------
# 쿼리 파라미터 (Google OAuth 리다이렉트 시 사용)
# -----------------------------
params = st.query_params

def _qp(k):
    v = params.get(k)
    if isinstance(v, list):
        return v[0]
    return v

# 세션 상태 기본값
# CHANGED: provider 필드 추가
for key in ["token", "user_name", "user_email", "provider"]:  # CHANGED
    if key not in st.session_state:
        st.session_state[key] = None

# NEW: 백엔드에서 사용 가능한 OAuth 제공자 확인
def _get_enabled_providers():  # NEW
    try:
        r = requests.get(f"{BACKEND_URL}/auth/enabled", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    # 실패 시 기본값(구글만 True로 가정)
    return {"google": True, "naver": False, "kakao": False}

ENABLED = _get_enabled_providers()  # NEW

# NEW: 토큰 검증해 세션 보강 (/me 호출)
def _verify_and_fill(token: str):  # NEW
    try:
        me = requests.get(f"{BACKEND_URL}/me",
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=5)
        if me.status_code == 200:
            data = me.json()
            # 이름/이메일이 쿼리로 온 값이 없으면 서버 값으로 채움
            st.session_state.user_name  = st.session_state.user_name or data.get("name") or ""
            st.session_state.user_email = st.session_state.user_email or data.get("email") or ""
            st.session_state.provider   = data.get("provider") or st.session_state.get("provider")
            return True
        else:
            return False
    except Exception:
        return False

# ✅ 로그인 콜백에서 받은 값 세션에 저장
tok = _qp("token")
if tok:
    st.session_state.token      = tok
    st.session_state.user_name  = _qp("name") or st.session_state.user_name or ""    # CHANGED(보존 + 보강)
    st.session_state.user_email = _qp("email") or st.session_state.user_email or ""  # CHANGED
    # NEW: provider는 쿼리에 없을 수 있어 /me로 채움
    _verify_and_fill(tok)  # NEW

    # 쿼리 파라미터 초기화 (로그인 후 URL 깔끔하게 유지)
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        email = st.session_state.user_email
        r = requests.get(f"{BACKEND_URL}/userinfo/{email}", headers=headers)
        if r.status_code == 200:
            data = r.json()
            if "message" not in data:
                st.session_state.store_profile = data
            else:
                st.session_state.store_profile = {
                    "store_name": "",
                    "category": "",
                    "phone": "",
                    "address": "",
                }
        else:
            st.session_state.store_profile = {
                "store_name": "",
                "category": "",
                "phone": "",
                "address": "",
            }
    except Exception:
        st.session_state.store_profile = {
            "store_name": "",
            "category": "",
            "phone": "",
            "address": "",
        }

    # ✅ URL 정리 (쿼리 파라미터 제거)
    try:
        st.query_params.clear()
    except Exception:
        pass

# NEW: 수동 로그아웃 헬퍼
def _logout():  # NEW
    for k in ["token", "user_name", "user_email", "provider"]:
        st.session_state[k] = None
    st.rerun()

# NEW: 토큰만 있고 /me 검증 실패 시 안전하게 로그아웃 처리
if st.session_state.get("token") and not st.session_state.get("user_email"):  # NEW
    ok = _verify_and_fill(st.session_state["token"])
    if not ok:
        st.warning("세션이 만료되었거나 토큰 검증에 실패했어요. 다시 로그인해주세요.")
        _logout()

# -----------------------------
# 로그인 UI (최종)
# -----------------------------
if st.session_state.get("token"):
    colA, colB = st.columns([3, 1], gap="small")
    with colA:
        # CHANGED: provider 표기 추가
        provider = f" via {st.session_state.provider}" if st.session_state.get("provider") else ""
        st.success(f"✅ 로그인됨: {st.session_state.user_name} ({st.session_state.user_email}){provider}")
    with colB:
        if st.button("로그아웃", use_container_width=True):
            _logout()  # CHANGED
else:
    # --- 로그인 영역 전용 스타일 ---
    st.markdown("""
    <style>
      .login-wrap{
        max-width: 420px;
        margin: -80px auto 0;          /* 더 위로: -100px 등으로 조절 */
        text-align: center;
      }
      /* '파2팀' ↔ '광고 제작 서비스' 간격은 gap으로 */
      .login-head{
        display: flex; flex-direction: column; align-items: center;
        gap: 25px;                      /* ← 둘 사이 간격 */
        margin-bottom: 10px;            /* ← 입력폼과의 간격 */
      }
      .login-pill{
        display: inline-flex; align-items: center; justify-content: center;
        padding: 12px 30px; border-radius: 9999px;
        background: linear-gradient(180deg,#FFE66D,#FFC800);
        box-shadow: 0 10px 20px rgba(255,200,0,.35), inset 0 2px 0 #FFF7B8;
      }
      .pill-text{
        font-weight: 900; font-size: 22px; letter-spacing: 1.5px; color:#111;
        text-shadow: 0 1px 0 rgba(255,255,255,.6);
      }
      .login-title{
        font-weight: 800; font-size: 26px; margin: 0;  /* 제목을 배지 바로 아래에 붙임 */
      }
      .help-link{
        display:block; text-align:center; margin:12px 0 6px;
        color:#2E5AAC; font-weight:800; text-decoration:none;
      }
      .help-link:hover{ text-decoration: underline; }

      /* 모바일 여백 보정 (선택) */
      @media (max-width: 480px){
        .login-wrap{ margin: -40px 12px 0; }
      }
    </style>
    """, unsafe_allow_html=True)

    _l, _c, _r = st.columns([1,2,1])
    with _c:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        # 파2팀(위) + 제목(아래)
        st.markdown("""
        <div class="login-head">
          <div class="login-pill"><span class="pill-text">파2팀</span></div>
          <div class="login-title">광고 제작 서비스</div>
        </div>
        """, unsafe_allow_html=True)

        # 입력/버튼 (원본 보존)
        st.text_input("아이디", key="login_id", label_visibility="collapsed", placeholder="아이디")
        st.text_input("비밀번호", key="login_pw", label_visibility="collapsed", placeholder="비밀번호", type="password")

        # CHANGED: 소셜 로그인 버튼을 '가용한 경우'에만 노출
        if ENABLED.get("google"):
            st.link_button("Google로 로그인", f"{BACKEND_URL}/auth/google/login", use_container_width=True)  # CHANGED
        if ENABLED.get("naver"):  # NEW
            st.link_button("네이버로 로그인", f"{BACKEND_URL}/auth/naver/login", use_container_width=True)
        if ENABLED.get("kakao"):  # NEW
            st.link_button("카카오로 로그인", f"{BACKEND_URL}/auth/kakao/login", use_container_width=True)

        st.markdown('<a class="help-link" href="#">아이디 / 비밀번호 찾기 &gt;</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # .login-wrap 닫기

st.divider()

# -----------------------------
# 광고 기능 미리보기 (2열씩 배치)
# -----------------------------
st.header("✨ 광고 기능 미리보기")

mascot_dir = "data/sample/mascot_sample"

base_dir = "data/sample"

# 포스터 이미지
poster_dir = os.path.join(base_dir, "poster_sample")
poster_images = sorted(
    glob.glob(os.path.join(poster_dir, "*.jpg"))
    + glob.glob(os.path.join(poster_dir, "*.png"))
)

# 카드뉴스 이미지
cardnews_dir = os.path.join(base_dir, "cardnews_sample")
cardnews_images = sorted(
    glob.glob(os.path.join(cardnews_dir, "*.jpg"))
    + glob.glob(os.path.join(cardnews_dir, "*.png"))
)

# 홈페이지 이미지
homepage_dir = os.path.join(base_dir, "homepage_img_sample")
homepage_images = sorted(
    glob.glob(os.path.join(homepage_dir, "*.jpg"))
    + glob.glob(os.path.join(homepage_dir, "*.png"))
)

# 마스코트 이미지
mascot_dir = os.path.join(base_dir, "mascot_sample")
mascot_images = sorted(
    glob.glob(os.path.join(mascot_dir, "*.jpg"))
    + glob.glob(os.path.join(mascot_dir, "*.png"))
)

features = [
    {
        "title": "🖼️ 포스터 광고 생성",
        "desc": "상품명, 이벤트, 날짜 등을 입력하면 AI가 자동으로 포스터 이미지를 생성합니다.",
        "image": poster_images,
        "page": "pages/1_포스터_광고_생성.py"
    },
    {
        "title": "🎨 카드 섹션 광고 생성",
        "desc": "업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.",
        "image": cardnews_images,
        "page": "pages/2_카드_광고_생성.py"
    },
    {
        "title": "📝 홈페이지 생성",
        "desc": "가게명, 상품명, 이벤트 등을 입력하면 블로그 홍보 글을 만들어줍니다.",
        "image": homepage_images,
        "page": "pages/3_홈페이지.py"
    },
    {
        "title": "🎨 마스코트 생성",
        "desc": "업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.",
        "image": mascot_images,
        "page": "pages/4_마스코트.py"
    },
]

def to_data_uri(path: str):
    """이미지 파일을 base64로 인코딩해서 브라우저에서 직접 표시 가능하게 변환"""
    with open(path, "rb") as f:
        data = f.read()
    mime = "image/" + path.split(".")[-1]
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"

# ✅ 2열씩 반복 배치
for i in range(0, len(features), 2):
    cols = st.columns(2)
    for j, feature in enumerate(features[i:i+2]):
        with cols[j]:
            st.subheader(feature["title"])
            st.caption(feature["desc"])

            # 여러 장 이미지 → 슬라이더로 출력
            if "image" in feature and feature["image"]:
                uris = []
                for img_path in feature["image"]:
                    if os.path.exists(img_path):
                        uris.append(to_data_uri(img_path))

                if uris:
                    swiper_class = f"swiper-{abs(hash(feature['title']))}"

                    slider_html = f"""
                    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css"/>
                    <div class="{swiper_class} swiper">
                    <div class="swiper-wrapper">
                        {''.join(f'<div class="swiper-slide"><img src="{u}"/></div>' for u in uris)}
                    </div>
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
                    <script>
                    new Swiper('.{swiper_class}', {{
                        loop: true,
                        slidesPerView: 'auto',   // 이미지 크기만큼 이어붙이기
                        spaceBetween: 0,         // 여백 제거
                        freeMode: true,          // 자연스럽게 흐름
                        speed: 4000,             // 흐르는 속도
                        autoplay: {{
                        delay: 0,
                        disableOnInteraction: false,
                        pauseOnMouseEnter: false,   // 🔹 마우스 올려도 멈추지 않음
                        stopOnLastSlide: false      // 🔹 마지막 슬라이드에서 멈추지 않음
                        }}
                    }});
                    </script>
                    <style>
                    .swiper {{
                        width: 100%;
                        height: 200px;   /* 슬라이더 높이 */
                        border-radius: 8px;
                        overflow: hidden;
                        background: #000;
                    }}
                    .swiper-slide {{
                        width: auto !important;  /* 이미지 크기대로 */
                    }}
                    .swiper-slide img {{
                        height: 100%;
                        width: auto;
                        object-fit: contain;   /* 잘리지 않게 */
                    }}
                    </style>
                    """
                    st.components.v1.html(slider_html, height=220, scrolling=False)
                else:
                    st.warning("⚠️ 미리보기 이미지 없음")

st.divider()

# -----------------------------
# 광고 히스토리 불러오기
# -----------------------------
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
                            mime="image/png"
                        )
    except Exception as e:
        st.error(f"히스토리 불러오기 실패: {e}")
