import streamlit as st
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os, datetime

from utils.init_session import init_common_session
init_common_session()

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="포스터 광고 생성", page_icon="🖼️", layout="wide")
st.title("🖼️ 포스터 광고 생성")

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
# 세션 상태 초기화
# -----------------------------
if "poster_history" not in st.session_state:
    st.session_state.poster_history = []

# -----------------------------
# 광고 유형 선택
# -----------------------------
st.markdown("### 🎯 광고 세부 정보 입력")
ad_type = st.radio("광고할 대상 선택", ["브랜드", "제품", "이벤트"], horizontal=True)

# ✅ 공통 도움말 (브랜드 설명 + 분위기/스타일)
with st.expander("💡 광고 프롬프트 작성 가이드 보기"):
    st.markdown("""
    ### 🏪 브랜드 설명 & 🎨 광고 분위기·스타일 작성 가이드

    AI는 **텍스트로부터 장면을 상상하는 능력**이 매우 뛰어납니다.  
    아래와 같은 방식으로 **시각적인 설명 중심의 문장**을 작성하면  
    훨씬 더 높은 품질의 광고 이미지를 얻을 수 있습니다.  

    ---

    #### 🏪 **1️⃣ 브랜드 설명 작성 방법**
    👉 브랜드의 정체성과 감정을 담아 작성하세요.
    - **포함할 내용 예시**
      - 브랜드의 특징 (예: 친환경, 전통, 프리미엄, 가족 중심)
      - 주요 제품 또는 서비스 (예: 수제 햄버거, 원두 커피, 수공예품)
      - 고객에게 주는 인상 (예: 따뜻함, 신뢰감, 활기, 감성적임)
    - **예시 문장**
      - “따뜻한 분위기의 수제 버거 전문점으로, 가족이 함께 즐길 수 있는 편안한 공간이에요.”
      - “감성적인 디자인과 천연 재료로 만든 수공예 향초 브랜드입니다.”
      - “도심 속에서 느끼는 프리미엄 카페, 부드러운 조명과 향긋한 커피 향이 매력적이에요.”

    ---

    #### 🎨 **2️⃣ 광고 분위기 / 이미지 스타일 작성 방법**
    👉 장면과 시각적인 톤을 함께 설명하면 AI가 훨씬 더 정확히 이해합니다.

    - **작성 구조 예시**
      ```
      [광고 목적/대상] + [장면 묘사] + [스타일] + [색감/조명]
      ```
    - **스타일 추천 키워드**
      - 📸 사진 느낌: 현실적인, 영화 조명 같은, 제품 촬영 같은, 흐릿한 배경  
      - 🎨 일러스트 느낌: 수채화, 플랫 디자인, 만화풍, 3D 렌더링, 벡터 아트  
      - 🌈 감정 톤: 따뜻한, 아늑한, 밝은, 활기찬, 미니멀한, 고급스러운, 파스텔 톤  
      - 💡 조명 분위기: 햇살, 네온 조명, 스튜디오 배경, 빛 번짐 효과
    - **예시 문장**
      - “따뜻한 햇살 아래 가족이 함께 있는 버거 광고, 파스텔톤의 일러스트 스타일”
      - “고급스러운 와인 광고, 어두운 배경에 금빛 조명, 영화 같은 분위기”
      - “밝고 활기찬 여름 아이스크림 포스터, 만화풍 스타일, 선명한 색감”

    ---

    #### ✨ **3️⃣ AI가 좋아하는 문장 예시**
    - “따뜻한 가족 버거 매장 광고, 파스텔톤의 일러스트 느낌, 웃는 사람들”
    - “럭셔리 향수 광고, 어두운 배경, 고급스러운 조명, 간결한 구도”
    - “활기찬 여름 아이스크림 포스터, 만화풍 스타일, 부드러운 그림자 효과”

    ---

    💬 **Tip:**  
    - 감정(느낌) + 시각적 스타일을 함께 써주세요.  
      → 예: “따뜻한 + 수채화”, “고급스러운 + 영화조명”  
    - 한국어로 자연스럽게 써도 충분합니다.  
    - 예: “따뜻한 햇살 아래 감성적인 카페, 파스텔톤 수채화 스타일”  
      이런 식으로 길게 써줄수록 더 정확한 이미지를 생성할 수 있습니다.
    """)

# -----------------------------
# 광고 유형별 입력
# -----------------------------
if ad_type == "브랜드":
    brand_desc = st.text_area(
        "브랜드에 대한 설명",
        placeholder="예: 친환경 원두를 사용하는 감성 카페로, 부드러운 조명과 향긋한 커피 향이 특징이에요."
    )
    extra_inputs = {"brand_desc": brand_desc}

elif ad_type == "제품":
    product_name = st.text_input("제품명", placeholder="예: 수제 햄버거")
    product_feature = st.text_area("특징/장점", placeholder="예: 신선한 재료, 부드러운 식감, 정성 가득한 수제버거")
    extra_inputs = {"product_name": product_name, "product_feature": product_feature}

else:
    start_date, end_date = st.date_input("이벤트 기간", value=(datetime.date.today(), datetime.date.today()))
    event_desc = st.text_area("이벤트 내용", placeholder="예: 10월 한정 30% 할인 행사")
    extra_inputs = {
        "event_period": [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")],
        "event_desc": event_desc,
    }

# -----------------------------
# 분위기/스타일 입력
# -----------------------------
vibe = st.text_input(
    "광고 분위기 / 스타일",
    placeholder="예: 따뜻한 햇살 아래 가족 피크닉 느낌, 파스텔톤 수채화 일러스트"
)

# -----------------------------
# 텍스트 스타일 옵션
# -----------------------------
st.markdown("### ✍️ 텍스트 스타일 설정")

col1, col2 = st.columns(2)
with col1:
    title_color = st.color_picker("제목 색상", "#FFFFFF")
    body_color = st.color_picker("본문 색상", "#FFFF00")
with col2:
    title_font_size = st.slider("제목 폰트 크기", 40, 120, 80)
    body_font_size = st.slider("본문 폰트 크기", 30, 80, 50)

# -----------------------------
# 🎨 폰트 선택 및 미리보기
# -----------------------------
font_dir = "data/fonts"
fonts = [f for f in os.listdir(font_dir) if f.lower().endswith(".ttf")]

if fonts:
    selected_font = st.selectbox("폰트 선택", fonts, index=0)
    font_path = os.path.join(font_dir, selected_font)

    st.markdown("##### ✨ 폰트 미리보기")
    preview_text = "포스터 광고 예시 텍스트"

    try:
        font = ImageFont.truetype(font_path, 50)
        img = Image.new("RGB", (800, 150), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), preview_text, font=font, fill=(255, 255, 255))
        st.image(img, caption=f"{selected_font} 폰트 미리보기", use_container_width=False)
    except Exception as e:
        st.error(f"⚠️ 폰트 로드 실패: {e}")
else:
    st.warning("⚠️ data/fonts 폴더에 폰트(.ttf)가 없습니다.")
    selected_font = None

# -----------------------------
# 기타 설정
# -----------------------------
position = st.selectbox("제목 위치 선택", ["상단", "중앙", "하단"], index=0)
dalle_size = st.selectbox("이미지 크기", ["1024x1024", "1024x1792", "1792x1024"], index=0)

go = st.button("🎨 포스터 생성", type="primary")

# -----------------------------
# 요청 전송 및 결과 표시
# -----------------------------
if go:
    with st.spinner("포스터 생성 중..."):
        payload = {
            "email": st.session_state.get("user_email"),
            "store_name": store.get("store_name", ""),
            "category": store.get("category", ""),
            "phone": store.get("phone", ""),
            "address": store.get("address", ""),
            "vibe": vibe or "분위기 미정",
            "ad_type": ad_type,
            "font_name": selected_font or "",
            **extra_inputs,
        }

        text_res = requests.post(f"{BACKEND_URL}/poster/text", json=payload, headers=headers)
        if text_res.status_code != 200:
            st.error("❌ 텍스트 생성 실패")
            st.stop()
        text_data = text_res.json()

        image_payload = {
            "title": text_data["title"],
            "body": text_data["body"],
            "dalle_prompt": text_data["dalle_prompt"],
            "position": position,
            "dalle_size": dalle_size,
            "title_color": title_color,
            "body_color": body_color,
            "title_font_size": title_font_size,
            "body_font_size": body_font_size,
            "font_name": selected_font or "",
        }

        img_res = requests.post(f"{BACKEND_URL}/poster/image", json=image_payload, headers=headers)
        if img_res.status_code != 200:
            st.error("❌ 이미지 생성 실패")
            st.stop()

        img_bytes = BytesIO(img_res.content)
        st.session_state.poster_history.append({
            "title": text_data["title"],
            "body": text_data["body"],
            "dalle_prompt": text_data["dalle_prompt"],
            "image_bytes": img_bytes.getvalue()
        })
        st.success("✅ 포스터 생성 완료!")

# -----------------------------
# 히스토리
# -----------------------------
if st.session_state.poster_history:
    st.subheader("📜 내가 만든 포스터 히스토리")
    for i, ad in enumerate(reversed(st.session_state.poster_history), 1):
        st.write(f"### {i}. {ad['title']}")
        st.write(ad["body"])
        st.code(ad["dalle_prompt"], language="json")
        st.image(BytesIO(ad["image_bytes"]), caption="포스터", use_container_width=True)
        st.download_button(
            f"📥 다운로드 {i}",
            data=ad["image_bytes"],
            file_name=f"poster_{i}.png",
            mime="image/png"
        )
