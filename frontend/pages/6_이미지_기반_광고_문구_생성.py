# 이미지 업로드 → 백엔드 /poster/image (multipart/form-data) 호출 → raw + copies 출력.

# frontend/pages/image_text.py
import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.title("광고 문구 생성")

# 토큰 체크
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# ------------------------
# 2️⃣ 옵션 토글 / 선택
# ------------------------
uploaded_file = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg"])

# 톤앤매너 토글
tone_options = ["친근한", "전문적인", "유머러스한", "감성적인", "럭셔리한", "트렌디한"]
selected_tones = st.multiselect("문구 스타일", tone_options)
tone = ", ".join(selected_tones) if selected_tones else "기본"

# 문구 길이 토글
length_options = ["short", "long"]
length_labels  = ["짧게 (1~2문장)", "길게 (3~4문장)"]
length = st.selectbox("문구 길이", length_options, format_func=lambda x: length_labels[length_options.index(x)], index=1)

# 생성 개수
num_copies = st.number_input("생성할 문구 개수", min_value=1, max_value=10, value=3)

# 모델 선택 토글
model = st.selectbox("모델 선택 (gpt-5 : 긴 문장에 추천)", ["gpt-4.1-mini","gpt-4.1-nano","gpt-5","gpt-5-nano","gpt-5-mini"])

# ------------------------
# 3️⃣ 문구 생성 버튼
# ------------------------
if uploaded_file and st.button("이미지로 문구 생성"):
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    data = {"tone": tone, "length": length, "num_copies": num_copies, "model": model}

    try:
        with st.spinner("생성 중... (이미지 → 모델 호출)"):
            r = requests.post(f"{BACKEND_URL}/adcopy/image", files=files, data=data, headers=headers, timeout=120)
            r.raise_for_status()
            result = r.json()
            
        st.subheader("생성 결과")
        copies = result.get("copies", [])
        if copies:
            for i, c in enumerate(copies, 1):
                st.write(f"{i}. {c}")
        else:
            st.warning("생성된 문구가 없습니다. raw_output을 확인하세요.")
    except Exception as e:
        st.error(f"오류 발생: {e}")