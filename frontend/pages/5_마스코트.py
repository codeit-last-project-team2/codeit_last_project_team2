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
# 입력 UI
# -----------------------------
with st.form("mascot_form"):
    st.subheader("매장 선택")
    store_list_res = requests.post(f"{BACKEND_URL}/userinfo/get_store_names", json={"user_email": st.session_state.get("user_email")}, headers=headers)

    if store_list_res.status_code != 200:
        st.error("조회 실패")
        st.text(store_list_res.status_code)
    else:
        stores = store_list_res.json()

    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
    else:
        selected_store = st.radio("매장을 선택하세요:", stores, horizontal=True)

    store_info_res = requests.post(f"{BACKEND_URL}/userinfo/get_store_info", json={"user_email": st.session_state.get("user_email"), "store_name": selected_store}, headers=headers)

    if store_info_res.status_code != 200:
        st.error("조회 실패")
        st.text(store_info_res.status_code)
    else:
        store_info = store_info_res.json()

    st.subheader("추가 정보 입력")

    color = st.text_input("대표 색상",)
    keyword = st.text_input("키워드",)
    personality = st.text_input("성격",)
    output_style = st.selectbox("출력 형태를 선택하세요", ["2d", "3d", "픽셀", "카툰", "실사 일러스트", "미니멀", "심볼/아이콘", "수채화풍", "사이버/메카닉"], index=0)
    additional_requirements = st.text_area("추가 요구 사항","(선택)")
    submitted = st.form_submit_button("마스코트 생성하기")



# -----------------------------
# 실행
# -----------------------------
if submitted:
    st.info("마스코트 이미지를 생성 중입니다... 잠시만 기다려주세요!")
    mascot_req = {
        'main_color': color,
        'keyword': keyword,
        'mascot_personality': personality,
        'store_name': store_info['store_name'],
        'mood': store_info['mood'],
        'output_style': output_style,
        'additional_requirements': additional_requirements if additional_requirements != "(선택)" else '없음',
    }

    response = requests.post(f"{BACKEND_URL}/mascot/generate", json=mascot_req, headers=headers)

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