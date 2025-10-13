import streamlit as st
from datetime import datetime
from typing import Dict, Any
import streamlit as st
import requests, time

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="홈페이지 생성", layout="wide")
st.title("🌐 홈페이지 생성")

# -----------------------------
# 로그인 및 매장 정보 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

user_email = st.session_state.get("user_email")

if "store_profile" not in st.session_state or not st.session_state["store_profile"].get("store_name"):
    st.warning("⚠️ 매장 관리 페이지에서 정보를 먼저 입력해주세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}
store = st.session_state["store_profile"]

# ---------- 공통 설정 ----------
TYPES = {
    "브랜드 스토리형": "brand",
    "이벤트 홍보형": "event",
    "메뉴 홍보형": "menu",
}

def required_warn(ok: bool, msg: str):
    if not ok:
        st.warning(msg, icon="⚠️")

def section_header(title: str, subtitle: str = ""):
    if subtitle:
        st.subheader(f"{title} · :gray[{subtitle}]")
    else:
        st.subheader(title)

def iso_dt(s: str) -> bool:
    try:
        datetime.fromisoformat(s)
        return True
    except Exception:
        return False

# ---------- 공통 입력 ----------
def render_common_inputs() -> Dict[str, Any]:
    st.header("공통 정보 입력", divider="gray")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        brand_name = st.text_input("브랜드명 (필수)", value=store['store_name'], disabled=True)
        industry = st.text_input("업종 분류 (필수)", value=store['category'], disabled=True)
        contact = st.text_input("연락처 (필수)", value=store['phone'], disabled=True)
        address = st.text_input("주소 (필수)", value=store['address'], disabled=True)

    with col2:
        hero_title = st.text_input("대표 제목 (필수)", placeholder="예) 우리는 왜 이 길을 택했나")
        hero_lead = st.text_area("부제 또는 설명 (선택)", placeholder="예) 지역과 사람, 그리고 정직한 재료로 브랜드를 만듭니다.", height=70)

    with col3:
        with st.expander("🎨 색상 팔레트 (선택)", expanded=False):
            brand = st.color_picker("대표 색상", "#1f6feb")
            brand2 = st.color_picker("보조 색상", "#0ea5e9")
            accent = st.color_picker("포인트 색상", "#f59e0b")
    

    required_warn(bool(brand_name), "브랜드명은 필수입니다.")
    required_warn(bool(industry), "업종 분류는 필수입니다.")
    required_warn(bool(contact), "연락처는 필수입니다.")
    required_warn(bool(address), "주소는 필수입니다.")
    required_warn(bool(hero_title), "대표제목은 필수입니다.")

    return {
        "brand_name": brand_name,
        "industry": industry,
        "contact": contact,
        "address": address,
        "palette": {"brand": brand, "brand2": brand2, "accent": accent},
        "hero": {"title": hero_title, "lead": hero_lead}
    }
# ---------- 안내 입력 ----------
def notes_input():
    st.markdown("#### 이용안내/고지")
    notes_all = st.text_area('', placeholder="서비스 특성상 일부 기능은 지역/플랜에 따라 상이할 수 있습니다.")
    return notes_all

# ---------- FAQ 입력 ----------
def faq_input(example_qs=None, example_as=None, default_count=2):
    st.markdown("#### 자주 묻는 질문 (FAQ)")

    example_qs = example_qs or []
    example_as = example_as or []

    faq_count = st.number_input("FAQ 개수", min_value=0, max_value=20, step=1, value=default_count)

    faq = []

    for i in range(faq_count):
        q_placeholder = (example_qs[i] if i < len(example_qs) else f"FAQ 예시 질문 {i+1}")
        a_placeholder = (example_as[i] if i < len(example_as) else f"FAQ 예시 답변 {i+1}")

        with st.expander(f"FAQ {i+1}", expanded=(i == 0)):
            fq = st.text_input(f"질문 {i+1}", placeholder=q_placeholder, key=f"fq_{i}")
            fa = st.text_area(f"답변 {i+1}", placeholder=a_placeholder, key=f"fa_{i}", height=120)

            if fq.strip():
                faq.append({"q": fq.strip(), "a": fa.strip()})
    return faq

# ---------- 메뉴 홍보형 ----------
def form_menu() -> Dict[str, Any]:
    st.markdown("## 메뉴 홍보형")

    # 1) 카테고리 & 아이템
    with st.container(border=True):
        # 1-1) 카테고리
        section_header("카테고리 & 아이템")
        cats = st.text_input("카테고리 (쉼표 구분, 필수)", placeholder="플랜,서비스,상품,콘텐츠")
        categories = [s.strip() for s in cats.split(",") if s.strip()]

        # 1-2) 아이템
        st.markdown("**아이템/메뉴**")
        items = []

        defaults = [
            ("Starter 플랜", "인기", "개인용 기본 기능", "플랜/요금제", "가성비,입문", "", "9900", "월", "월간", "기본/연간할인", "사용자수:1\n스토리지:10GB"),
            ("프리미엄 헤어컷", "", "스타일 컨설팅 포함", "서비스", "예약제,전문가", "가위 사용 주의", "45000", "회", "60분", "남성/여성", "디자인컷:포함\n샴푸:포함"),
            ("핸드메이드 머그", "신상", "도자기 수공예 머그", "상품", "수공예,선물", "깨짐 주의", "28000", "개", "", "패키징옵션", "재질:세라믹\n용량:350ml\n색상:아이보리")
        ]

        item_count = st.number_input("아이템 개수", min_value=0, max_value=50, step=1, value=3)

        items = []
        for i in range(item_count):
            if i < len(defaults):
                nm, bd, sb, itype, tg, wrn, price, unit, dur, opts, attrs = defaults[i]
            else:
                nm, bd, sb, itype, tg, wrn, price, unit, dur, opts, attrs = "", "", "", "상품", "", "", "", "", "", "", ""

            with st.expander(f"아이템 {i+1}", expanded=(i == 0)):
                name = st.text_input("이름", placeholder=nm, key=f"it_n_{i}")
                badge = st.text_input("뱃지 (선택)", placeholder=bd, key=f"it_b_{i}")
                subtitle = st.text_input("부제/짧은 설명 (선택)", placeholder=sb, key=f"it_s_{i}")

                item_type = st.selectbox(
                    "유형",
                    options=["상품", "서비스", "플랜/요금제", "콘텐츠", "기타"],
                    index=["상품","서비스","플랜/요금제","콘텐츠","기타"].index(itype)
                    if itype in ["상품","서비스","플랜/요금제","콘텐츠","기타"]
                    else 0,
                    key=f"it_ty_{i}"
                )

                tags = st.text_input("태그 (쉼표)", placeholder=tg, key=f"it_t_{i}")
                warnings = st.text_input("경고/주의 (쉼표, 선택)", placeholder=wrn, key=f"it_w_{i}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    price_val = st.text_input("가격 (숫자/문자 허용)", placeholder=price, key=f"it_p_{i}")
                with col2:
                    unit_val = st.text_input("단위 (예: 개/월/회)", placeholder=unit, key=f"it_u_{i}")
                with col3:
                    duration = st.text_input("이용기간/소요시간 (선택)", placeholder=dur, key=f"it_d_{i}")

                options = st.text_input("옵션 (쉼표, 선택)", placeholder=opts, key=f"it_opt_{i}")
                attributes = st.text_area(
                    "스펙/속성 (키:값, 줄바꿈으로 구분)",
                    placeholder=attrs, key=f"it_attr_{i}", height=180
                )

                items.append({
                    "name": name,
                    "badge": badge,
                    "subtitle": subtitle,
                    "type": item_type,
                    "tags": [s.strip() for s in tags.split(",") if s.strip()],
                    "warnings": [s.strip() for s in warnings.split(",") if s.strip()],
                    "price": price_val,
                    "unit": unit_val,
                    "duration": duration,
                    "options": [s.strip() for s in options.split(",") if s.strip()],
                    "attributes": {
                        k.strip(): v.strip()
                        for kv in attrs.replace("\n", ";").split(";")
                        if (kv.strip() and ":" in kv)
                        for k, v in [kv.split(":", 1)]
                    }
                })

        required_warn(bool(categories), "카테고리는 필수입니다.")

    # 2) 안내/FAQ
    with st.container(border=True):
        section_header("안내/FAQ (선택)")
        # 2-1) 안내
        notes_all = notes_input()        

        # 2-2) FAQ 입력
        example_qs = [
            "메뉴(상품)의 가격은 언제 변경되나요?",
            "알레르기 유발 성분이 포함된 메뉴가 있나요?",
            "온라인으로 주문이나 예약이 가능한가요?"
        ]

        example_as = [
            "시즌 한정 또는 원자재 변동 시 가격이 조정될 수 있으며, 최신 가격은 홈페이지 및 매장에서 항상 확인하실 수 있습니다.",
            "일부 제품에는 우유, 견과류, 글루텐 등이 포함될 수 있습니다. 자세한 원재료 정보는 각 메뉴 설명에서 확인하실 수 있습니다.",
            "일부 제품 또는 서비스는 온라인 주문·예약이 가능합니다. 메뉴 상세 페이지의 ‘주문하기’ 또는 ‘예약하기’ 버튼을 눌러 진행해주세요."
        ]

        faq = faq_input(example_qs=example_qs, example_as=example_as)

    catalog_payload = {"categories": categories, "items": items}

    return {
        "catalog": catalog_payload,
        "notes": notes_all,
        "faq": faq,
    }

# ---------- 브랜드 스토리형 ----------
def form_story() -> Dict[str, Any]:
    section_header("브랜드 스토리형")

    # 1) 브랜드 핵심 가치
    with st.container(border=True):
        section_header("창업자 메시지 & 핵심 가치")
        founder_note = st.text_area("창업자 메시지 (필수)", placeholder="작은 골목에서 시작했지만 우리의 신념은 변하지 않았습니다.", height=90)
        start_year = st.number_input("설립 연도", min_value=1900, max_value=datetime.now().year, placeholder=2018, step=1)

        st.markdown("**핵심 가치 (3~6개 권장)**")
        val_count = st.number_input("핵심 가치 개수", min_value=1, max_value=10, step=1, value=3)

        defaults_vals = [
            ("정직", "원료·과정을 투명하게 공개"),
            ("지속가능", "친환경 포장과 생산"),
            ("지역상생", "로컬 협업을 통한 성장"),
            ("혁신", "끊임없는 개선과 실험"),
            ("고객중심", "고객의 목소리에 귀 기울임")
        ]

        values = []

        for i in range(val_count):
            with st.expander(f"핵심 가치 {i+1}", expanded=(i == 0)):
                t = st.text_input(
                    f"가치 {i+1} 제목",
                    placeholder=defaults_vals[i][0] if i < len(defaults_vals) else "",
                    key=f"val_title_{i}"
                )
                d = st.text_input(
                    f"가치 {i+1} 설명",
                    placeholder=defaults_vals[i][1] if i < len(defaults_vals) else "",
                    key=f"val_desc_{i}"
                )
                if t.strip():
                    values.append({"title": t.strip(), "desc": d.strip()})
    # 2) 연혁
    with st.container(border=True):
        section_header("연혁")
        st.markdown("**연혁 / 주요 이정표**")
        timeline_count = st.number_input(
            "연혁 개수",
            min_value=1, max_value=20, step=1, value=3,
            help="입력할 연혁(년도/이벤트) 개수를 선택하세요."
        )

        defaults_tl = [
            (2018, "1호점 오픈", "브랜드의 첫 시작"),
            (2023, "지속가능 라인 론칭", "친환경 제품군 출시"),
            (2025, "리브랜딩", "새로운 로고와 슬로건 공개")
        ]

        timeline = []

        for i in range(timeline_count):
            if i < len(defaults_tl):
                y, ttl, dsc = defaults_tl[i]
            else:
                y, ttl, dsc = (2025, "", "")

            with st.expander(f"연혁 {i+1}", expanded=(i == 0)):
                yv = st.number_input(
                    f"연혁 {i+1} 연도",
                    min_value=1900, max_value=2100, value=y, step=1, key=f"tl_y_{i}"
                )
                tv = st.text_input(f"연혁 {i+1} 제목", placeholder=ttl, key=f"tl_t_{i}")
                desc = st.text_input(f"연혁 {i+1} 설명 (선택)", placeholder=dsc, key=f"tl_d_{i}")

                if tv.strip():
                    timeline.append({"year": yv, "title": tv.strip(), "desc": desc.strip()})

    # 3) 팀 소개
    with st.container(border=True):
        section_header("팀 소개")

        team_count = st.number_input(
            "팀원 수",
            min_value=1,
            max_value=20,
            step=1,
            value=3,
            help="입력할 팀원 수를 선택하세요."
        )

        defaults_team = [
            ("", "Founder · Creative Director", "브랜드 철학 총괄"),
            ("", "Product Lead", "원료·제조 협업 담당"),
            ("", "Brand Designer", "시각 아이덴티티·패키지 디자인"),
            ("", "Marketing Lead", "콘텐츠 전략 및 채널 운영"),
        ]

        team = []

        for i in range(team_count):
            if i < len(defaults_team):
                nm, rl, bio = defaults_team[i]
            else:
                nm, rl, bio = "", "", ""

            with st.expander(f"팀원 {i+1}", expanded=(i == 0)):
                name = st.text_input("이름", placeholder=nm, key=f"tm_n_{i}")
                role = st.text_input("역할/직책", placeholder=rl, key=f"tm_r_{i}")
                bio_ = st.text_input("소개 (간단 설명)", placeholder=bio, key=f"tm_b_{i}")

                if name.strip():
                    team.append({
                        "name": name.strip(),
                        "role": role.strip(),
                        "bio": bio_.strip()
                    })
    # 4) FQA
    with st.container(border=True):
        section_header("FQA")

        example_qs = [
            "브랜드를 시작하게 된 계기는 무엇인가요?",
            "제품(서비스)에 담긴 브랜드 철학은 무엇인가요?",
            "앞으로 브랜드가 나아가고자 하는 방향은 무엇인가요?"
        ]

        example_as = [
            "일상 속에서 지속가능한 가치를 실천하고 싶다는 마음으로 시작했습니다. 작은 아이디어에서 출발했지만, 지금은 많은 분들과 그 철학을 나누고 있습니다.",
            "‘정직한 재료, 진정성 있는 과정’이라는 원칙 아래 모든 제품을 만듭니다. 단순히 물건을 파는 것이 아니라, 우리의 가치가 담긴 경험을 전달하고자 합니다.",
            "지역 사회와 함께 성장하며, 환경에 긍정적인 영향을 주는 브랜드가 되고자 합니다. 더 많은 사람들이 우리의 가치를 공감할 수 있도록 꾸준히 진화할 예정입니다."
        ]
        faq = faq_input(example_qs=example_qs, example_as=example_as)

    return {
        "story": {"founder_note": founder_note, "start_year": start_year},
        "values": values,
        "timeline": timeline,
        "team": team,
        "faq": faq,
    }

# ---------- 이벤트 홍보형 ----------
def form_event() -> Dict[str, Any]:
    st.markdown("## 🎉 이벤트 홍보형")

    # 1) 이벤트 개요
    with st.container(border=True):
        section_header("이벤트 개요")
        purpose = st.text_area("이벤트 목적", placeholder="고객 감사 이벤트로, 참여 고객에게 다양한 선물을 제공합니다.")
        target = st.text_input("참여 대상", placeholder="홈페이지 방문 고객 누구나")
        period = st.text_input("진행 기간", placeholder="2025년 10월 15일 ~ 11월 15일")

        event_summary = {
            "purpose": purpose,
            "target": target,
            "period": period
        }

    # 2) 참여 방법
    with st.container(border=True):
        st.markdown("### 🪜 참여 방법")

        step_count = st.number_input("단계 수", min_value=1, max_value=10, value=3, step=1)
        steps = []
        default_steps = [
            ("신청하기", "이벤트 신청 폼을 작성해주세요."),
            ("참여하기", "이벤트 기간 중 조건을 만족하면 자동 응모됩니다."),
            ("혜택 받기", "당첨자 발표 후 개별 연락을 드립니다."),
        ]

        for i in range(step_count):
            with st.expander(f"참여 단계 {i+1}", expanded=(i == 0)):
                step_title = st.text_input(
                    f"단계 {i+1} 제목",
                    placeholder=default_steps[i][0] if i < len(default_steps) else "",
                    key=f"step_t_{i}"
                )
                step_desc = st.text_area(
                    f"단계 {i+1} 설명",
                    placeholder=default_steps[i][1] if i < len(default_steps) else "",
                    key=f"step_d_{i}", height=60
                )
                if step_title.strip():
                    steps.append({
                        "step": str(i + 1),
                        "title": step_title.strip(),
                        "desc": step_desc.strip()
                    })

    # 3) 경품 및 혜택
    with st.container(border=True):
        st.markdown("### 🎁 혜택 / 경품 안내")

        reward_count = st.number_input("경품 개수", min_value=1, max_value=20, value=2, step=1)
        rewards = []
        default_rewards = [
            ("커피 기프티콘", "100명", "참여 고객 중 추첨"),
            ("브랜드 굿즈 세트", "10명", "우수 후기 작성자")
        ]

        for i in range(reward_count):
            with st.expander(f"경품 {i+1}", expanded=(i == 0)):
                name = st.text_input(
                    "경품명", placeholder=default_rewards[i][0] if i < len(default_rewards) else "", key=f"rw_n_{i}"
                )
                count = st.text_input(
                    "수량/당첨 인원", placeholder=default_rewards[i][1] if i < len(default_rewards) else "", key=f"rw_c_{i}"
                )
                condition = st.text_input(
                    "지급 조건", placeholder=default_rewards[i][2] if i < len(default_rewards) else "", key=f"rw_cond_{i}"
                )
                if name.strip():
                    rewards.append({
                        "name": name.strip(),
                        "count": count.strip(),
                        "condition": condition.strip()
                    })

    # 4) 유의사항 & FAQ
    with st.container(border=True):
        st.markdown("### ⚠️ 유의사항 및 FAQ")

        # 4-1) 유의사항
        notes_raw = st.text_area(
            "유의사항 (줄바꿈으로 구분)",
            placeholder="이벤트 일정 및 내용은 당사 사정에 따라 변경될 수 있습니다.\n부정 참여로 판단될 경우 당첨이 취소될 수 있습니다.\n경품은 당첨자 발표 후 7일 이내 발송됩니다.",
            height=200
        )
        notes = [n.strip() for n in notes_raw.replace(";", ",").replace("\n", ",").split(",") if n.strip()]

        # 4-2) FAQ
        example_qs = [
                "참여 후 당첨 여부는 어떻게 확인하나요?",
                "중복 참여가 가능한가요?",
                "경품은 언제 배송되나요?"
            ]

        example_as = [
            "이벤트 종료 후 홈페이지와 이메일을 통해 공지됩니다.",
            "공정한 진행을 위해 1인 1회만 참여 가능합니다.",
            "당첨자 발표 후 7일 이내에 발송됩니다."
        ]

        faq = faq_input(example_qs=example_qs, example_as=example_as)

    return {
        "summary": event_summary,
        "steps": steps,
        "rewards": rewards,
        "notes": notes,
        "faq": faq
    }

# ---------- UI ----------
st.caption("홈페이지 유형을 선택하면, 해당 유형에 맞는 입력 항목이 표시됩니다. 안내 내용을 참고하여 나만의 홈페이지를 완성해 보세요.")

st.header("유형 선택")
readable = st.selectbox("홈페이지 유형", list(TYPES.keys()))
chosen_type = TYPES[readable]

common = render_common_inputs()
st.markdown("---")

if chosen_type == "menu":
    type_payload = form_menu()
elif chosen_type == "brand":
    type_payload = form_story()
elif chosen_type == "event":
    type_payload = form_event()

# ---------- 최종 JSON 조립 ----------
site = {
    "brand_name": common["brand_name"],
    "type": chosen_type,
    "palette": common["palette"],
    "hero": common["hero"],
    "contact": {"phone": common["contact"], "address": common["address"]},
    "industry": common["industry"],
}

final_payload = {
    "site": site,
    "content": type_payload
}

if st.button("🏗️ 홈페이지 생성"):
    with st.spinner("AI가 홈페이지를 생성하는 중입니다... 잠시만 기다려주세요."):
        res = requests.post(f"{BACKEND_URL}/homepage/generate", json=final_payload, headers=headers)

        if res.status_code != 200:
            st.error(f"홈페이지 생성 실패 ❌ (상태 코드: {res.status_code})")
            st.text(res.text)
            st.stop()
        else:
            html_content = res.text

            st.success("✅ 홈페이지 생성 완료!", icon="🎉")

    with st.spinner("생성한 홈페이지를 등록하는 중입니다... 잠시만 기다려주세요."):
        res = requests.post(f"{BACKEND_URL}/homepage/upload", json={"html": html_content}, headers=headers)
        if res.status_code != 200:
            st.error(f"홈페이지 등록 실패 ❌ (상태 코드: {res.status_code})")
            st.text(res.text)
            st.stop()
        else:
            st.success("✅ 홈페이지 등록 완료!")
            deploy_url = res.json().get("url")

    deployed = False
    DEPLOY_CHECK_INTERVAL = 10
    DEPLOY_TIMEOUT = 300
    for i in range(0, DEPLOY_TIMEOUT, DEPLOY_CHECK_INTERVAL):
        time.sleep(10)

        try:
            check = requests.get(deploy_url)
            if check.status_code == 200:
                deployed = True
                break
            else:
                st.write(f"⏳ {i + DEPLOY_CHECK_INTERVAL}s... 아직 배포 중입니다.")
        except requests.exceptions.RequestException:
            st.write(f"⏳ {i + DEPLOY_CHECK_INTERVAL}s... 서버가 아직 응답하지 않습니다.")

    if deployed:
        st.success(f"✅ 홈페이지가 성공적으로 배포되었습니다! 🌐 [바로가기]({deploy_url})", icon="🎉")
    else:
        st.warning(
            f"⏰ 지정된 시간({DEPLOY_TIMEOUT}s) 안에 배포 완료를 확인하지 못했습니다.\n\n"
            f"잠시 후 직접 접속해 확인해주세요:\n\n👉 {deploy_url}"
        )
    

            
st.markdown("---")

