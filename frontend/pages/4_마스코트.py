import streamlit as st
import requests, os, datetime

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
# 세션 상태 초기화
# -----------------------------
if "mascot_candidates" not in st.session_state:
    st.session_state.mascot_candidates = []
if "mascot_info" not in st.session_state:
    st.session_state.mascot_info = {}

# -----------------------------
# 저장 경로 설정
# -----------------------------
BASE_MASCOT_SAVE_DIR = os.path.join("data", "user_info", st.session_state.get("user_email"))

# -----------------------------
# 입력 UI
# -----------------------------
with st.form("mascot_form"):
    st.subheader("매장 선택")
    store_list_res = requests.get(
        f"{BACKEND_URL}/userinfo/get_store_names",
        headers=headers,
    )

    if store_list_res.status_code != 200:
        st.error("조회 실패")
        st.text(store_list_res.status_code)
        stores = []
    else:
        stores = store_list_res.json()

    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
        selected_store = None
        submitted = st.form_submit_button("마스코트 생성하기", disabled=True)
        st.stop()

    else:
        selected_store = st.radio("매장을 선택하세요:", stores, horizontal=True)

    store_info = {}
    if selected_store:
        store_info_res = requests.post(
            f"{BACKEND_URL}/userinfo/get_store_info",
            json={"user_email": st.session_state.get("user_email"), "store_name": selected_store},
            headers=headers,
        )
        if store_info_res.status_code == 200:
            store_info = store_info_res.json()
        else:
            st.error("매장 정보 조회 실패")
            store_info = {}

    st.subheader("추가 정보 입력")
    color = st.text_input("대표 색상")
    keyword = st.text_input("키워드")
    personality = st.text_input("성격")
    output_style = st.selectbox(
        "출력 형태를 선택하세요",
        ["2d", "3d", "픽셀", "카툰", "실사 일러스트", "미니멀", "심볼/아이콘", "수채화풍", "사이버/메카닉"],
        index=0,
    )
    additional_requirements = st.text_area("추가 요구 사항", "(선택)")

    submitted = st.form_submit_button("마스코트 생성하기")

# -----------------------------
# 마스코트 생성 실행 (자동 저장)
# -----------------------------
if submitted and selected_store and store_info:
    st.info("마스코트 이미지를 생성 중입니다... 잠시만 기다려주세요!")

    mascot_req = {
        "main_color": color,
        "keyword": keyword,
        "mascot_personality": personality,
        "store_name": store_info["store_name"],
        "mood": store_info["mood"],
        "output_style": output_style,
        "additional_requirements": additional_requirements if additional_requirements != "(선택)" else "없음",
    }

    response = requests.post(f"{BACKEND_URL}/mascot/generate", json=mascot_req, headers=headers)

    if response.status_code != 200:
        st.error(f"마스코트 생성 실패: {response.text}")
    else:
        mascot_urls = response.json()
        st.session_state.mascot_candidates = mascot_urls
        st.session_state.mascot_info = mascot_req

        # ✅ 자동 저장 (생성 시 히스토리에 추가)
        MASCOT_SAVE_DIR = os.path.join(BASE_MASCOT_SAVE_DIR, store_info["store_name"], 'mascot_img')
        os.makedirs(MASCOT_SAVE_DIR, exist_ok=True)
        for url in mascot_urls:
            response = requests.get(url)
            if response.status_code == 200:
                filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                filepath = os.path.join(MASCOT_SAVE_DIR, filename)
        
                # 저장
                with open(filepath, "wb") as f:
                    f.write(response.content)
                    
                save_req = {
                    "user_email": st.session_state.get("user_email"),
                    "store_name": mascot_req["store_name"],
                    "keyword": mascot_req["keyword"],
                    "mascot_personality": mascot_req["mascot_personality"],
                    "path": filepath,
                }
                save_res = requests.post(f"{BACKEND_URL}/mascot/save", json=save_req, headers=headers)
        st.success("✅ 생성된 마스코트가 히스토리에 자동 저장되었습니다!")

# -----------------------------
# 히스토리 불러오기 (항목별 다운로드만)
# -----------------------------
st.subheader("📜 내가 만든 마스코트 히스토리")
hist_res = requests.get(f"{BACKEND_URL}/mascot/history", headers=headers)
if hist_res.status_code == 200:
    histories = hist_res.json()
    if not histories:
        st.info("히스토리가 없습니다.")
    else:
        for i, ad in enumerate(histories, 1):
            st.write(f"### {i}. {ad['keyword']} / {ad['mascot_personality']}")
            st.image(
                ad["path"],
                caption=f"{ad['store_name']} - {ad['created_at']}",
                use_container_width=True,
            )

            # PNG/JPG 다운로드 버튼 (항목별 제공)
            try:
                with open(ad["path"], "rb") as f:
                    img_bytes = f.read()

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.download_button(
                        f"📥 PNG 다운로드 {i}",
                        data=img_bytes,
                        file_name=f"mascot_{i}.png",
                        mime="image/png",
                    )
                with col2:
                    st.download_button(
                        f"📥 JPG 다운로드 {i}",
                        data=img_bytes,
                        file_name=f"mascot_{i}.jpg",
                        mime="image/jpeg",
                    )
            except FileNotFoundError:
                st.warning("❌ 이미지 파일을 찾을 수 없습니다.")
else:
    st.error("히스토리 조회 실패")
