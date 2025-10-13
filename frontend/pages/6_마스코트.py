import streamlit as st
import requests
from io import BytesIO
from PIL import Image
import io

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="마스코트 생성", layout="wide")
st.title("🎨 마스코트 생성")

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
# 추가 입력 UI
# -----------------------------
st.markdown("### 🧸 마스코트 정보 입력")

main_color = st.text_input("대표 색상", placeholder="예: 파스텔 블루")
keyword = st.text_input("키워드", placeholder="예: 귀여움, 친근함, 동물")
personality = st.text_input("성격", placeholder="예: 밝고 긍정적")
output_style = st.text_input("출력 스타일", placeholder="예: 3D 캐릭터, 일러스트, 심플 로고")
additional = st.text_area("추가 요구사항 (선택)", placeholder="예: 매장 로고와 어울리게 제작해주세요")

go = st.button("🎨 마스코트 생성", type="primary")

# -----------------------------
# 실행
# -----------------------------
def fetch_image_and_bytes(url: str):
    """URL에서 이미지를 받아 PIL.Image로 로드하고 PNG/JPG 바이트를 모두 반환."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")  # 투명 채널 대비

    # PNG 바이트
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    png_bytes = png_buf.getvalue()

    # JPG 바이트 (JPG는 알파 채널 없음)
    jpg_buf = io.BytesIO()
    img_rgb = img.convert("RGB")
    img_rgb.save(jpg_buf, format="JPEG", quality=95)
    jpg_bytes = jpg_buf.getvalue()

    return img, png_bytes, jpg_bytes

if go:
    with st.spinner("마스코트 생성 중..."):
        payload = {
            "user_email": st.session_state.get("user_email"),
            "store_name": store.get("store_name", ""),
            "category": store.get("category", ""),
            "main_color": main_color,
            "keyword": keyword,
            "mascot_personality": personality,
            "output_style": output_style,
            "additional_requirements": additional,
        }

        res = requests.post(f"{BACKEND_URL}/mascot/generate", json=payload, headers=headers)
        if res.status_code != 200:
            st.error("❌ 마스코트 생성 실패")
            st.stop()

        # 서버 응답: 이미지 URL 리스트
        image_urls = res.json()
        if not image_urls:
            st.warning("생성된 이미지가 없습니다.")
            st.stop()

    st.success("✅ 마스코트 후보가 생성되었습니다!")
    st.markdown("### 🐱 생성된 마스코트 후보들")

    cols = st.columns(len(image_urls))

    for i, url in enumerate(image_urls):
        with cols[i % len(cols)]:
            try:
                img, png_bytes, jpg_bytes = fetch_image_and_bytes(url)
            except Exception as e:
                st.error(f"이미지 로드 실패({i+1}번): {e}")
                continue

            st.image(img, caption=f"{i+1}번", use_container_width=True)

            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                fname_base = (store.get("store_name") or "mascot").strip().replace(" ", "_")
                st.download_button(
                    label="⬇️ PNG 다운로드",
                    data=png_bytes,
                    file_name=f"{fname_base}_{i+1}.png",
                    mime="image/png",
                    key=f"dl_png_{i}",
                )
            with sub_col2:
                st.download_button(
                    label="⬇️ JPG 다운로드",
                    data=jpg_bytes,
                    file_name=f"{fname_base}_{i+1}.jpg",
                    mime="image/jpeg",
                    key=f"dl_jpg_{i}",
                )

    