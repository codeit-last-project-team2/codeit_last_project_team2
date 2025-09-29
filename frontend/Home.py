import streamlit as st
import requests
import os
import base64
import glob

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
