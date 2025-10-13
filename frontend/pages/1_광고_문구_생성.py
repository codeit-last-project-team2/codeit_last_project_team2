# 사용자로부터 브랜드/상품/톤/길이/개수/모델 입력 받아 백엔드 /poster/text 호출. 원문(디버그) + 파싱 결과 표시.

# frontend/pages/create_text.py
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

st.title("📝 광고 문구 생성")

# 환경 체크
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# ------------------------
# 백엔드 호출 함수
# ------------------------
def generate_ad_copy(product, num_copies, tone, length):
    model = MODEL_BY_LENGTH.get(length, "gpt-5-mini")
    payload = {
        "product": product,
        "tone": tone,
        "length": length,
        "num_copies": num_copies,
        "model": model,
    }
    r = requests.post(f"{BACKEND_URL}/adcopy/text", json=payload, headers=headers, timeout=60)
    if r.ok:
        return r.json()
    else:
        try:
            err = r.json()
            detail = err.get("detail") or r.text
        except Exception:
            detail = r.text
        raise RuntimeError(f"API {r.status_code} - {detail}")
    
# --- 도움말 (접기/펼치기) ---
with st.expander("❓ 도움말", expanded=False):
    st.markdown(
        """
        <div style="
            background:#f7f7f8;
            border:1px solid #e5e7eb;
            border-radius:12px;
            padding:16px 18px;
            line-height:1.7;
            font-size:15px;
        ">
            <p><b>상품명</b> : 광고의 주체가 되는 제품/서비스 이름을 입력하세요.</p>
            <p><b>문구 스타일</b> : 광고 문구의 전반적인 분위기를 선택하세요.</p>
            <p><b>문구 길이</b> : <i>짧게</i>는 1~2문장, <i>길게</i>는 3~4문장 기준으로 생성됩니다.</p>
            <p><b>생성 개수</b> : 한 번에 받아볼 문구의 개수입니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------
# 1️⃣ 브랜드 / 상품명 입력
# ------------------------
product = st.text_input("상품명", placeholder = "EX) 아메리카노")

# ------------------------
# 2️⃣ 옵션 토글 / 선택
# ------------------------
st.subheader("옵션 설정")

# 톤앤매너 토글
tone_options = ["친근한", "전문적인", "유머러스한", "감성적인", "럭셔리한", "트렌디한"]
selected_tones = st.multiselect("문구 스타일", tone_options)
tone = ", ".join(selected_tones) if selected_tones else "기본"

# 길이 선택 (짧게/중간/길게)
length_options = ["short", "medium", "long"]
length_labels  = ["짧게 (1~2문장)", "중간 (2~3문장)", "길게 (4~5문장)"]
length = st.selectbox(
    "문구 길이",
    length_options,
    index=1,
    format_func=lambda x: length_labels[length_options.index(x)]
)

# 길이에 따른 모델 자동 매핑
MODEL_BY_LENGTH = {
    "short":  "gpt-4.1-mini",
    "medium": "gpt-5-mini",
    "long":   "gpt-5",
}

# 생성 개수
num_copies = st.number_input("생성할 문구 개수", min_value=1, max_value=10, value=3)

# ------------------------
# 3️⃣ 문구 생성 버튼
# ------------------------
if st.button("문구 생성"):
    if not product:
        st.warning("상품명을 입력해주세요.")
    else:
        with st.spinner("문구 생성 중..."):
            try:
                result = generate_ad_copy(product, num_copies, tone, length)

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
