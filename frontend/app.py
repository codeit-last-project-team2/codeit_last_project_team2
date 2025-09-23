# ---------------------------------------------------------
# Streamlit Frontend (Slim)
# - STEP1: GPT 문구 추천
# - STEP2: 이미지 생성(원본 / 깔끔포스터)
# - 히스토리(보기/다운로드/삭제/벌크삭제)
# - 합성/업로드 기능 제거
# ---------------------------------------------------------
import os, base64, requests, streamlit as st

BACKEND_URL  = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
TIMEOUT_GET  = 30
TIMEOUT_POST = 60

st.set_page_config(page_title="AdGen (Slim)", page_icon="🚀", layout="wide")
st.title("🚀 광고지 생성기 — Slim")

def _qp(params, k):
    v = params.get(k)
    return v[0] if isinstance(v, list) else v

def _auth_headers():
    h = {}
    if "token" in st.session_state:
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h

def api_get(path, params=None):
    r = requests.get(f"{BACKEND_URL}{path}", params=params, headers=_auth_headers(), timeout=TIMEOUT_GET)
    r.raise_for_status(); return r

def api_post(path, data=None, files=None):
    r = requests.post(f"{BACKEND_URL}{path}", data=data, files=files, headers=_auth_headers(), timeout=TIMEOUT_POST)
    r.raise_for_status(); return r

def api_post_json(path, json_body=None):
    r = requests.post(f"{BACKEND_URL}{path}", json=json_body, headers=_auth_headers(), timeout=TIMEOUT_POST)
    r.raise_for_status(); return r

def api_delete(path, params=None):
    r = requests.delete(f"{BACKEND_URL}{path}", params=params, headers=_auth_headers(), timeout=TIMEOUT_POST)
    r.raise_for_status(); return r

def _clear_qs():
    try: st.query_params.clear()
    except Exception: st.experimental_set_query_params()

def _logout():
    for k in ["token","user_name","user_email","suggestions","picked_text","ai_image_url","poster_url"]:
        st.session_state.pop(k, None)
    _clear_qs(); st.rerun()

def _ensure_token_valid():
    try:
        js = api_get("/me").json()
        user = js.get("user", {})
        if not user.get("email"): raise ValueError("invalid user")
        st.session_state.user_name  = user.get("name",  st.session_state.get("user_name",""))
        st.session_state.user_email = user.get("email", st.session_state.get("user_email",""))
        return True
    except Exception:
        _logout(); return False

# ---- 콜백 흡수: token 있으면 교체
params = st.query_params
tok = _qp(params, "token")
if tok and (st.session_state.get("token") != tok):
    st.session_state.token = tok
    st.session_state.user_name  = _qp(params, "name")  or ""
    st.session_state.user_email = _qp(params, "email") or ""
    for k in ["suggestions","picked_text","ai_image_url","poster_url"]:
        st.session_state.pop(k, None)
    _clear_qs()
    st.rerun()

# ---- 상단 바
left, right = st.columns([0.65, 0.35])
with left:
    if "token" in st.session_state:
        st.success(f"로그인됨: {st.session_state.get('user_name','')} ({st.session_state.get('user_email','')})")
    else:
        st.info("로그인이 필요합니다.")
with right:
    if "token" in st.session_state:
        if st.button("로그아웃"): _logout()
    else:
        st.link_button("Google로 로그인", f"{BACKEND_URL}/auth/google/login", use_container_width=True)

st.divider()

# ---- 로컬 회원가입/로그인 (간단폼)
if "token" not in st.session_state:
    st.subheader("또는 이메일로 이용하기")
    tab1, tab2 = st.tabs(["회원가입", "로그인"])
    with tab1:
        su_email = st.text_input("Email (회원가입)")
        su_name  = st.text_input("Name (선택)")
        su_pw    = st.text_input("Password (6자 이상)", type="password")
        if st.button("계정 만들기"):
            try:
                r = requests.post(f"{BACKEND_URL}/auth/signup",
                                  json={"email": su_email, "password": su_pw, "name": su_name},
                                  timeout=TIMEOUT_POST)
                if r.status_code >= 400: st.error(r.json().get("detail", "Signup failed"))
                else:
                    js = r.json()
                    st.session_state.token = js["token"]
                    st.session_state.user_name  = js.get("name","")
                    st.session_state.user_email = js.get("email","")
                    st.success("회원가입 & 로그인 완료!")
                    st.rerun()
            except Exception as e:
                st.error(f"Signup error: {e}")
    with tab2:
        li_email = st.text_input("Email (로그인)")
        li_pw    = st.text_input("Password", type="password")
        if st.button("로그인"):
            try:
                r = requests.post(f"{BACKEND_URL}/auth/login",
                                  json={"email": li_email, "password": li_pw},
                                  timeout=TIMEOUT_POST)
                if r.status_code >= 400: st.error(r.json().get("detail", "Login failed"))
                else:
                    js = r.json()
                    st.session_state.token = js["token"]
                    st.session_state.user_name  = js.get("name","")
                    st.session_state.user_email = js.get("email","")
                    st.success("로그인 완료!")
                    st.rerun()
            except Exception as e:
                st.error(f"Login error: {e}")

# ---- 미로그인 가드
if "token" not in st.session_state:
    st.warning("로그인 후 이용할 수 있습니다."); st.stop()
if not _ensure_token_valid():
    st.warning("세션 만료 또는 유효하지 않음. 다시 로그인해주세요."); st.stop()

# ---- 상태
for key, default in [("suggestions", []), ("picked_text", ""), ("ai_image_url", None), ("poster_url", None)]:
    if key not in st.session_state: st.session_state[key] = default

# ---- 서버 상태
with st.expander("서버 상태 / Health", expanded=False):
    try: st.json(api_get("/health").json())
    except Exception as e: st.warning(f"백엔드 실행 필요: uvicorn backend:app --reload --port 8000\n{e}")

# ---- STEP 1: 카피 추천
st.header("STEP 1) 내 문구 입력 → GPT 추천")
base_line = st.text_input("내 문구", value=st.session_state.get("picked_text") or "프리미엄 원두, 깊은 풍미를 담다.")

c1, c2 = st.columns(2)
with c1:
    if st.button("추천 생성 (GPT)"):
        if not base_line.strip():
            st.warning("문구를 입력해줘!")
        else:
            with st.spinner("추천 생성 중..."):
                try:
                    js = api_post("/generate_text_suggestions",
                                  data={"base_line": base_line.strip(), "n": 6}).json()
                    st.session_state.suggestions = js.get("texts", [])
                    if st.session_state.suggestions: st.success("추천 생성 완료!")
                    else: st.error(f"빈 응답: {js.get('error','')}")
                except requests.HTTPError as he:
                    st.error(f"요청 실패: {he.response.text}")
                except Exception as e:
                    st.error(f"에러: {e}")

with c2:
    if st.button("내 문구 바로 사용"):
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
st.session_state.picked_text = st.text_input("최종 문구", value=st.session_state.picked_text or base_line)

# ---- STEP 2: 이미지 생성 (합성 제거)
st.header("STEP 2) 이미지 생성")
size    = st.selectbox("이미지 크기", ["1024x1024", "1024x1792", "1792x1024"], index=0)
quality = st.selectbox("품질", ["standard", "hd"], index=0)
style   = st.selectbox("스타일", ["vivid", "natural"], index=0)

c3, c4 = st.columns(2)
with c3:
    if st.button("AI 이미지 생성"):
        if not st.session_state.picked_text.strip():
            st.warning("먼저 문구를 선택/입력해줘!")
        else:
            with st.spinner("이미지 생성 중..."):
                try:
                    js = api_post("/generate_ai_image",
                                  data={"ad_text": st.session_state.picked_text.strip(),
                                        "size": size, "quality": quality, "style": style}).json()
                    if js.get("image_url"):
                        st.session_state.ai_image_url = js["image_url"]
                        st.image(js["image_url"], caption=f"AI 이미지 ({size})", use_container_width=True)
                        st.success("완료!")
                    else:
                        st.error(f"실패: {js.get('error','')}")
                except requests.HTTPError as he:
                    st.error(f"요청 실패: {he.response.text}")
                except Exception as e:
                    st.error(f"에러: {e}")

with c4:
    if st.button("깨끗한 포스터 생성"):
        if not st.session_state.picked_text.strip():
            st.warning("먼저 문구를 선택/입력해줘!")
        else:
            with st.spinner("포스터 생성 중..."):
                try:
                    js = api_post("/generate_poster_from_text",
                                  data={"ad_text": st.session_state.picked_text.strip(),
                                        "size": size, "quality": quality, "style": style}).json()
                    if js.get("result_url"):
                        st.session_state.poster_url = js["result_url"]
                        st.image(js["result_url"], caption="포스터", use_container_width=True)
                        st.success("완료! 🔥")
                    else:
                        st.error(f"실패: {js.get('error','')}")
                except requests.HTTPError as he:
                    st.error(f"요청 실패: {he.response.text}")
                except Exception as e:
                    st.error(f"에러: {e}")

# ---- 다운로드 버튼
def _data_url_to_bytes(data_url: str) -> bytes:
    header, b64 = data_url.split(",", 1)
    return base64.b64decode(b64)

if st.session_state.get("ai_image_url"):
    st.download_button("AI 이미지 다운로드",
        data=_data_url_to_bytes(st.session_state["ai_image_url"]),
        file_name="ai_image.png", mime="image/png", use_container_width=True)
if st.session_state.get("poster_url"):
    st.download_button("포스터 이미지 다운로드",
        data=_data_url_to_bytes(st.session_state["poster_url"]),
        file_name="poster.png", mime="image/png", use_container_width=True)

# ---- 히스토리
st.write("---")
st.header("📚 내 작업 히스토리")

colh1, colh2 = st.columns([0.25, 0.75])
with colh1:
    limit = st.number_input("가져올 개수", min_value=1, max_value=100, value=12, step=1)
with colh2:
    include_orphans = st.checkbox("파일 없는 레코드도 표시(디버그용)", value=False)

items = []
try:
    js = api_get("/ads", params={"limit": int(limit), "include_orphans": bool(include_orphans)}).json()
    items = js.get("items", [])
except requests.HTTPError as he:
    st.error(f"히스토리 불러오기 실패: {he.response.text}")
except Exception as e:
    st.error(f"히스토리 불러오기 실패: {e}")

if not items:
    st.info("아직 저장된 작업이 없어요. 이미지를 생성하면 자동 저장됩니다.")
else:
    st.subheader("선택 삭제")
    selected_ids = set()
    cols = st.columns(3)
    for i, it in enumerate(items):
        with cols[i % 3]:
            st.caption(f'#{it["id"]} · {it["kind"]} · {it["size"]} · {it["created_at"]}')
            if st.checkbox("선택", key=f"sel_{it['id']}"):
                selected_ids.add(it["id"])
            if it.get("data_url"):
                st.image(it["data_url"], use_container_width=True)
            else:
                st.warning("이미지 파일을 불러올 수 없어요.")
            st.write(it["ad_text"])
            if st.button("이 항목 삭제", key=f"del_{it['id']}"):
                try:
                    api_delete(f"/ads/{it['id']}")
                    st.success("삭제 완료!")
                    st.rerun()
                except requests.HTTPError as he:
                    st.error(f"삭제 실패: {he.response.text}")
                except Exception as e:
                    st.error(f"삭제 실패: {e}")

    if selected_ids:
        ids_str = ",".join(str(x) for x in sorted(selected_ids))
        if st.button(f"선택한 {len(selected_ids)}개 삭제"):
            try:
                api_delete("/ads", params={"ids": ids_str})
                st.success("벌크 삭제 완료!")
                st.rerun()
            except requests.HTTPError as he:
                st.error(f"벌크 삭제 실패: {he.response.text}")
            except Exception as e:
                st.error(f"벌크 삭제 실패: {e}")
