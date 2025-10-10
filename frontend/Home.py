import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="홈", page_icon="🏠", layout="wide")
st.title("🏠 홈")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# -----------------------------
# 쿼리 파라미터 (Google OAuth 리다이렉트 시 사용)
# -----------------------------
params = st.query_params

def _qp(k):
    v = params.get(k)
    if isinstance(v, list):
        return v[0]
    return v

# -----------------------------
# 로그인 성공 시 세션 업데이트
# -----------------------------
tok = _qp("token")
if tok:
    st.session_state.token = tok
    st.session_state.user_name = _qp("name") or ""
    st.session_state.user_email = _qp("email") or ""

    # ✅ 로그인 직후 매장 정보 자동 불러오기
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        email = st.session_state.user_email
        r = requests.get(f"{BACKEND_URL}/userinfo/{email}", headers=headers)
        if r.status_code == 200:
            data = r.json()
            if "message" not in data:
                st.session_state.store_profile = data
            else:
                st.session_state.store_profile = {
                    "store_name": "",
                    "category": "",
                    "phone": "",
                    "address": "",
                }
        else:
            st.session_state.store_profile = {
                "store_name": "",
                "category": "",
                "phone": "",
                "address": "",
            }
    except Exception:
        st.session_state.store_profile = {
            "store_name": "",
            "category": "",
            "phone": "",
            "address": "",
        }

    # ✅ URL 정리 (쿼리 파라미터 제거)
    try:
        st.query_params.clear()
    except Exception:
        pass

# -----------------------------
# 로그인 상태에 따른 UI
# -----------------------------
if st.session_state.token:
    st.success(f"✅ 로그인됨: {st.session_state.user_email}")

    # 매장 정보 미리보기
    if "store_profile" in st.session_state and st.session_state.store_profile.get("store_name"):
        info = st.session_state.store_profile
        st.markdown(f"""
        **🏪 매장명:** {info.get('store_name')}  
        **📞 전화번호:** {info.get('phone', '-')}  
        **📍 주소:** {info.get('address', '-')}  
        """)
    else:
        st.info("ℹ️ 매장 정보가 아직 없습니다. 매장 관리 페이지에서 입력해주세요.")

    # 로그아웃
    if st.button("로그아웃"):
        for k in ["token", "user_email", "user_name", "store_profile"]:
            st.session_state[k] = None
        st.rerun()

else:
    # -----------------------------
    # 로그인 / 회원가입 UI
    # -----------------------------
    tab_login, tab_register = st.tabs(["🔑 로그인", "📝 회원가입"])

    # --- 로그인 탭 ---
    with tab_login:
        st.subheader("이메일 로그인")
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인"):
            res = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": email, "password": password}
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.token = data["token"]
                st.session_state.user_email = email
                st.session_state.user_name = data.get("name", email.split("@")[0])

                # ✅ 로그인 직후 매장정보 불러오기
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    r = requests.get(f"{BACKEND_URL}/userinfo/{email}", headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        if "message" not in data:
                            st.session_state.store_profile = data
                except:
                    pass

                st.success("✅ 로그인 성공!")
                st.experimental_rerun()
            else:
                st.error("❌ 로그인 실패. 이메일/비밀번호를 확인하세요.")

        st.markdown("---")
        st.markdown("또는 ↓")
        st.link_button("🔗 Google로 로그인", f"{BACKEND_URL}/auth/google/login")

    # --- 회원가입 탭 ---
    with tab_register:
        st.subheader("회원가입")
        reg_email = st.text_input("이메일", key="reg_email")
        reg_pw = st.text_input("비밀번호", type="password", key="reg_pw")
        reg_name = st.text_input("이름", key="reg_name")
        if st.button("회원가입"):
            res = requests.post(
                f"{BACKEND_URL}/auth/register",
                json={"email": reg_email, "password": reg_pw, "name": reg_name}
            )
            if res.status_code == 200:
                st.success("✅ 회원가입 완료! 로그인 탭에서 로그인하세요.")
            else:
                st.error("❌ 회원가입 실패. 이미 존재하는 이메일일 수 있습니다.")
