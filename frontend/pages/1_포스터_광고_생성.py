import streamlit as st
import requests
from io import BytesIO
from PIL import Image

BACKEND_URL = "http://127.0.0.1:8000"

st.title("🖼️ 포스터 광고 생성")

# -----------------------------
# 세션 값 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# -----------------------------
# 세션 상태 초기화 (최초 실행 시만)
# -----------------------------
if "poster_history" not in st.session_state:
    st.session_state.poster_history = []  # [{title, body, dalle_prompt, image_bytes}, ...]

# -----------------------------
# 입력 UI
# -----------------------------
product = st.text_input("상품명", placeholder="수제 햄버거")
event = st.text_input("이벤트", placeholder="50% 할인 행사")
date = st.text_input("날짜", placeholder="2025년 9월 20일")
location = st.text_input("장소", placeholder="서울 강남역 매장")
vibe = st.text_input("분위기/스타일", placeholder="따뜻한, 가족, 피크닉")

position = st.selectbox("제목 위치 선택", ["top", "center", "bottom"], index=0)
gpt_model = st.selectbox("텍스트 생성 모델 선택", ["gpt-4.1-mini", "gpt-4.1-nano", "gpt-5-mini"], index=0)
dalle_size = st.selectbox("이미지 크기", ["1024x1024", "1024x1792", "1792x1024"], index=0)

go = st.button("🎨 포스터 생성", type="primary")

# -----------------------------
# 실행
# -----------------------------
if go:
    with st.spinner("백엔드에 요청 중..."):
        # 1. 텍스트 생성
        payload = {
            "product": product or "상품명 미정",
            "event": event or "이벤트 미정",
            "date": date or "날짜 미정",
            "location": location or "장소 미정",
            "vibe": vibe or "분위기 미정",
            "gpt_model": gpt_model,
        }

        text_res = requests.post(f"{BACKEND_URL}/poster/text", json=payload, headers=headers)
        if text_res.status_code != 200:
            st.error("텍스트 생성 실패")
            st.stop()

        text_data = text_res.json()

        # 2. 이미지 생성
        image_payload = {
            "title": text_data["title"],
            "body": text_data["body"],
            "dalle_prompt": text_data["dalle_prompt"],
            "position": position,
            "dalle_size": dalle_size,
        }

        img_res = requests.post(f"{BACKEND_URL}/poster/image", json=image_payload, headers=headers)
        if img_res.status_code != 200:
            st.error("이미지 생성 실패")
            st.stop()

        img_bytes = BytesIO(img_res.content)

        # ✅ 세션에 저장
        st.session_state.poster_history.append({
            "title": text_data["title"],
            "body": text_data["body"],
            "dalle_prompt": text_data["dalle_prompt"],
            "image_bytes": img_bytes.getvalue()
        })

# -----------------------------
# 히스토리 보여주기
# -----------------------------
if st.session_state.poster_history:
    st.subheader("📜 내가 만든 광고 히스토리")
    for i, ad in enumerate(reversed(st.session_state.poster_history), 1):
        st.write(f"### {i}. {ad['title']}")
        st.write(ad["body"])
        st.code(ad["dalle_prompt"], language="json")
        st.image(BytesIO(ad["image_bytes"]), caption="포스터", use_container_width=True)
        st.download_button(
            f"📥 다운로드 {i}",
            data=ad["image_bytes"],
            file_name=f"poster_{i}.png",
            mime="image/png"
        )
