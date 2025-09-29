import streamlit as st
import requests
import os

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="광고 제작 도우미", page_icon="🎯", layout="wide")
st.title("🎯 소상공인 광고 제작 도우미")

st.markdown("""
안녕하세요! 이 앱은 **소상공인을 위한 광고 콘텐츠 제작 도구**입니다.  
왼쪽 사이드바에서 원하는 기능을 선택하거나, 아래 미리보기를 눌러 바로 이동해 보세요.
""")

# -----------------------------
# 쿼리 파라미터 처리 (로그인 후 리다이렉트 시)
# -----------------------------
params = st.query_params  # ✅ 최신 문법

def _qp(k):
    v = params.get(k)
    if isinstance(v, list):
        return v[0]
    return v

# 세션 상태 기본값
for key in ["token", "user_name", "user_email"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ✅ 로그인 콜백에서 받은 값 세션에 저장
tok = _qp("token")
if tok:
    st.session_state.token = tok
    st.session_state.user_name = _qp("name") or ""
    st.session_state.user_email = _qp("email") or ""

    # 쿼리 파라미터 초기화 (로그인 후 URL 깔끔하게 유지)
    try:
        st.query_params.clear()  # ✅ 최신 문법
    except Exception:
        pass

# -----------------------------
# 로그인 UI
# -----------------------------
colA, colB = st.columns(2)
with colA:
    if st.session_state.token:
        st.success(f"✅ 로그인됨: {st.session_state.user_name} ({st.session_state.user_email})")
    else:
        st.info("로그인이 필요합니다.")

with colB:
    if st.session_state.token:
        if st.button("로그아웃"):
            for k in ["token", "user_name", "user_email"]:
                st.session_state[k] = None
            st.rerun()
    else:
        st.link_button("Google로 로그인", f"{BACKEND_URL}/auth/google/login")

st.divider()

# -----------------------------
# 광고 기능 미리보기 (2열씩 배치)
# -----------------------------
st.header("✨ 광고 기능 미리보기")

features = [
    {
        "title": "🖼️ 포스터 광고 생성",
        "desc": "상품명, 이벤트, 날짜 등을 입력하면 AI가 자동으로 포스터 이미지를 생성합니다.",
        "image": "data/sample/poster_sample.png",
        "page": "pages/1_포스터_광고_생성.py"
    },
    {
        "title": "🎨 카드 섹션 광고 생성",
        "desc": "업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.",
        "image": "data/sample/card_sample.png",
        "page": "pages/2_카드_광고_생성.py"
    },
    {
        "title": "📝 홈페이지 생성",
        "desc": "가게명, 상품명, 이벤트 등을 입력하면 블로그 홍보 글을 만들어줍니다.",
        "image": "data/sample/homepage_sample.png",
        "page": "pages/3_홈페이지.py"
    },
    {
        "title": "🎨 마스코트 생성",
        "desc": "업로드한 이미지를 흑백, 블러, 텍스트 오버레이 등으로 꾸밀 수 있습니다.",
        "image": "data/sample/mascot_sample.jpg",
        "page": "pages/4_마스코트.py"
    },
]

# ✅ 2열씩 반복 배치
for i in range(0, len(features), 2):
    cols = st.columns(2)
    for j, feature in enumerate(features[i:i+2]):
        with cols[j]:
            st.subheader(feature["title"])
            st.caption(feature["desc"])
            if os.path.exists(feature["image"]):
                st.image(feature["image"], use_container_width=True)
            else:
                st.warning("⚠️ 미리보기 이미지 없음")
            if st.button("👉 이동하기", key=feature["title"]):
                st.switch_page(feature["page"])

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
