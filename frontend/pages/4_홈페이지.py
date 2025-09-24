import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.title("가게 홈페이지 자동 생성기")
# -----------------------------
# 세션 값 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# -----------------------------
# 세션 상태 초기화 (최초 실행 시만)
# -----------------------------
if "poster_history" not in st.session_state:
    st.session_state.poster_history = []  # [{title, body, dalle_prompt, image_bytes}, ...]

# -----------------------------
# 입력 UI
# -----------------------------
# 0. 브랜드 명
store_name = st.text_input("**0. 상호명 (가게 이름)**")

# 1. 업종 대분류 ------------------------------
category_main = st.selectbox("**1. 업종 대분류**", 
    ["요식업", "서비스업", "소매업", "생활/여가", "건강/웰빙", "기타"])

# 2. 업종 소분류 ------------------------------
category_sub_list = {
    "요식업": ["한식당", "중식당", "일식당", "양식당", "치킨집", "분식집", "패스트푸드점", "카페/디저트", "술집/호프/포차", "배달 전문점", "기타(직접 입력)"],
    "서비스업": ["미용실/헤어샵", "네일샵", "피부관리/에스테틱", "세탁소", "학원/교육 서비스", "운동/헬스/PT 스튜디오", "사진관/스튜디오", "기타(직접 입력)"],
    "소매업": ["편의점", "마트/슈퍼", "전통시장 상점", "의류 매장", "신발 매장", "액세서리/잡화점", "화장품 매장", "전자제품 매장", "서점", "기타(직접 입력)"],
    "생활/여가": ["꽃집/플라워샵", "애견샵", "노래방", "PC방", "당구장", "보드게임/방탈출 카페", "스튜디오 대여", "기타(직접 입력)"],
    "건강/웰빙": ["약국", "한의원", "헬스클럽", "요가/필라테스", "마사지샵/스파", "건강식품 매장", "기타(직접 입력)"],
    "기타": ["프리랜서/개인 사업", "온라인 판매(스마트스토어 등)", "푸드트럭", "지역 특산물 판매점", "기타(직접 입력)"]
}

category_sub = st.selectbox("**2. 세부 업종**", category_sub_list[category_main])

category_sub_custom = ""
if category_sub == "기타(직접 입력)":
    category_sub_custom = st.text_input("직접 입력해주세요:")

category_sub = category_sub_custom if category_sub == "기타(직접 입력)" else category_sub

# 3. 주요 메뉴 ------------------------------ㄹ
st.markdown("**3. 주요 메뉴 입력**") 

num_menus = st.number_input("메뉴 개수를 입력하세요", min_value=1, max_value=20, value=2, step=1)
menus = []

for i in range(num_menus):
    name = st.text_input(f"서비스 {i+1} 이름", key=f"name_{i}")
    price = st.text_input(f"서비스 {i+1} 가격 (원)", key=f"price_{i}_text")
    st.markdown(f"---") 
    try:
        price = int(price) if price else 0
    except ValueError:
        price = 0
    
    menus.append({"name": name, "price": price})

# 4. 타겟 ------------------------------
st.markdown("**4. 타겟 고객층**")

target_options = [
    "가족 단위", "직장인", "학생", "연인/데이트 고객", "40대 이상 중장년층", "1인 고객",
    "어린이 동반 고객", "시니어(60대 이상)", "관광객/여행객", "지역 주민", "인근 상권 종사자",
    "운동/건강 관심 고객", "트렌드/유행 관심 고객", "프리랜서/재택근무자", "외국인 고객"
]

targets = []

col1, col2, col3 = st.columns(3)
third = (len(target_options) + 2) // 3

with col1:
    for opt in target_options[:third]:
        if st.checkbox(opt, key=f"col1_{opt}"):
            targets.append(opt)

with col2:
    for opt in target_options[third:2*third]:
        if st.checkbox(opt, key=f"col2_{opt}"):
            targets.append(opt)

with col3:
    for opt in target_options[2*third:]:
        if st.checkbox(opt, key=f"col3_{opt}"):
            targets.append(opt)

custom_targets_raw = st.text_input("직접 입력(쉼표로 구분)", placeholder="예: MZ세대, 온라인 고객, 지역 축제 방문객")
if custom_targets_raw:
    custom_targets = [ct.strip() for ct in custom_targets_raw.split(",") if ct.strip()]
    targets.extend(custom_targets)


# 5. 주요 판매 포인트 ------------------------------
selling_points = st.multiselect("**5. 주요 판매 포인트 (USP, 장점)**", 
    [
        "저렴한 가격", "빠른 배달", "건강한 재료", "푸짐한 양", "독특한 맛/레시피", "지역 특산물 활용",
        "프리미엄 품질", "친절한 서비스", "깔끔한 위생 관리", "트렌디한 메뉴 구성", "계절/한정 메뉴 제공",
        "고객 맞춤형 옵션", "SNS 인증샷용 비주얼", "오랜 전통/역사", "친환경/로컬푸드 사용",
        "포장/테이크아웃 용이", "단체/모임 적합", "가성비 좋은 세트 메뉴"
    ]
)

custom_points_raw = st.text_input("직접 입력(쉼표로 구분)", placeholder="예: 비건 메뉴, 프리미엄 와인, 저칼로리 옵션")
if custom_points_raw:
    custom_points = [p.strip() for p in custom_points_raw.split(",") if p.strip()]
    selling_points.extend(custom_points)

# 6. 광고 목적 ------------------------------
ad_purpose = st.selectbox("**6. 광고 목적**", 
    ["신규 고객 유치", "단골 고객 확보", "시즌/이벤트 홍보", "신메뉴 출시 홍보", "브랜드 이미지 강화", "기타(직접 입력)"]
)

custom_ad_purpose = ""
if ad_purpose == "기타(직접 입력)":
    custom_ad_purpose = st.text_input("기타 광고 목적을 입력하세요", placeholder="예: 지역 사회 참여, 프리미엄 이미지 구축")

ad_purpose = custom_ad_purpose if ad_purpose == "기타(직접 입력)" else ad_purpose


# 7. 분위기 ------------------------------
mood = st.selectbox("**7. 가게 분위기/컨셉(선택)**", 
    ["(선택 안 함)", "아늑한/편안한", "세련된/트렌디한", "활기찬/에너지 넘치는", "전통적인/향토적인", "프리미엄/고급스러운", "기타(직접 입력)"]
)

custom_mood = ""
if mood == "기타(직접 입력)":
    custom_mood = st.text_input("✏️ 기타 분위기를 입력하세요", placeholder="예: 모던한 감성, 빈티지 스타일")

mood = custom_mood if mood == "기타(직접 입력)" else mood

# 8. 위치 ------------------------------
location = st.selectbox("**8. 위치/입지 특성(선택)**", 
    ["(선택 안 함)", "역세권", "학교/학원가 근처", "주거 단지 중심", "번화가/상권 중심지", "관광지/명소 인근", "기타(직접 입력)"]
)
custom_location = ""
if location == "기타(직접 입력)":
    custom_location = st.text_input("✏️ 기타 위치/입지 특성을 입력하세요", placeholder="예: 오피스 밀집 지역, 대형 마트 근처")
location = custom_location if location == "기타(직접 입력)" else location


# 9. 이벤트 ------------------------------
event = st.selectbox("**9. 이벤트/프로모션(선택)**", 
    ["(선택 안 함)", "오픈 이벤트", "1+1 행사", "특정 요일 할인", "생일 쿠폰 제공", "단체 주문 할인", "기타(직접 입력)"]
)
custom_event = ""
if event == "기타(직접 입력)":
    custom_event = st.text_input("✏️ 기타 이벤트/프로모션을 입력하세요", placeholder="예: 해피아워, 첫 방문 고객 할인")
event = custom_event if event == "기타(직접 입력)" else event


# 10. 브랜드 톤 ------------------------------
tone = st.selectbox("**10. 브랜드 톤 & 메시지 스타일(선택)**", 
    ["(선택 안 함)", "친근하고 유쾌한", "세련되고 감각적인", "전통적이고 신뢰감 있는", "트렌디하고 젊은 감성", "따뜻하고 가족적인", "기타(직접 입력)"]
)
custom_tone = ""
if tone == "기타(직접 입력)":
    custom_tone = st.text_input("✏️ 기타 톤 & 메시지 스타일을 입력하세요", placeholder="예: 럭셔리, 캐주얼, 미니멀리즘")
tone = custom_tone if tone == "기타(직접 입력)" else tone

# 사용자별 폴더 구분용 ------------------------------
store_id = st.text_input("가게 ID (예: store123)")

info = {
    "store_name": store_name,
    "category_main": category_main,
    "category_sub": category_sub,
    "menus": menus,
    "targets": targets,
    "selling_points": selling_points,
    "ad_purpose": ad_purpose,
    "mood": mood if mood != "(선택 안 함)" else "",
    "location": location if location != "(선택 안 함)" else "",
    "event": event if event != "(선택 안 함)" else "",
    "tone": tone if tone != "(선택 안 함)" else "",
}

# -----------------------------
# 실행
# -----------------------------

if st.button("홈페이지 만들기"):
    st.info("홈페이지를 생성 중입니다... 5~10분정도 소요됩니다.")

    # --- HTML 템플릿 생성 ---
    html_res = requests.post(f"{BACKEND_URL}/homepage/generate", json=info, headers=headers)

    if html_res.status_code != 200:
        st.error(f"홈페이지 생성 실패: {html_res.text}")
    else:
        html = html_res.json() 
    try:
        github_req = {
            'html': html,
            'store_id': store_id
        }

        homepage_res = requests.post(f"{BACKEND_URL}/homepage/upload", json=github_req, headers=headers)
        if homepage_res.status_code != 200:
            st.error(f"홈페이지 업로드 실패: {homepage_res.text}")
        else:
            homepage_url = homepage_res.json() 

        st.success("✅ GitHub에 홈페이지 업로드 완료!")

        # --- GitHub Pages 주소 안내 ---
        st.markdown(f"🌍 [홈페이지 보러가기]({homepage_url})")
        st.text(f"홈페이지 주소: {homepage_url}")

    except Exception as e:
        st.error(f"업로드 중 오류 발생: {e}")