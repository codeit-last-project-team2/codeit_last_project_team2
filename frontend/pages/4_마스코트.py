import streamlit as st
import requests
from io import BytesIO
from PIL import Image

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="마스코트 생성", layout="wide")
st.title("🎨 마스코트 생성")

# -----------------------------
# 로그인 및 매장 정보 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

if "store_profile" not in st.session_state or not st.session_state["store_profile"].get("store_name"):
    st.warning("⚠️ 매장 관리 페이지에서 정보를 먼저 입력해주세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}
store = st.session_state["store_profile"]

# -----------------------------
# 추가 입력 UI
# -----------------------------
st.markdown("### 🧸 마스코트 정보 입력")

main_color = st.text_input("대표 색상", placeholder="예: 파스텔 블루")
keyword = st.text_input("키워드", placeholder="예: 귀여움, 친근함, 동물")
personality = st.text_input("성격", placeholder="예: 밝고 긍정적")
output_style = st.text_input("출력 스타일", placeholder="예: 3D 캐릭터, 일러스트, 심플 로고")
additional = st.text_area("추가 요구사항 (선택)", placeholder="예: 매장 로고와 어울리게 제작해주세요")

go = st.button("🎨 마스코트 생성", type="primary")

# -----------------------------
# 실행
# -----------------------------
if go:
    with st.spinner("마스코트 생성 중..."):
        payload = {
            "user_email": st.session_state.get("user_email"),
            "store_name": store.get("store_name", ""),
            "category": store.get("category", ""),
            "main_color": main_color,
            "keyword": keyword,
            "mascot_personality": personality,
            "output_style": output_style,
            "additional_requirements": additional,
        }

        res = requests.post(f"{BACKEND_URL}/mascot/generate", json=payload, headers=headers)
        if res.status_code != 200:
            st.error("❌ 마스코트 생성 실패")
            st.stop()

        image_bytes = BytesIO(res.content)
        st.image(Image.open(image_bytes), caption="생성된 마스코트", use_container_width=True)
        st.download_button("📥 이미지 다운로드", image_bytes, file_name="mascot.png", mime="image/png")
