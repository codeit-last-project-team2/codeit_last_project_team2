import streamlit as st
import openai

# ==== OpenAI API 키 설정 ====
openai.api_key = ""

# ==== 블로그 글 생성 함수 ====
def gen_blog(store, product, event, audience, style, max_tokens=1024, temperature=0.8):
    prompt = f"""
너는 한국어 블로그 전문 작가야.  
가게명: {store}  
상품명: {product}  
이벤트/프로모션: {event}  
대상 고객: {audience}  
스타일: {style}  

형식:
1. 도입부 (가게/상품 소개, 200자 내외)
2. 본문 (소제목 2개 이상, 각 소제목 150자 이상, 이벤트/상품 특장점 설명)
3. 결론 (행동 유도 문구 포함, 100자 내외)
"""
    response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "당신은 블로그 전문 작가입니다."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()

# ==== Streamlit UI ====
st.title("📢 소상공인 맞춤 블로그 글 자동 생성기")

# 입력값 받기
store = st.text_input("🏪 가게명", placeholder="예: 강남 수제버거")
product = st.text_input("🍔 상품명", placeholder="예: 치즈버거 세트")
event = st.text_input("🎉 이벤트/프로모션", placeholder="예: 9월 한정 1+1 이벤트")
audience = st.text_input("👥 대상 고객", placeholder="예: 20~30대 직장인")

st.subheader("✍️ 글 스타일 선택")
preset_styles = {
    "대화체": "친근하고 대화하듯 편안한 톤",
    "전문적": "논리적이고 신뢰감 있는 톤",
    "감성적": "따뜻하고 감성적인 톤",
    "유머러스": "재미있고 위트있는 톤"
}

selected_styles = []
for name, desc in preset_styles.items():
    if st.checkbox(f"{name} ({desc})"):
        selected_styles.append(desc)

custom_style = st.text_input("📝 직접 입력 (원하는 스타일이 없다면)", "")

# 최종 스타일 결정
if custom_style:
    style = custom_style
elif selected_styles:
    style = ", ".join(selected_styles)
else:
    style = "일반적인 블로그 톤"

temperature = st.slider("창의성 (temperature)", 0.0, 1.0, 0.8)

# 생성 버튼
if st.button("🚀 블로그 글 생성하기"):
    if not store or not product or not audience:
        st.warning("⚠️ 가게명, 상품명, 대상 고객은 반드시 입력해주세요.")
    else:
        with st.spinner("블로그 글 생성 중..."):
            try:
                blog_text = gen_blog(store, product, event, audience, style, temperature=temperature)
                st.subheader("✨ 생성된 블로그 글")
                st.text_area("결과", blog_text, height=500)

                # 다운로드 버튼
                st.download_button(
                    "⬇️ 블로그 글 다운로드",
                    blog_text,
                    file_name=f"{store}_blog_post.txt",
                    mime="text/plain"
                )
            except Exception as e:
                st.error(f"블로그 생성 실패: {e}")
