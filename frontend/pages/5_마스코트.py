import streamlit as st
import requests

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
if "poster_history" not in st.session_state:
    st.session_state.poster_history = []  # [{title, body, dalle_prompt, image_bytes}, ...]

# -----------------------------
# 입력 UI
# -----------------------------
with st.form("mascot_form"):
    st.subheader("브랜드 정보 입력")

    대표색상 = st.text_input("대표 색상",)
    키워드 = st.text_input("키워드",)
    성격 = st.text_input("성격",)
    브랜드소개 = st.text_area("브랜드 소개")
    추가요구사항 = st.text_area("추가 요구 사항","(선택)")

    submitted = st.form_submit_button("마스코트 생성하기")

# -----------------------------
# 실행
# -----------------------------
if submitted:
    info = {
        "main_color": 대표색상,
        "keyword": 키워드,
        "personality": 성격,
        "brand_intro": 브랜드소개,
        "additional_requirements": '없음' if 추가요구사항=='(선택)' else 추가요구사항
    }

    st.info("마스코트 이미지를 생성 중입니다... 잠시만 기다려주세요!")


    response = requests.post(f"{BACKEND_URL}/mascot/generate", json=info, headers=headers)

    if response.status_code != 200:
        st.error(f"마스코트 생성 실패: {response.text}")
    else:
        mascot_urls = response.json() 

    st.subheader("생성된 마스코트 후보들")
    selected_url = None
    cols = st.columns(3)

    for idx, (col, url) in enumerate(zip(cols, mascot_urls)):
        with col:
            st.image(url, use_container_width=True)
            if st.button(f"이 마스코트 선택하기 #{idx+1}"):
                selected_url = url

    if selected_url:
        st.success("🎉 선택된 마스코트")
        st.image(selected_url, use_container_width=True)