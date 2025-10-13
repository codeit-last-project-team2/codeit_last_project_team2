import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="매장 관리", layout="wide")
st.title("🏪 매장 관리")

# 로그인 체크
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()   

headers = {"Authorization": f"Bearer {st.session_state.token}"}
user_email = st.session_state.get("user_email")

profile = st.session_state.store_profile

st.markdown("### ✏️ 매장 정보 입력/수정")

col1, col2 = st.columns(2)

with col1:
    store_name = st.text_input(
        "당신의 매장 이름은 무엇인가요?",
        value=profile.get("store_name", "")
    )
    category = st.text_input(
        "어떤 업종에 해당하나요? (예: 카페, 음식점, 소매점)",
        value=profile.get("category", "")
    )

with col2:
    phone = st.text_input(
        "고객이 연락할 수 있는 전화번호를 입력해주세요.",
        value=profile.get("phone", "")
    )
    address = st.text_input(
        "매장은 어디에 위치해 있나요?",
        value=profile.get("address", "")
    )

# 저장 버튼
if st.button("💾 매장 정보 저장"):
    payload = {
        "email": user_email,
        "store_name": store_name,
        "category": category,
        "phone": phone,
        "address": address
    }
    r = requests.post(f"{BACKEND_URL}/userinfo/save", json=payload, headers=headers)
    if r.status_code == 200:
        st.success("✅ 매장 정보가 저장되었습니다.")
        st.session_state.store_profile = payload
    else:
        st.error("❌ 저장 중 오류가 발생했습니다.")

st.divider()

# 매장 정보
st.markdown("### 👀 매장 정보")

profile = st.session_state.store_profile

with st.container():
    st.markdown(
        f"""
        <div style="
            background-color:#f9f9f9;
            border-radius:12px;
            padding:20px;
            box-shadow:0 2px 6px rgba(0,0,0,0.1);
            font-size:16px;
            line-height:1.6;
        ">
            <p>🏷️ 매장 이름은 <b>{profile.get("store_name", "미입력")}</b> 입니다.</p>
            <p>📂 업종은 <b>{profile.get("category", "미입력")}</b> 이고,</p>
            <p>📞 매장 연락처는 <b>{profile.get("phone", "미입력")}</b> 입니다.</p>
            <p>📍 매장은 <b>{profile.get("address", "미입력")}</b> 에 위치해 있습니다.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.caption("💡 저장된 정보는 포스터/카드뉴스/홈페이지/마스코트에서 자동으로 사용됩니다.")
