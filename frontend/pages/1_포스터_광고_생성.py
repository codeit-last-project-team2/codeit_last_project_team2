import streamlit as st
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os, datetime

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

# ✅ 공통 도움말
with st.expander("💡 광고 프롬프트 작성 가이드 보기"):
    st.markdown("AI가 잘 이해하도록 감정과 장면을 구체적으로 써주세요.")

# -----------------------------
# 광고 유형별 입력
# -----------------------------
if ad_type == "브랜드":
    brand_desc = st.text_area("브랜드에 대한 설명", placeholder="예: 친환경 원두를 사용하는 감성 카페입니다.")
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
vibe = st.text_input("광고 분위기 / 스타일", placeholder="예: 따뜻한 햇살 아래 가족 피크닉 느낌, 파스텔톤 일러스트")

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
    try:
        preview_text = "포스터 광고 예시 텍스트"
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
position = st.selectbox("제목 위치 선택", ["top", "center", "bottom"], index=0)
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
            "stroke_color_title": "#000000",
            "stroke_color_body": "#000000",
            "stroke_width_title": 2,
            "stroke_width_body": 2
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
# 📂 히스토리 불러오기
# -----------------------------
st.divider()
st.subheader("📜 내가 만든 포스터 히스토리")

if st.button("📂 히스토리 불러오기"):
    try:
        res = requests.get(f"{BACKEND_URL}/poster/history", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("history", [])
            st.session_state.poster_history = []

            for item in data:
                path = item.get("image_path")
                if path and os.path.exists(path):
                    with open(path, "rb") as f:
                        img_bytes = f.read()
                    st.session_state.poster_history.append({
                        "title": item["text"].split("\n")[0],
                        "body": "\n".join(item["text"].split("\n")[1:]),
                        "dalle_prompt": "",
                        "image_bytes": img_bytes
                    })
            st.success(f"✅ {len(st.session_state.poster_history)}개의 포스터를 불러왔습니다!")
        else:
            st.error("❌ 히스토리 요청 실패")
    except Exception as e:
        st.error(f"요청 오류: {e}")

# -----------------------------
# 히스토리 표시 (선택버튼 제거)
# -----------------------------
if st.session_state.poster_history:
    for i, ad in enumerate(reversed(st.session_state.poster_history), 1):
        st.write(f"### {i}. {ad['title']}")
        st.write(ad["body"])
        st.image(BytesIO(ad["image_bytes"]), caption="포스터", use_container_width=True)
        st.download_button(
            f"📥 다운로드 {i}",
            data=ad["image_bytes"],
            file_name=f"poster_{i}.png",
            mime="image/png"
        )
else:
    st.info("아직 생성된 포스터 히스토리가 없습니다.")
