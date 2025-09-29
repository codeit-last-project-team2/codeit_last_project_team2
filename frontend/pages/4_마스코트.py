import streamlit as st
import requests
from io import BytesIO
from PIL import Image

BACKEND_URL = "http://127.0.0.1:8000"

st.title("마스코트 생성기")

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
if "mascot_history" not in st.session_state:
    st.session_state.mascot_history = []  # [{info, url, image_bytes}, ...]
if "mascot_candidates" not in st.session_state:
    st.session_state.mascot_candidates = []
if "selected_url" not in st.session_state:
    st.session_state.selected_url = None
if "mascot_info" not in st.session_state:
    st.session_state.mascot_info = {}

# -----------------------------
# 입력 UI
# -----------------------------
with st.form("mascot_form"):
    st.subheader("브랜드 정보 입력")

    대표색상 = st.text_input("대표 색상")
    키워드 = st.text_input("키워드")
    성격 = st.text_input("성격")
    브랜드소개 = st.text_area("브랜드 소개")
    추가요구사항 = st.text_area("추가 요구 사항", "(선택)")

    submitted = st.form_submit_button("마스코트 생성하기")

# -----------------------------
# 실행 (마스코트 생성 API 호출)
# -----------------------------
if submitted:
    info = {
        "main_color": 대표색상,
        "keyword": 키워드,
        "personality": 성격,
        "brand_intro": 브랜드소개,
        "additional_requirements": '없음' if 추가요구사항 == '(선택)' else 추가요구사항
    }

    st.info("마스코트 이미지를 생성 중입니다... 잠시만 기다려주세요!")

    response = requests.post(f"{BACKEND_URL}/mascot/generate", json=info, headers=headers)

    if response.status_code != 200:
        st.error(f"마스코트 생성 실패: {response.text}")
    else:
        st.session_state.mascot_candidates = response.json()  # ✅ 후보 저장
        st.session_state.mascot_info = info
        st.session_state.selected_url = None  # 새로 만들면 기존 선택 초기화

# -----------------------------
# 후보 보여주기
# -----------------------------
if st.session_state.mascot_candidates:
    st.subheader("생성된 마스코트 후보들")
    cols = st.columns(3)

    for idx, (col, url) in enumerate(zip(cols, st.session_state.mascot_candidates)):
        with col:
            st.image(url, use_container_width=True)
            if st.button(f"이 마스코트 선택하기 #{idx+1}", key=f"select_{idx}"):
                st.session_state.selected_url = url  # ✅ 선택 저장

# -----------------------------
# 선택된 마스코트 표시
# -----------------------------
if st.session_state.selected_url:
    st.success("🎉 선택된 마스코트")
    st.image(st.session_state.selected_url, use_container_width=True)

    # 이미지 다운로드 → 세션 저장
    img_res = requests.get(st.session_state.selected_url)
    if img_res.status_code == 200:
        img_bytes = img_res.content
        # 중복 저장 방지
        if not any(ad["url"] == st.session_state.selected_url for ad in st.session_state.mascot_history):
            st.session_state.mascot_history.append({
                "info": st.session_state.mascot_info,
                "url": st.session_state.selected_url,
                "image_bytes": img_bytes
            })
    else:
        st.warning("이미지 다운로드 실패")

# -----------------------------
# 히스토리 보여주기
# -----------------------------
if st.session_state.mascot_history:
    st.subheader("📜 내가 만든 마스코트 히스토리")
    for i, ad in enumerate(reversed(st.session_state.mascot_history), 1):
        st.write(f"### {i}. {ad['info']['keyword']} / {ad['info']['personality']}")
        st.image(BytesIO(ad["image_bytes"]), caption="마스코트", use_container_width=True)
        st.download_button(
            f"📥 다운로드 {i}",
            data=ad["image_bytes"],
            file_name=f"mascot_{i}.png",
            mime="image/png"
        )
