import streamlit as st
from PIL import Image
import io
import openai

# ==== OpenAI API 키 설정 ====
openai.api_key = ""

# ==== GPT 광고/블로그 생성 함수 ====
def gen_ad(prompt, keyword, max_tokens=1024, temperature=0.8):
    response = openai.chat.completions.create(

        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "당신은 한국어 전문 광고 문구 카피라이터입니다."},
            {"role": "user", "content": f"{prompt}\n키워드:{keyword}"}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        n=3,
    )
    ads = [choice.message.content.strip() for choice in response.choices]
    return ads

# ==== 세션 상태 초기화 ====
if 'uploaded_img' not in st.session_state:
    st.session_state.uploaded_img = None

if 'ads' not in st.session_state:
    st.session_state.ads = []

if 'selected_ad' not in st.session_state:
    st.session_state.selected_ad = ""

# ==== Streamlit UI ====
st.title("블로그/광고 콘텐츠 생성기")

# 1. 프롬프트 입력
prompt = st.text_area("블로그/광고용 프롬프트 입력", "")
keyword = st.text_input("키워드 입력", "")


# 2. 생성 실행
if st.button("생성하기"):
    if not prompt or not keyword:
        st.warning("프롬프트와 키워드를 모두 입력해주세요.")
    else:
        with st.spinner("모델 실행 중..."):
            try:
                st.session_state.ads = gen_ad(prompt, keyword)
            except Exception as e:
                st.error(f"글 생성 실패: {e}")
                st.session_state.ads = []

# 3. 생성된 글 선택
if st.session_state.ads:
    st.subheader("생성된 글 선택")
    st.session_state.selected_ad = st.radio(
        "마음에 드는 글을 선택하세요:",
        st.session_state.ads,
        index=0  # 기본 선택
    )

    # 선택된 글 출력
    st.subheader("선택된 글")
    st.text_area("선택된 글 내용", st.session_state.selected_ad, height=300)

    # 다운로드 버튼
    buf = io.BytesIO()

    st.download_button("선택된 글 다운로드", st.session_state.selected_ad,
                       file_name="selected_blog_text.txt", mime="text/plain")