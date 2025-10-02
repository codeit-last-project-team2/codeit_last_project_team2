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
import re, requests, json, uuid

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

#---------------------------------------------#
#                기능 선택                     #
#---------------------------------------------#
col1, col2 = st.columns(2)

with col1:
    if st.button('매장 추가'):
        st.session_state.add_store = True
        st.session_state.show_stores = False
        st.rerun()

with col2:
    if st.button("등록된 매장 확인"):
        st.session_state.add_store = False
        st.session_state.show_stores = True
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

    # 입력 저장
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

        if missing_fields:
            st.error(f"❌ 다음 항목을 입력해 주세요: {', '.join(missing_fields)}")
            st.stop()

        # 입력 후처리
        final_category_sub = category_sub_custom if category_sub == "기타(직접 입력)" else category_sub

        user_info = UserInformation(
                store_name=store_name,
                category_main=category_main,
                category_sub=final_category_sub,
                call_number=call_number,
                address=address,
        )

        res = requests.post(f"{BACKEND_URL}/userinfo/upload", json=user_info.model_dump(), headers=headers)
        if res.status_code != 200:
            st.error(f"매장 등록 실패 error code: {res.status_code}")
            
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

    res = requests.get(f"{BACKEND_URL}/userinfo/get_store_names", headers=headers)

    if res.status_code != 200:
        st.error(f"조회 실패 error code: {res.status_code}")
    else:
        stores = res.json()
    
    if len(stores) == 0:
        st.text("등록된 매장이 없습니다.")
    else:
        selected_store = st.radio("매장을 선택하세요:", stores, horizontal=True)
       
        if st.button("삭제하기", key='del_store_top'):
            res = requests.post(f"{BACKEND_URL}/userinfo/delete_store", json={"store_name": selected_store}, headers=headers)

            if res.status_code != 200:
                st.error(f"삭제 실패, error code: {res.status_code}")
                st.text(res.status_code)
            else:
                st.rerun()

        res = requests.post(f"{BACKEND_URL}/userinfo/get_store_info", json={"store_name": selected_store}, headers=headers)

        if res.status_code != 200:
            st.error("조회 실패")
            st.text(res.status_code)
        else:
            info = res.json()

        store_name = info['store_name']
        st.text_input("매장명", value=store_name, disabled=True)  # 매장명은 수정 불가
        category_main = st.text_input("업종(대)", value=info['category_main'])
        category_sub = st.text_input("업종(소)", value=info['category_sub'])
        call_number = st.text_input("전화번호", value=info['call_number'])
        address = st.text_input("주소", value=info['address'])

        sub_col1, sub_col2 = st.columns(2)

        with sub_col1:
            if st.button("저장하기"):
                # 필수 값 검증
                missing_fields = []
                if not category_main.strip():
                    missing_fields.append("업종 대분류")
                if not category_sub.strip():
                    missing_fields.append("업종 소분류")
                if not call_number.strip():
                    missing_fields.append("연락처")
                if not address.strip():
                    missing_fields.append("주소")

                if missing_fields:
                    st.error(f"❌ 다음 항목을 입력해 주세요: {', '.join(missing_fields)}")
                    st.stop()

                # 업데이트 데이터 생성
                updated_info = {
                    "store_name": store_name,
                    "category_main": category_main,
                    "category_sub": category_sub,
                    "call_number": call_number,
                    "address": address,
                }

                res = requests.post(f"{BACKEND_URL}/userinfo/update", json=updated_info, headers=headers)
                if res.status_code != 200:
                    st.error("매장 수정 실패")
                    st.stop()

                st.session_state.add_store = False
                st.rerun()
                st.text("매장 정보가 수정되었습니다!")

        with sub_col2:
            if st.button("삭제하기", key='del_store_bottom'):
                res = requests.post(f"{BACKEND_URL}/userinfo/delete_store", json={"user_email": st.session_state.get("user_email"), "store_name": selected_store}, headers=headers)

                if res.status_code != 200:
                    st.error("조회 실패")
                    st.text(res.status_code)
                else:
                    st.rerun()