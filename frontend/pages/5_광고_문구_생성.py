# 사용자로부터 브랜드/상품/톤/길이/개수/모델 입력 받아 백엔드 /poster/text 호출. 원문(디버그) + 파싱 결과 표시.

# frontend/pages/create_text.py
import os
import requests
import streamlit as st
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())   # 최상위에 있는 .env 파일 자동 로드

st.title("광고 문구 생성")

# ------------------------
# 환경 변수 / secrets
# ------------------------
BACKEND_URL = st.secrets.get("BACKEND_URL") or os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_API_KEY = st.secrets.get("BACKEND_API_KEY") or os.getenv("BACKEND_API_KEY", None)

# ------------------------
# 백엔드 호출 함수
# ------------------------
def generate_ad_copy(product, num_copies, tone, length, model):
    payload = {
        "product": product,
        "tone": tone,
        "length": length,
        "num_copies": num_copies,
        "model": model,
    }
    headers = {}
    if BACKEND_API_KEY:
        headers["x-api-key"] = BACKEND_API_KEY
    r = requests.post(f"{BACKEND_URL}/adcopy/text", json=payload, headers=headers, timeout=60)
    if r.ok:
        return r.json()
    else:
        # ✅ 502 등에 담긴 백엔드 detail 표시
        try:
            err = r.json()
            detail = err.get("detail") or r.text
        except Exception:
            detail = r.text
        # 스트림릿 상단에서 보여줄 수 있게 예외 메시지에 포함
        raise RuntimeError(f"API {r.status_code} - {detail}")

# ------------------------
# 1️⃣ 브랜드 / 상품명 입력
# ------------------------
product = st.text_input("상품명", placeholder = "여기에 입력해주세요")

# ------------------------
# 2️⃣ 옵션 토글 / 선택
# ------------------------
st.subheader("옵션 설정")

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
if st.button("문구 생성"):
    if not product:
        st.warning("상품명을 입력해주세요.")
    else:
        with st.spinner("문구 생성 중..."):
            try:
                result = generate_ad_copy(product, num_copies, tone, length, model)

                # 파싱된 문구 출력
                st.subheader("생성 결과")
                copies = result.get("copies", [])
                if copies:
                    for i, c in enumerate(copies, 1):
                        st.write(f"{i}. {c}")
                else:
                    st.warning("생성된 문구가 없습니다.")

            except Exception as e:
                st.error(f"문구 생성 중 오류 발생: {e}")
