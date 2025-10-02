# import streamlit as st
# import requests

# BACKEND_URL = "http://127.0.0.1:8000"

# st.set_page_config(page_title="홈페이지 생성", layout="wide")
# st.title("🌐 홈페이지 생성")

# if not st.session_state.get("token"):
#     st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
#     st.stop()

# headers = {"Authorization": f"Bearer {st.session_state.token}"}
# store = st.session_state.get("store_profile", {})

# menus = []
# st.subheader("메뉴 입력")
# menu_count = st.number_input("메뉴 개수", min_value=1, max_value=10, value=3)

# for i in range(menu_count):
#     st.markdown(f"#### 메뉴 {i+1}")
#     name = st.text_input(f"메뉴명 {i+1}", key=f"menu_name_{i}")
#     price = st.text_input(f"가격 {i+1}", key=f"menu_price_{i}")
#     feature = st.text_area(f"특징/장점 {i+1}", key=f"menu_feature_{i}")
#     if name and price:
#         menus.append({"name": name, "price": price, "feature": feature})

# style = st.text_input("홈페이지 톤앤매너", placeholder="예: 모던하고 심플한 스타일")
# purpose = st.text_input("홈페이지 목적", placeholder="예: 가게 홍보, 신규 고객 유치")

# if st.button("홈페이지 생성", type="primary"):
#     payload = {
#         "email": st.session_state.get("user_email"),
#         "store_name": store.get("store_name", ""),
#         "category": store.get("category", ""),
#         "phone": store.get("phone", ""),
#         "address": store.get("address", ""),
#         "menus": menus,
#         "style": style,
#         "purpose": purpose,
#     }
#     r = requests.post(f"{BACKEND_URL}/homepage/generate", json=payload, headers=headers)
#     if r.status_code == 200:
#         st.success("홈페이지가 생성되었습니다 ✅")
#         st.download_button("📥 HTML 다운로드", r.content, file_name="homepage.html", mime="text/html")
#     else:
#         st.error("생성 실패")
