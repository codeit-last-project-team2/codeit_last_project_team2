# frontend/app.py
# ---------------------------------------------------------
# Google OAuth 로그인 게이트 + 기존 광고 생성기 UI
# - 로그인 전: "Google로 로그인"만 노출
# - 로그인 후: 생성기 UI 표시
# - 로그인 완료 시/로그아웃 시: URL 쿼리스트링 정리(자동 재로그인 방지)
# ---------------------------------------------------------
import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"
st.set_page_config(page_title="AdGen", page_icon="🚀")
st.title("🚀 광고지 생성기 — (Login Guard ON)")

# -----------------------------
# 1) 로그인 바 (콜백 파라미터 처리 + 쿼리 정리)
# -----------------------------
params = st.query_params
def _qp(k):
    v = params.get(k)
    if isinstance(v, list): return v[0]
    return v

if "token" not in st.session_state:
    tok = _qp("token")
    if tok:
        st.session_state.token = tok
        st.session_state.user_name = _qp("name") or ""
        st.session_state.user_email = _qp("email") or ""
        # ✅ 콜백에서 받은 뒤 URL 파라미터 제거(자동 재로그인 방지)
        try:
            st.query_params.clear()
        except Exception:
            st.experimental_set_query_params()

colA, colB = st.columns(2)
with colA:
    if "token" in st.session_state:
        st.success(f"로그인됨: {st.session_state.get('user_name','')} ({st.session_state.get('user_email','')})")
    else:
        st.info("로그인이 필요합니다.")

with colB:
    if "token" in st.session_state:
        if st.button("로그아웃"):
            for k in ["token","user_name","user_email"]:
                st.session_state.pop(k, None)
            # ✅ 로그아웃 시에도 쿼리스트링 제거
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            st.rerun()
    else:
        st.link_button("Google로 로그인", f"{BACKEND_URL}/auth/google/login")

st.divider()

# -----------------------------
# 2) 인증 헤더가 붙는 API 헬퍼
# -----------------------------
def api_get(path, params=None):
    headers = {}
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.get(f"{BACKEND_URL}{path}", params=params, headers=headers, timeout=30)

def api_post(path, data=None, files=None):
    headers = {}
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.post(f"{BACKEND_URL}{path}", data=data, files=files, headers=headers, timeout=60)

# -----------------------------
# 3) 로그인 안 되었으면 여기서 종료
# -----------------------------
if "token" not in st.session_state:
    st.warning("로그인 후 이용할 수 있습니다.")
    st.stop()

# -----------------------------
# 4) 여기부터 '네가 만든 광고 생성기' UI
#    (requests → api_get/api_post 로만 바꿔서 사용)
# -----------------------------

# 상태 변수 초기화
for key, default in [
    ("suggestions", []),
    ("picked_text", ""),
    ("ai_image_url", None),
    ("poster_url", None),
    ("upload_file", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# 서버 상태 (선택)
with st.expander("서버 상태", expanded=False):
    try:
        r = api_get("/health")
        st.write(r.json())
    except Exception:
        st.warning("백엔드를 먼저 실행해줘: uvicorn backend.main:app --reload --port 8000")

# ---- STEP 1) 문구 → 추천 ----
st.header("STEP 1) 내 문구 입력 → 추천 문구 5개 생성")
base_line = st.text_input("내 문구", value="프리미엄 원두, 깊은 풍미를 담다.")

c1, c2 = st.columns(2)
with c1:
    if st.button("추천 5개 생성"):
        if not base_line.strip():
            st.warning("문구를 입력해줘!")
        else:
            with st.spinner("추천 생성 중..."):
                res = api_post("/generate_text_suggestions", data={"base_line": base_line.strip(), "n": 5})
                js = res.json()
            st.session_state.suggestions = js.get("texts", [])
            if st.session_state.suggestions:
                st.success("추천 5개 생성 완료!")
            else:
                st.error(f"생성 실패 또는 빈 응답: {js.get('error','')}")

with c2:
    if st.button("내 문구 바로 사용할래"):
        st.session_state.picked_text = base_line.strip()
        st.success("내 문구를 선택했어.")

if st.session_state.suggestions:
    st.subheader("추천 문구 중 하나 선택")
    choice = st.radio("선택", st.session_state.suggestions, index=0)
    if st.button("이 문구 선택"):
        st.session_state.picked_text = choice
        st.success(f"선택됨: {choice}")

st.write("---")
st.subheader("현재 사용할 문구 (수정 가능)")
st.session_state.picked_text = st.text_input(
    "최종 문구", value=st.session_state.picked_text or base_line
)

# ---- STEP 2) 이미지 선택/생성 ----
st.header("STEP 2) 이미지 선택/생성")
img_source = st.radio("이미지 소스",
                      ["AI로 생성(원본 그대로)", "깨끗한 포스터 생성(권장)", "내가 업로드"], index=1)

if img_source in ["AI로 생성(원본 그대로)", "깨끗한 포스터 생성(권장)"]:
    size = st.selectbox("AI 이미지 크기",
                        ["1024x1024", "1024x1536", "1536x1024", "auto"], index=0)

    c3, c4 = st.columns(2)
    with c3:
        if st.button("AI 이미지 생성(그대로)"):
            if not st.session_state.picked_text.strip():
                st.warning("먼저 문구를 선택/입력해줘!")
            else:
                with st.spinner("AI 이미지 생성 중..."):
                    res = api_post("/generate_ai_image",
                                   data={"ad_text": st.session_state.picked_text.strip(), "size": size})
                    js = res.json()
                if js.get("image_url"):
                    st.session_state.ai_image_url = js["image_url"]
                    st.image(js["image_url"], caption=f"AI 생성 이미지 ({size})")
                else:
                    st.error(f"이미지 생성 실패: {js.get('error','Unknown error')}")

    with c4:
        if st.button("깨끗한 포스터 바로 만들기 (배경+합성) ✅"):
            if not st.session_state.picked_text.strip():
                st.warning("먼저 문구를 선택/입력해줘!")
            else:
                with st.spinner("포스터 생성 중..."):
                    res = api_post("/generate_poster_from_text",
                                   data={"ad_text": st.session_state.picked_text.strip(), "size": size})
                    js = res.json()
                if js.get("result_url"):
                    st.session_state.poster_url = js["result_url"]
                    st.image(js["result_url"], caption="최종 광고지")
                    st.success("완료! 🔥")
                else:
                    st.error(f"생성 실패: {js.get('error','Unknown error')}")

else:
    upload = st.file_uploader("이미지 업로드 (png/jpg/jpeg)", type=["png", "jpg", "jpeg"])
    if upload:
        st.session_state.upload_file = upload
        st.image(upload, caption="업로드 미리보기", use_column_width=True)

# ---- STEP 3) 최종 합성 ----
st.header("STEP 3) 최종 광고지 만들기 (합성)")
final_text = st.text_area("최종 문구 확인 (수정 가능)",
                          value=st.session_state.picked_text or base_line, height=80)

if img_source == "AI로 생성(원본 그대로)":
    if st.button("AI 이미지로 합성"):
        if not st.session_state.ai_image_url:
            st.warning("먼저 AI 이미지를 생성해줘!")
        else:
            with st.spinner("합성 중..."):
                res = api_post("/compose_with_image_url",
                               data={"image_url": st.session_state.ai_image_url,
                                     "ad_text": final_text.strip()})
                js = res.json()
            if js.get("result_url"):
                st.image(js["result_url"], caption="최종 광고지")
                st.success("완료! 🔥")
            else:
                st.error(f"합성 실패: {js.get('error','Unknown error')}")

elif img_source == "내가 업로드":
    if st.button("업로드 이미지로 합성"):
        if not st.session_state.upload_file:
            st.warning("이미지를 업로드해줘!")
        else:
            with st.spinner("합성 중..."):
                res = api_post("/compose_with_upload",
                               files={"file": st.session_state.upload_file},
                               data={"ad_text": final_text.strip()})
                js = res.json()
            if js.get("result_url"):
                st.image(js["result_url"], caption="최종 광고지")
                st.success("완료! 🔥")
            else:
                st.error(f"합성 실패: {js.get('error','Unknown error')}")
else:
    st.info("위의 ‘깨끗한 포스터 바로 만들기’ 버튼으로 이미 최종 이미지가 만들어집니다 😊")
