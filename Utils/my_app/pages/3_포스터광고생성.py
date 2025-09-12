import os
import json
import re
import requests
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# 🔑 OpenAI API Key (직접 선언)
OPENAI_API_KEY = ""
client = OpenAI(api_key=OPENAI_API_KEY)

# Streamlit 기본 설정
st.set_page_config(page_title="포스터 광고 생성", page_icon="🖼️", layout="wide")

# Helper Functions
def parse_json_block(text: str) -> dict:
    try:
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}

def fit_text_to_width(text, font_path, max_width, font_size, min_size=20):
    """주어진 텍스트를 max_width에 맞도록 폰트 크기를 줄임"""
    while font_size > min_size:
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font
        font_size -= 2
    return ImageFont.truetype(font_path, min_size)

def draw_multiline_text(draw, xy, text, font_path, fill, outline,
                        stroke=3, max_width=None, start_size=80, min_size=20):
    """여러 줄 텍스트 출력 (자동 줄바꿈 + 크기조정 + 외곽선)"""
    if not text:
        return [], 0, start_size

    x, y = xy
    lines = []
    font = ImageFont.truetype(font_path, start_size)

    # 자동 줄바꿈
    if max_width:
        words = text.split()
        line = ""
        for w in words:
            test_line = line + (" " if line else "") + w
            bbox = font.getbbox(test_line)
            w_width = bbox[2] - bbox[0]
            if w_width <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
    else:
        lines = text.split("\n")

    total_height = 0
    max_line_width = 0

    # 각 줄 그리기
    for line in lines:
        font = fit_text_to_width(line, font_path, max_width, start_size, min_size)
        _, _, w, h = font.getbbox(line)
        max_line_width = max(max_line_width, w)

        # 외곽선
        if stroke > 0:
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x+dx, y+dy), line, font=font, fill=outline)

        # 본문
        draw.text((x, y), line, font=font, fill=fill)

        y += font.size + 12
        total_height += font.size + 12

    return lines, total_height, font.size

# 설명
st.title("🖼️ 포스터 광고 생성")

st.markdown("""
이 페이지에서는 **광고 포스터**를 자동으로 생성합니다.

👉 타이틀과 본문은 항상 이미지 안에 들어가도록 자동으로 크기가 조정됩니다.  
겹치거나 잘리는 일이 없도록 **타이틀/본문 모두 함께 축소**됩니다.
""")

# 입력 UI (세션 유지)
col1, col2 = st.columns(2)

defaults = {
    "product": "수제 햄버거",
    "event": "50% 할인 행사",
    "date": "2025년 9월 20일",
    "location": "서울 강남역 매장",
    "vibe": "따뜻한, 가족, 피크닉",
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

with col1:
    st.session_state.product  = st.text_input("상품명", st.session_state.product)
    st.session_state.event    = st.text_input("이벤트", st.session_state.event)
    st.session_state.date     = st.text_input("날짜", st.session_state.date)
    st.session_state.location = st.text_input("장소", st.session_state.location)
    st.session_state.vibe     = st.text_input("분위기/스타일", st.session_state.vibe)

    # 제목 위치 직접 선택
    position = st.selectbox("제목 위치 선택", ["top", "center", "bottom"], index=0)

    gpt_model = st.selectbox("GPT 모델 선택", ["gpt-4o", "gpt-5", "gpt-5-mini"], index=0)
    dalle_size= st.selectbox("이미지 크기", ["1024x1024", "1024x1792", "1792x1024"], index=0)

    go = st.button("🎨 포스터 생성", type="primary")

with col2:
    result_area = st.empty()

# 실행
if go:
    # 1. GPT로 카피라이팅 + 프롬프트 생성
    with st.spinner("카피라이팅 생성 중..."):
        prompt = f"""
        - 상품: {st.session_state.product}
        - 이벤트: {st.session_state.event}
        - 날짜: {st.session_state.date}
        - 장소: {st.session_state.location}
        - 분위기: {st.session_state.vibe}

        출력 JSON:
        {{
          "TITLE_KO": "한 줄 광고 제목",
          "BODY_KO": "짧은 설명 문구",
          "DALLE_PROMPT_EN": "영어 프롬프트 (no text)"
        }}
        """
        res = client.chat.completions.create(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        data = parse_json_block(res.choices[0].message.content)

    title = data.get("TITLE_KO", "")
    body  = data.get("BODY_KO", "")
    dalle_prompt = data.get("DALLE_PROMPT_EN", "")

    with st.expander("생성된 DALL·E 프롬프트 보기"):
        st.code(dalle_prompt)

    # 2. DALL·E-3로 포스터 배경 생성
    with st.spinner("포스터 배경 생성 중..."):
        resp = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size=dalle_size,
        )
        img_url = resp.data[0].url
        img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")

    # 3. 폰트 지정 (NanumGothic)
    FONT_PATH = "font/NanumGothic.ttf"
    margin = 60
    max_width = img.width - margin * 2

    # 4. 제목 위치 계산
    if position == "top":
        title_y = 60
    elif position == "center":
        title_y = img.height // 3
    elif position == "bottom":
        title_y = img.height - 400  # 본문 공간 확보
    else:
        title_y = 60

    # 5. 텍스트 합성 (자동 크기 조정 포함)
    draw = ImageDraw.Draw(img)
    lines_t, title_height, title_font_size = draw_multiline_text(
        draw, (margin, title_y), title, FONT_PATH,
        (255,255,255,255), (0,0,0,255),
        stroke=4, max_width=max_width, start_size=80
    )

    body_y = title_y + title_height + 30
    lines_b, body_height, body_font_size = draw_multiline_text(
        draw, (margin, body_y), body, FONT_PATH,
        (255,255,0,255), (0,0,0,255),
        stroke=3, max_width=max_width, start_size=50
    )

    # --- 자동 크기 조정 루프 ---
    while body_y + body_height > img.height - 60:  # 잘리는 경우
        img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # 글자 크기 동시 축소
        title_font_size = max(20, title_font_size - 4)
        body_font_size = max(16, body_font_size - 4)

        lines_t, title_height, _ = draw_multiline_text(
            draw, (margin, title_y), title, FONT_PATH,
            (255,255,255,255), (0,0,0,255),
            stroke=4, max_width=max_width, start_size=title_font_size
        )
        body_y = title_y + title_height + 30
        lines_b, body_height, _ = draw_multiline_text(
            draw, (margin, body_y), body, FONT_PATH,
            (255,255,0,255), (0,0,0,255),
            stroke=3, max_width=max_width, start_size=body_font_size
        )

        if title_font_size <= 20 and body_font_size <= 16:
            break  # 더 이상 줄일 수 없음

    # 6. 결과 출력
    result_area.image(img, caption="최종 포스터", use_container_width=True)

    buf = BytesIO()
    img.save(buf, format="PNG")
    st.download_button("📥 다운로드", data=buf.getvalue(),
                       file_name="poster.png", mime="image/png")
