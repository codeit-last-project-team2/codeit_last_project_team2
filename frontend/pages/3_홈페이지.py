import streamlit as st
import requests, json, time

BACKEND_URL = "http://127.0.0.1:8000"

st.title("가게 홈페이지 자동 생성기")
# -----------------------------
# 세션 값 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

with st.form("mascot_form"):
    st.subheader("매장 선택")
    store_list_res = requests.get(f"{BACKEND_URL}/userinfo/get_store_names", headers=headers)

    if store_list_res.status_code != 200:
        st.error(f"조회 실패, error code: {store_list_res.status_code}")
        st.stop()
    else:
        stores = store_list_res.json()

    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
        make = st.form_submit_button('홈페이지 생성', disabled=True)
        st.stop()
    else:
        selected_store = st.radio("매장을 선택하세요:", stores, horizontal=True)

    store_info_res = requests.post(f"{BACKEND_URL}/userinfo/get_store_info", json={"user_email": st.session_state.get("user_email"), "store_name": selected_store}, headers=headers)

    if store_info_res.status_code != 200:
        st.error("조회 실패")
        st.text(store_info_res.status_code)
    else:
        store_info = store_info_res.json()

    if isinstance(store_info["menus"], str):
        store_info["menus"] = json.loads(store_info["menus"])
    if isinstance(store_info["targets"], str):
        store_info["targets"] = json.loads(store_info["targets"])
    if isinstance(store_info["selling_points"], str):
        store_info["selling_points"] = json.loads(store_info["selling_points"])

    # 샘플 문서
    sample_id = st.selectbox("참고 템플릿 선택", options=['1'])
    store_info['sample_id'] = sample_id

    st.markdown("[템플릿 1 보기](https://codeit-last-project-team2.github.io/homepage/sample_pages/sample1.html)")
    make = st.form_submit_button('홈페이지 생성')

# -----------------------------
# 실행
# -----------------------------
if make:
    st.info("홈페이지를 생성 중입니다...")

    # --- HTML 템플릿 생성 ---
    html_res = requests.post(f"{BACKEND_URL}/homepage/generate", json=store_info, headers=headers)

    if html_res.status_code != 200:
        st.error(f"홈페이지 생성 실패: {html_res.text}")
    else:
        html = html_res.json() 
    try:
        github_req = {
            'html': html,
            'email': store_info.get('email'),
            'store_name': store_info.get('store_name')
        }

        homepage_res = requests.post(f"{BACKEND_URL}/homepage/upload", json=github_req, headers=headers)
        if homepage_res.status_code != 200:
            st.error(f"홈페이지 업로드 실패: {homepage_res.text}")
            st.stop()

        homepage_url = homepage_res.json()

        st.success("✅ GitHub에 홈페이지 업로드 요청 완료!")
        st.info("GitHub Pages가 활성화되기까지 기다리는 중...")

        # 최대 60초 동안 확인
        for i in range(12):
            try:
                resp = requests.get(homepage_url, timeout=5)
                if resp.status_code == 200:
                    st.success("🌍 홈페이지가 준비되었습니다!")
                    st.markdown(f"[홈페이지 보러가기]({homepage_url})")
                    break
            except:
                pass
            time.sleep(5)
        else:
            st.warning("아직 준비되지 않았습니다. 몇 분 뒤 다시 시도해주세요.")
            st.text(f"홈페이지 주소: {homepage_url}")

    except Exception as e:
        st.error(f"업로드 중 오류 발생: {e}")