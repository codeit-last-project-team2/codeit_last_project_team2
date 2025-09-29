#---------------------------------------------#
#                루트 경로 추가                #
#---------------------------------------------#
import sys, os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

#---------------------------------------------#
#                 import                      #
#---------------------------------------------#
import streamlit as st
import re, requests, json

from backend.models.user_information_model import UserInformation

#---------------------------------------------#
#                기본 설정                     #
#---------------------------------------------#
st.set_page_config(page_title="매장 관리", layout="wide")
st.title("매장 관리")

BACKEND_URL = "http://127.0.0.1:8000"

#---------------------------------------------#
#                로그인 확인                   #
#---------------------------------------------#
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()
    
headers = {"Authorization": f"Bearer {st.session_state.token}"}

#---------------------------------------------#
#                세션 초기화                   #
#---------------------------------------------#
if "add_store" not in st.session_state:
    st.session_state.add_store = False

if "show_stores" not in st.session_state:
    st.session_state.show_stores = False

if "del_store" not in st.session_state:
    st.session_state.del_store = False

#---------------------------------------------#
#                기능 선택                     #
#---------------------------------------------#
col1, col2, col3 = st.columns(3)

with col1:
    if st.button('매장 추가'):
        st.session_state.add_store = True
        st.session_state.show_stores = False
        st.session_state.del_store = False
        st.rerun()

with col2:
    if st.button("등록된 매장 확인"):
        st.session_state.add_store = False
        st.session_state.show_stores = True
        st.session_state.del_store = False
        st.rerun()

with col3:
    if st.button('매장 삭제'):
        st.session_state.add_store = False
        st.session_state.show_stores = False
        st.session_state.del_store = True
        st.rerun()

#---------------------------------------------#
#                매장 추가                     #
#---------------------------------------------#
if st.session_state.add_store:

    if st.button('매장 추가 닫기', key='close_add_store'):
        st.session_state.add_store = False
        st.rerun()

    st.markdown("정보를 입력한 후 저장을 눌러주세요.")
    st.markdown("※'매장 추가 닫기' 버튼 클릭 시 입력한 정보가 사라집니다.※")
    # ------------------------------------------------------------------------------------------
    st.markdown("### 가게 정보")
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 상호명")
    store_name = st.text_input("", key='store name')
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 업종 대분류")
    category_main = st.selectbox("", 
        ["요식업", "서비스업", "소매업", "생활/여가", "건강/웰빙", "기타"])
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 업종 소분류")
    category_sub_list = {
        "요식업": ["한식당", "중식당", "일식당", "양식당", "치킨집", "분식집", "패스트푸드점", "카페/디저트", "술집/호프/포차", "배달 전문점", "기타(직접 입력)"],
        "서비스업": ["미용실/헤어샵", "네일샵", "피부관리/에스테틱", "세탁소", "학원/교육 서비스", "운동/헬스/PT 스튜디오", "사진관/스튜디오", "기타(직접 입력)"],
        "소매업": ["편의점", "마트/슈퍼", "전통시장 상점", "의류 매장", "신발 매장", "액세서리/잡화점", "화장품 매장", "전자제품 매장", "서점", "기타(직접 입력)"],
        "생활/여가": ["꽃집/플라워샵", "애견샵", "노래방", "PC방", "당구장", "보드게임/방탈출 카페", "스튜디오 대여", "기타(직접 입력)"],
        "건강/웰빙": ["약국", "한의원", "헬스클럽", "요가/필라테스", "마사지샵/스파", "건강식품 매장", "기타(직접 입력)"],
        "기타": ["프리랜서/개인 사업", "온라인 판매(스마트스토어 등)", "푸드트럭", "지역 특산물 판매점", "기타(직접 입력)"]
    }
    category_sub = st.selectbox("", category_sub_list[category_main])
    category_sub_custom = ""
    if category_sub == "기타(직접 입력)":
        category_sub_custom = st.text_input("직접 입력해주세요:")
    category_sub = category_sub_custom if category_sub == "기타(직접 입력)" else category_sub
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 연락처")
    call_number = st.text_input("연락처를 입력하세요 (예: 010-1234-5678)", key="call_number")

    pattern = r"^01[0-9]-\d{3,4}-\d{4}$"
    if call_number:
        if not re.match(pattern, call_number):
            st.error("❌ 형식이 올바르지 않습니다. 예: 010-1234-5678")
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 주소")
    address = st.text_input("", key='address')
    st.markdown("---")
    # ------------------------------------------------------------------------------------------
    st.markdown("### 서비스(메뉴)")
    menu_count = st.number_input("메뉴 개수를 입력하세요", min_value=1, max_value=20, value=3, step=1)

    cols_per_row = 5
    menus = []
    for row_start in range(0, menu_count, cols_per_row):
        row_cols = st.columns(cols_per_row)
        for offset in range(cols_per_row):
            idx = row_start + offset + 1
            if idx > menu_count:
                break
            with row_cols[offset]:
                st.markdown(f"#### 메뉴 {idx}")
                image = st.file_uploader("이미지 업로드", type=["jpg", "png"], key=f"menu_img_{idx}")
                name = st.text_input("메뉴명", key=f"menu_name_{idx}")
                price = st.number_input("가격", min_value=0, step=100, key=f"menu_price_{idx}")
                desc = st.text_area("설명", key=f"menu_desc_{idx}")
                img_path = None
                if image is not None:
                    files = {"file": (image.name, image.getvalue(), image.type)}
                    res = requests.post(
                        f"{BACKEND_URL}/userinfo/uploupload_imagead/{st.session_state['token']}/{store_name}/menu/{idx}",
                        files=files,
                        headers=headers
                    )
                    if res.status_code == 200:
                        img_path = res.json().get("path")

                menus.append({
                    "img_path": img_path,
                    "name": name,
                    "price": price,
                    "desc": desc,
                })

    st.markdown("---")
    # ------------------------------------------------------------------------------------------
    st.markdown("### 추가 정보(선택)")
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 타겟층")
    target_options = [
        "가족 단위", "직장인", "학생", "연인/데이트 고객", "40대 이상 중장년층", "1인 고객",
        "어린이 동반 고객", "시니어(60대 이상)", "관광객/여행객", "지역 주민", "인근 상권 종사자",
        "운동/건강 관심 고객", "트렌드/유행 관심 고객", "프리랜서/재택근무자", "외국인 고객"
    ]

    targets = []

    target_col1, target_col2, target_col3 = st.columns(3)
    third = (len(target_options) + 2) // 3

    with target_col1:
        for opt in target_options[:third]:
            if st.checkbox(opt, key=f"col1_{opt}"):
                targets.append(opt)

    with target_col2:
        for opt in target_options[third:2*third]:
            if st.checkbox(opt, key=f"col2_{opt}"):
                targets.append(opt)

    with target_col3:
        for opt in target_options[2*third:]:
            if st.checkbox(opt, key=f"col3_{opt}"):
                targets.append(opt)

    custom_targets_raw = st.text_input("직접 입력(쉼표로 구분)", placeholder="예: MZ세대, 온라인 고객, 지역 축제 방문객")
    if custom_targets_raw:
        custom_targets = [ct.strip() for ct in custom_targets_raw.split(",") if ct.strip()]
        targets.extend(custom_targets)
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 판패 포인트")
    selling_points = st.multiselect("", 
        [
            "저렴한 가격", "빠른 배달", "건강한 재료", "푸짐한 양", "독특한 맛/레시피", "지역 특산물 활용",
            "프리미엄 품질", "친절한 서비스", "깔끔한 위생 관리", "트렌디한 메뉴 구성", "계절/한정 메뉴 제공",
            "고객 맞춤형 옵션", "SNS 인증샷용 비주얼", "오랜 전통", "친환경", "로컬푸드 사용",
            "포장/테이크아웃 용이", "단체/모임 적합", "가성비 좋은 세트 메뉴"
        ]
    )

    custom_points_raw = st.text_input("직접 입력(쉼표로 구분)", placeholder="예: 비건 메뉴, 프리미엄 와인, 저칼로리 옵션")
    if custom_points_raw:
        custom_points = [p.strip() for p in custom_points_raw.split(",") if p.strip()]
        selling_points.extend(custom_points)
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 광고 목적")
    ad_purpose = st.selectbox("", 
        ["신규 고객 유치", "단골 고객 확보", "시즌/이벤트 홍보", "신메뉴 출시 홍보", "브랜드 이미지 강화", "기타(직접 입력)"]
    )

    custom_ad_purpose = ""
    if ad_purpose == "기타(직접 입력)":
        custom_ad_purpose = st.text_input("기타 광고 목적을 입력하세요", placeholder="예: 지역 사회 참여, 프리미엄 이미지 구축")

    ad_purpose = custom_ad_purpose if ad_purpose == "기타(직접 입력)" else ad_purpose
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 브랜드 분위기")
    mood = st.selectbox("", 
        ["(선택 안 함)", "아늑한", "편안한", "세련된", "트렌디한", "활기찬", "에너지 넘치는", "전통적인", "향토적인", "프리미엄", "고급스러운", "기타(직접 입력)"]
    )

    custom_mood = ""
    if mood == "기타(직접 입력)":
        custom_mood = st.text_input("✏️ 기타 분위기를 입력하세요", placeholder="예: 모던한 감성, 빈티지 스타일")

    mood = custom_mood if mood == "기타(직접 입력)" else mood
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 이벤트")
    event = st.selectbox("", 
        ["(선택 안 함)", "오픈 이벤트", "1+1 행사", "특정 요일 할인", "생일 쿠폰 제공", "단체 주문 할인", "기타(직접 입력)"]
    )
    custom_event = ""
    if event == "기타(직접 입력)":
        custom_event = st.text_input("✏️ 기타 이벤트/프로모션을 입력하세요", placeholder="예: 해피아워, 첫 방문 고객 할인")
    event = custom_event if event == "기타(직접 입력)" else event
    # ------------------------------------------------------------------------------------------
    st.markdown("#### 광고 톤앤매너")
    tone = st.selectbox("", 
        ["(선택 안 함)", "친근하고 유쾌한", "세련되고 감각적인", "전통적이고 신뢰감 있는", "트렌디하고 젊은 감성", "따뜻하고 가족적인", "기타(직접 입력)"]
    )
    custom_tone = ""
    if tone == "기타(직접 입력)":
        custom_tone = st.text_input("✏️ 기타 톤 & 메시지 스타일을 입력하세요", placeholder="예: 럭셔리, 캐주얼, 미니멀리즘")
    tone = custom_tone if tone == "기타(직접 입력)" else tone

    st.markdown("---")
    # ------------------------------------------------------------------------------------------


    if st.button("저장", key='btn_save_bottom'):
        missing_fields = []
        if not store_name.strip():
            missing_fields.append("상호명")
        if not category_main.strip():
            missing_fields.append("업종 대분류")
        if not category_sub.strip():
            missing_fields.append("업종 소분류")
        if not call_number.strip():
            missing_fields.append("연락처")
        if not address.strip():
            missing_fields.append("주소")
        if not menus or all(not m["name"].strip() for m in menus):
            missing_fields.append("메뉴 (최소 1개 이상 이름 입력)")

        if missing_fields:
            st.error(f"❌ 다음 항목을 입력해 주세요: {', '.join(missing_fields)}")
            st.stop()
        
        user_info = UserInformation(
                email=st.session_state.get("user_email"),
                store_name=store_name,
                category_main=category_main,
                category_sub=category_sub,
                call_number=call_number,
                address=address,
                menus=menus,
                targets=targets,
                selling_points=selling_points, 
                ad_purpose=ad_purpose, 
                mood=mood,
                event=event,
                tone=tone, 
        )

        res = requests.post(f"{BACKEND_URL}/userinfo/upload", json=user_info.model_dump(), headers=headers)
        if res.status_code != 200:
            st.error("매장 등록 실패")
            st.stop()
    
        st.session_state.add_store = False
        st.rerun()
        st.text("매장이 등록되었습니다!")

#---------------------------------------------#
#                매장 확인/수정                #
#---------------------------------------------#
if st.session_state.show_stores:
    if st.button('매장 확인 닫기', key='close_show_store'):
        st.session_state.show_stores = False
        
        st.rerun()

    res = requests.post(f"{BACKEND_URL}/userinfo/get_store_names", json={"user_email": st.session_state.get("user_email")}, headers=headers)

    if res.status_code != 200:
        st.error("조회 실패")
        st.text(res.status_code)
    else:
        stores = res.json()
    
    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
    else:
        selected_store = st.radio("매장을 선택하세요:", stores, horizontal=True)

        res = requests.post(f"{BACKEND_URL}/userinfo/get_store_info", json={"user_email": st.session_state.get("user_email"), "store_name": selected_store}, headers=headers)

        if res.status_code != 200:
            st.error("조회 실패")
            st.text(res.status_code)
        else:
            info = res.json()

        store_name =info['store_name']
        category_main = st.text_input("업종(대)", value=info['category_main'])
        category_sub = st.text_input("업종(소)", value=info['category_sub'])
        call_number = st.text_input("전화번호", value=info['call_number'])
        address = st.text_input("주소", value=info['address'])

        menus_str = info['menus']
        menus = json.loads(menus_str)

        updated_menus = []
        for i, menu in enumerate(menus):
            st.subheader(f"메뉴 {i+1}")
            name = st.text_input(f"이름 {i+1}", value=menu['name'], key=f"name_{i}")
            price = st.number_input(f"가격 {i+1}", value=menu['price'], key=f"price_{i}")
            desc = st.text_input(f"설명 {i+1}", value=menu['desc'], key=f"desc_{i}")
            updated_menus.append({
                "img_path": menu['img_path'],
                "name": name,
                "price": price,
                "desc": desc
            })

        targets_str = info['targets']
        targets = json.loads(targets_str)
        targets_text = ", ".join(targets)
        targets_input = st.text_input("타겟 고객", value=targets_text)

        selling_points_str = info['selling_points']
        selling_points = json.loads(selling_points_str)
        selling_points_text = ", ".join(selling_points)
        selling_points_input = st.text_input("판매 포인트", value=selling_points_text)

        ad_purpose = st.text_input("광고 목적", value=info['ad_purpose'])
        mood = st.text_input("매장 분위기", value=info['mood'])
        event = st.text_input("이벤트", value=info['event'])
        tone = st.text_input("광고 톤", value=info['tone'])

        if st.button("저장하기"):
            updated_info = {
                "email": st.session_state.get("user_email"),
                "store_name": store_name,
                "category_main": category_main,
                "category_sub": category_sub,
                "call_number": call_number,
                "address": address,
                "menus": updated_menus, 
                "targets": [t.strip() for t in targets_input.split(",") if t.strip()],
                "selling_points": [s.strip() for s in selling_points_input.split(",") if s.strip()],  
                "ad_purpose": ad_purpose,
                "mood": mood,
                "event": event,
                "tone": tone,
            }
            res = requests.post(f"{BACKEND_URL}/userinfo/update", json=updated_info, headers=headers)
            if res.status_code != 200:
                st.error("매장 수정 실패")
                st.stop()
        
            st.session_state.add_store = False
            st.rerun()
            st.text("매장 정보가 수정되었습니다!")

#---------------------------------------------#
#                매장 삭제                     #
#---------------------------------------------#
if st.session_state.del_store:
    if st.button('매장 삭제 닫기', key='close_del_store'):
        st.session_state.del_store = False
        st.rerun()

    res = requests.post(f"{BACKEND_URL}/userinfo/get_store_names", json={"user_email": st.session_state.get("user_email")}, headers=headers)

    if res.status_code != 200:
        st.error("조회 실패")
        st.text(res.status_code)
    else:
        stores = res.json()
    
    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
    else:
        selected_store = st.radio("삭제할 매장을 선택하세요:", stores, horizontal=True)

        if st.button('삭제'):
            res = requests.post(f"{BACKEND_URL}/userinfo/delete_store", json={"user_email": st.session_state.get("user_email"), "store_name": selected_store}, headers=headers)

            if res.status_code != 200:
                st.error("조회 실패")
                st.text(res.status_code)
            else:
                st.rerun()    